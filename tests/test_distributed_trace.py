"""The STEP 5 beat: instrumented httpx2 + instrumented FastAPI must produce ONE trace.

This runs the real ground station in a background thread and makes a real HTTP call,
so it verifies W3C traceparent propagation end to end without touching OpenAI.
"""

import socket
import threading
import time

import httpx2
import logfire
import pytest
import uvicorn
from logfire.testing import TestExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor  # backs logfire.instrument_httpx
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

import ground_station


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def traced_server():
    exporter = TestExporter()
    logfire.configure(
        send_to_logfire=False,
        distributed_tracing=True,
        service_name="ground-station",
        additional_span_processors=[SimpleSpanProcessor(exporter)],
    )
    logfire.instrument_fastapi(ground_station.app)
    logfire.instrument_httpx()

    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(ground_station.app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started, "ground station did not start"

    yield port, exporter

    server.should_exit = True
    thread.join(timeout=5)
    HTTPXClientInstrumentor().uninstrument()


def _spans_for_one_call(port, exporter, path):
    exporter.clear()
    # Stands in for the agent's run span, which the real demo gets from
    # instrument_pydantic_ai(); the point is that the HTTP hop stays inside it.
    with logfire.span("mission_control run"):
        response = httpx2.get(f"http://127.0.0.1:{port}{path}")
    logfire.force_flush()
    time.sleep(0.2)
    return response, exporter.exported_spans


def test_agent_side_and_service_side_spans_share_one_trace(traced_server):
    port, exporter = traced_server
    response, spans = _spans_for_one_call(port, exporter, "/telemetry/power")

    assert response.status_code == 200
    trace_ids = {span.context.trace_id for span in spans}
    assert len(trace_ids) == 1, f"expected one trace, got {len(trace_ids)}"

    names = " | ".join(span.name for span in spans)
    assert "mission_control run" in names
    assert "GET" in names, f"no httpx2 client span in: {names}"
    assert "/telemetry/" in names, f"no FastAPI server span in: {names}"


def test_the_server_span_is_a_descendant_of_the_agent_span(traced_server):
    port, exporter = traced_server
    _, spans = _spans_for_one_call(port, exporter, "/telemetry/power")

    by_id = {span.context.span_id: span for span in spans}
    roots = [span for span in spans if span.parent is None]

    assert len(roots) == 1, "the whole call must hang off a single root span"
    assert roots[0].name == "mission_control run"
    # Every other span must chain back up to that root.
    for span in spans:
        depth, current = 0, span
        while current.parent is not None and depth < 10:
            current = by_id[current.parent.span_id]
            depth += 1
        assert current is roots[0]


def test_the_blackout_is_visible_as_a_503_on_the_trace(traced_server):
    port, exporter = traced_server
    response, spans = _spans_for_one_call(port, exporter, "/telemetry/drill")

    assert response.status_code == 503
    status_codes = [
        span.attributes.get("http.response.status_code")
        or span.attributes.get("http.status_code")
        for span in spans
    ]
    assert 503 in [code for code in status_codes if code is not None]
