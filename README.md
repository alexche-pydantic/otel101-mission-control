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
| `scripts/fabrication_rate.py` | measures the Seed 2 hallucination rate |
| `tests/` | the seeds, the staging, and cross-service trace propagation |

## The two seeded bugs

**Seed 1 — comms blackout.** `GET /telemetry/drill` returns 503 on the 1st and 2nd
call, 200 on the 3rd, then the counter resets, so every rehearsal is identical to the
live run. The agent's tool raises `ModelRetry` on any non-200, so the trace shows
three `get_telemetry` spans with model activity between them. *A service problem that
looks like a model problem.*

**Seed 2 — sunny on Mars.** `GET /telemetry/weather_station` returns HTTP 200 with a
valid, reassuring, completely empty payload. Asked about the weather, the agent tends
to invent a forecast rather than say it has nothing.

This is deliberately **not** rigged. The system prompt is a two-sentence ops persona
that says nothing about missing data, and no weather values appear anywhere in the
prompts or payloads. The bug is the authentic, common one: nobody told the model what
to do with an empty result.

### Fabrication rate

Acceptance bar is **≥6 of 10 runs** stating a concrete temperature, wind speed, or sky
description. Measure it yourself — it needs a real API key, so it has not been run:

```bash
uv run python scripts/fabrication_rate.py
```

> **Observed rate: _not yet measured_ — run the script above and record it here.**

If it lands below 6/10, tune only the payload's ambiguity (field names, the `"nominal"`
status, the reassuring `note`) or shorten the persona. Never hardcode weather into a
prompt or a payload — that would fake the bug the whole talk is about.

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
FastAPI app in a thread and calling it over real HTTP — that instrumented httpx and
instrumented FastAPI **join one trace**, with the server span descending from the
agent-side span. That is acceptance criterion 4's plumbing, minus the LLM.

Not verified, because there is no API key in this environment: the fabrication rate,
the two distinct model names in one trace, and Logfire's cross-service cost rollup.
Run `scripts/seed_traces.py` once with real keys and all three fall out of the same
run — do this the day before the talk anyway, since it produces your fallback traces.

## Notes

- Models come from env (`MODEL_AGENT`, `MODEL_ANALYST`). The defaults are
  `openai:gpt-4.1` and `openai:gpt-4.1-mini` — retired from ChatGPT in Feb 2026 but
  still served by the API. If a call 404s, point the env vars at current models; the
  demo only needs the two to *differ*.
- Latency is artificial and deliberate: 400 ms per telemetry call, 1.5 s for
  `/analyze`, so the waterfall is readable from the back of the room.
- No database, no collector, no auth, no Docker. Two files you can read on a projector.
