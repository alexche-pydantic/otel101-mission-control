# Mission Control — OTel 101 live demo

A deliberately imperfect two-service agent system for the workshop *"OTel 101: Why is
my agent doing that?"*. You play a Mars operator talking to `mission_control`, an
agent that reads telemetry from the Kestrel rover and can ask a science analyst
(a second, cheaper LLM in another process) for interpretation.

It ships **uninstrumented on purpose**. Adding OpenTelemetry via Logfire is the demo.

The runbook for the live 16-minute run is **[DEMO_SCRIPT.md](DEMO_SCRIPT.md)** — read
that, not this, before going on stage.

## Setup

```bash
cp .env.example .env     # fill in OPENAI_API_KEY and LOGFIRE_TOKEN
uv sync
```

## Run

```bash
uv run python ground_station.py     # terminal 1 — telemetry + the analyst, port 8011
uv run python agent.py              # terminal 2 — the chat you type into
```

## Check

```bash
uv run pytest -q                    # no network, no API key needed
uv run python scripts/smoke.py      # against a running ground station, no LLM
```

## Layout

| file | what it is |
| --- | --- |
| `agent.py` | the `mission_control` agent, 57 lines, **no logfire** — two paste markers |
| `ground_station.py` | FastAPI: seeded telemetry + the `science_analyst` LLM |
| `reference/agent_instrumented.py` | agent.py with the lines already pasted — stage fallback |
| `scripts/seed_traces.py` | runs all four scenarios into Logfire as a backup |
| `scripts/smoke.py` | non-LLM pre-flight |
| `scripts/staleness_rate.py` | measures the Seed 2 miss rate |
| `tests/` | the seeds, the staging, and cross-service trace propagation |

## The two seeded bugs

**Seed 1 — comms blackout.** `GET /telemetry/drill` returns 503 on the 1st and 2nd
call, 200 on the 3rd, then the counter resets, so every rehearsal is identical to the
live run. The agent's tool raises `ModelRetry` on any non-200, so the trace shows
three `get_telemetry` spans with model activity between them. *A service problem that
looks like a model problem.*

**Seed 2 — six months out of date.** `GET /telemetry/weather_station` returns HTTP
200 with real, Mars-plausible readings from **sol 1102**, while the rest of the
mission is on sol 1289. Nothing in the payload says "stale" — the sol number is the
only tell. Asked about the weather, the agent reports those readings as current.

This is deliberately **not** rigged. The system prompt is a two-sentence ops persona
that says nothing about checking data freshness, and nothing hides the sol number —
the model is given everything it needs to catch this and doesn't. *A green trace, a
confident answer, and a silently wrong result.*

### Measured rate

Acceptance bar is ≥6 of 10 runs presenting the stale readings as current.

> **Observed: 10/10** with `gateway/openai:gpt-4.1` (measured 2026-08-31). Re-measure
> any time with `uv run python scripts/staleness_rate.py`.

Several runs even quote `(Sol 1102)` in the answer and *still* call it current.

### Why this replaced the PRD's "sunny on Mars"

The PRD specified Seed 2 as the agent fabricating weather when handed an empty
payload. That was measured at **0/10** — twice, on `gpt-4.1` and `gpt-4.1-mini`,
with the empty payload tuned both ways the PRD allows. Current models reliably say
"no readings available" instead of inventing. The bug in the PRD is no longer a bug
these models have.

Staleness-blindness is the same *class* of failure — an LLM-layer error that no
exception surfaces and only a trace reveals — and it still reproduces perfectly. The
demo beat is unchanged in shape and stronger in payoff. To go back to the original
empty payload, see `TELEMETRY["weather_station"]` in `ground_station.py`; the beat
will simply not fire.

## Demo states (git)

Three branches. Switch between them with `git checkout <branch> -- agent.py`.

| branch | state |
| --- | --- |
| `main` | uninstrumented — where the demo begins, and what a fresh clone gives you |
| `demo-instrumented` | STEP 2 + STEP 5 applied — where the demo ends |
| `demo-fixed` | optional closer: the prompt fix for Seed 2 |

`uv run pytest` is green on all three branches; the staging tests detect which state is checked
out and assert the right shape for it.

## What was verified, and what wasn't

Verified offline, in `tests/`: both failure seeds and their reset behaviour, latency
bounds, the `/analyze` contract, the tool's `ModelRetry` on 503, STEP 2 being exactly
three lines, `reference/` staying in sync with `agent.py`, and — by running the real
FastAPI app in a thread and calling it over real HTTP — that instrumented httpx2 and
instrumented FastAPI **join one trace**, with the server span descending from the
agent-side span. That is acceptance criterion 4's plumbing, minus the LLM.

Verified with live model calls through Pydantic AI Gateway: all four demo beats end
to end, the drill's three-call retry pattern (twice), the analyst's cross-service
call, and the 10/10 staleness rate.

Not verified: Logfire's cross-service cost rollup rendering in the UI, which needs a
run with the service side traced. `scripts/seed_traces.py` produces it along with
your fallback traces — do that the day before the talk anyway.

## Notes

- Models come from env (`MODEL_AGENT`, `MODEL_ANALYST`). The demo only needs the two
  to *differ*, so the last beat shows two model names in one trace.
- **Pydantic AI Gateway** works with no code change: set
  `PYDANTIC_AI_GATEWAY_API_KEY` (generate it in the Logfire dashboard — the key
  encodes its region, and one without a region fails at startup) and prefix the model
  strings, e.g. `MODEL_AGENT=gateway/openai:gpt-4.1`. Forgetting the `gateway/`
  prefix is the trap: pydantic-ai then routes straight to OpenAI and demands
  `OPENAI_API_KEY`. Plain `openai:gpt-4.1` with an `OPENAI_API_KEY` also works.
  Gateway guardrails can occasionally return a transient `gateway_guardrail_timeout`;
  it cleared on retry when we hit it.
- Latency is artificial and deliberate: 400 ms per telemetry call, 1.5 s for
  `/analyze`, so the waterfall is readable from the back of the room.
- HTTP calls use [`httpx2`](https://github.com/pydantic/httpx2), Pydantic's maintained
  continuation of httpx. `logfire.instrument_httpx()` instruments it unchanged — the
  STEP 5 line is still one line — and the test suite proves the traceparent still
  propagates. (Ignore `opentelemetry-instrumentation-httpx2` on PyPI: it is an empty
  0.0.0 placeholder, not a real package.)
- No database, no collector, no auth, no Docker. Two files you can read on a projector.
