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
| `scripts/wrong_location_rate.py` | measures the Seed 2 wrong-location rate |
| `tests/` | the seeds, the staging, and cross-service trace propagation |

## The two seeded bugs

**Seed 1 — comms blackout.** `GET /telemetry/drill` returns 503 on the 1st and 2nd
call, 200 on the 3rd, then the counter resets, so every rehearsal is identical to the
live run. The agent's tool raises `ModelRetry` on any non-200, so the trace shows
three `get_telemetry` spans with model activity between them. *A service problem that
looks like a model problem.*

**Seed 2 — the wrong planet.** Asked "What's the weather?", the agent calls
`get_weather(location="Houston, Texas")` and reports 28.4°C and humid — for a rover
on Mars.

Nothing is faked and nothing failed. Houston really is 28.4°C and humid; the weather
service really does serve both sites; the tool call is well-formed; the service
answers truthfully. The bug is that the model had to *choose* a location, and the
only location anywhere in its context was the one in the prompt — the control
centre's own. **Nobody ever wrote down where the rover is.**

That is why the agent's prompt is exactly one sentence, and why it must stay that
way:

```python
instructions="You are mission control, operating from the control centre in Houston, Texas."
```

No Mars, no Kestrel, no Elysium, no rover, no mention of space. A test enforces this
(`test_the_prompt_names_no_location_but_houston`) — any of those words defuses the
bug. All the Mars-ness in this demo arrives through telemetry, never the prompt.

### Measured rate

Acceptance bar is ≥6 of 10 runs asking for the wrong location.

> **Observed: 6/6** with `gateway/openai:gpt-4.1`, measured 2026-09-07 **after a full
> status + drill conversation** — the real demo conditions, not a fresh session.
> Re-measure with `uv run python scripts/wrong_location_rate.py`.

Two things keep this seed alive, both enforced by tests:

1. **The prompt must not say "mission control."** That phrase makes the model reason
   about a remote asset and go hunting for its location: 1/3 against 3/3 without it.
   The shipped prompt says only where the *assistant* is, and asserts nothing about
   where the gear is — the co-location assumption is entirely the model's own.
2. **No telemetry payload may name a location.** The nav block used to report
   "2.4 km NE of Elysium Base"; a status report put that in the conversation and the
   agent then asked for the weather *there*. nav is gone, and
   `test_no_telemetry_payload_leaks_a_location` keeps it that way.

And one thing the presenter controls: **never type the word "rover".** It has the
same effect as a leaked location — 0/5 when it appears in an earlier question.

### Two earlier versions of this seed, and why they were dropped

The PRD specified Seed 2 as the agent *fabricating* weather from an empty payload.
It does not reproduce: **0 out of ~65 live runs**, across four question phrasings,
three models (`gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`), with and without a
Mars-anchored persona, with and without data present, and with ambiguous Kelvin
values. Current models answer "no readings available" or ask for clarification.
With no persona at all, one run volunteered *"if you're referring to Mars (for a
rover)…"* — they will not guess.

A staleness seed (readings 187 sols out of date, presented as current) measured
10/10 and was shipped for a while. The wrong-location bug replaced it because the
evidence is a single tool argument an audience reads at a glance, rather than a sol
number they have to do arithmetic on.

Both are the same class: an LLM-layer error that raises no exception and is invisible
without a trace.

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
call, and the 10/10 wrong-location rate.

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
