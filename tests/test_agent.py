"""The agent's tools, and the demo staging that the live run depends on."""

import pathlib

import httpx2
import pytest
from pydantic_ai import ModelRetry

import agent

REPO = pathlib.Path(__file__).parent.parent
AGENT_SOURCE = (REPO / "agent.py").read_text()
REFERENCE_SOURCE = (REPO / "reference" / "agent_instrumented.py").read_text()


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_get_telemetry_returns_the_payload_on_200(monkeypatch):
    monkeypatch.setattr(
        httpx2, "get", lambda *a, **kw: FakeResponse(200, {"subsystem": "power"})
    )

    assert agent.get_telemetry("power") == {"subsystem": "power"}


def test_get_telemetry_asks_the_model_to_retry_on_503(monkeypatch):
    monkeypatch.setattr(
        httpx2, "get", lambda *a, **kw: FakeResponse(503, {"error": "comms blackout"})
    )

    with pytest.raises(ModelRetry) as raised:
        agent.get_telemetry("drill")

    assert "503" in str(raised.value)
    assert "comms blackout" in str(raised.value)


def test_get_telemetry_is_registered_with_three_retries():
    tool = agent.mission_control._function_toolset.tools["get_telemetry"]
    assert tool.max_retries == 3


def test_request_analysis_returns_the_analyst_text(monkeypatch):
    monkeypatch.setattr(
        httpx2, "post", lambda *a, **kw: FakeResponse(200, {"analysis": "park and wait"})
    )

    assert agent.request_analysis("dust storm?") == "park and wait"


# ── Demo staging ──
#
# agent.py has two valid shapes: the bare state the demo starts from, and the
# instrumented state it ends in (the commit tagged demo-instrumented). These tests
# check whichever one is checked out, so the suite is green either way.

BARE = "STEP 2 (live)" in AGENT_SOURCE

demo_start_only = pytest.mark.skipif(
    not BARE, reason="agent.py is in the instrumented demo-end state"
)
demo_end_only = pytest.mark.skipif(
    BARE, reason="agent.py is in the bare demo-start state"
)


@demo_end_only
def test_instrumented_state_has_all_four_lines_active():
    for line in (
        "import logfire",
        "logfire.configure()",
        "logfire.instrument_pydantic_ai()",
        "logfire.instrument_httpx()",
    ):
        assert f"\n{line}\n" in AGENT_SOURCE, f"missing active line: {line}"


@demo_start_only
def test_agent_ships_uninstrumented():
    """Acceptance 1: bare agent.py has zero logfire references outside comments."""
    code_lines = [
        line
        for line in AGENT_SOURCE.splitlines()
        if "logfire" in line and not line.strip().startswith("#")
    ]
    assert code_lines == []


@demo_start_only
def test_step_2_is_exactly_three_pasted_lines():
    """Acceptance 5: the demo's central promise is 'three lines'."""
    lines = AGENT_SOURCE.splitlines()
    start = next(i for i, line in enumerate(lines) if "STEP 2 (live)" in line)
    pasted = []
    for line in lines[start + 1 :]:
        if not line.strip():
            break
        pasted.append(line.strip().removeprefix("# "))

    assert pasted == [
        "import logfire",
        "logfire.configure()",
        "logfire.instrument_pydantic_ai()",
    ]


@demo_start_only
def test_step_5_is_a_single_pasted_line():
    lines = AGENT_SOURCE.splitlines()
    start = next(i for i, line in enumerate(lines) if "STEP 5 (live)" in line)

    assert lines[start + 1].strip() == "# logfire.instrument_httpx()"
    assert lines[start + 2].strip() == ""


def test_agent_is_short_enough_to_read_on_a_projector():
    """Acceptance 6: under ~90 lines uninstrumented."""
    assert len(AGENT_SOURCE.splitlines()) < 90


def test_reference_matches_agent_plus_the_pasted_lines():
    """Acceptance 5: reference/ is agent.py with the markers activated, nothing more."""
    expected = []
    for line in AGENT_SOURCE.splitlines():
        stripped = line.strip()
        if not stripped or "(live)" in stripped:
            continue
        if stripped.startswith("# ") and "logfire" in stripped:
            stripped = stripped.removeprefix("# ")
        expected.append(stripped)

    actual = [line.strip() for line in REFERENCE_SOURCE.splitlines() if line.strip()]
    assert actual == expected
