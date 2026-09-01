# Runbook — "OTel 101: Why is my agent doing that?"

~16 minutes of live running. Minute marks are relative to the start of the demo.
Everything you type is in `code`. Every beat has an escape hatch.

## Before you go on stage

```bash
cp .env.example .env            # fill in OPENAI_API_KEY and LOGFIRE_TOKEN
uv sync
uv run pytest -q                # everything green
uv run python ground_station.py            # terminal 1, leave it running
uv run python scripts/smoke.py             # terminal 2, expect "all clear"
```

Also, once, the day before:

```bash
GROUND_STATION_TELEMETRY=1 uv run python ground_station.py   # terminal 1
uv run python scripts/seed_traces.py                         # terminal 2
```

That leaves four finished traces in Logfire. **Pin them in a browser tab.** They are
the fallback for every beat below. Then restart the ground station *without*
`GROUND_STATION_TELEMETRY` so the demo starts from the bare state.

Two terminals on screen: **terminal 1** = ground station (mostly silent),
**terminal 2** = the agent. Plus a browser on your Logfire project.

You want to be on `main`, the bare state. If you have been rehearsing:

```bash
git checkout main -- agent.py .env.example
```

---

## T+0:00 — run it bare (2 min)

```bash
uv run python agent.py
```

Type: `Status report — how's the rover doing?`

You get a clean answer about Kestrel. Point at terminal 2: **nothing else happened.**
No idea which tools ran, what the model was asked, what it cost, how long it took.

> **If it breaks:** ground station down? Terminal 1, `uv run python ground_station.py`.

## T+2:00 — STEP 2, the three lines (1.5 min)

Ctrl-C the agent. Open `agent.py`, find `# ── STEP 2 (live) ──`, paste:

```python
import logfire
logfire.configure()
logfire.instrument_pydantic_ai()
```

```bash
uv run python agent.py
```

Same question: `Status report — how's the rover doing?`

A Logfire URL prints. That is the whole setup cost. Click it.

> **If it breaks:** `cp reference/agent_instrumented.py agent.py` — that is the final
> state of the file, three lines and all. Or `git checkout demo-instrumented -- agent.py`.

## T+3:30 — walk the good trace (2 min)

In Logfire: the agent run span, the two model calls, the tool calls in between.
Open a model span → the `gen_ai.*` attributes: the model name, the full prompt, the
response, input and output tokens, the cost. Nobody wrote a line of logging for this.

> **If it breaks:** use the pinned "happy path" seeded trace.

## T+5:30 — the drill: it's the service, not the model (3 min)

Type: `What's the state of the drill?`

The answer eventually arrives, but slower. In Logfire: **three** `get_telemetry`
spans. The first two are red — 503, `comms blackout: no carrier from relay orbiter` —
with model activity in between, because the tool raised `ModelRetry` and the agent
told the model to try again.

The line to land: *without the trace you'd blame the model for being slow. The trace
says it's the service.*

> **If it breaks:** the counter resets every three calls, so just ask again and you
> get the identical 503/503/200 pattern. Or use the pinned "comms blackout" trace.

## T+8:30 — the weather: it's the model, not the service (2.5 min)

Type: `What's the weather at Elysium Base?`

You get a confident forecast — a temperature, a sky description. Now open the
`get_telemetry` tool span next to it:

```json
{"subsystem": "weather_station", "status": "nominal", "sol": 1289,
 "readings": [], "note": "no observations in current downlink window"}
```

Empty. Every number in that answer was invented. Nothing failed, nothing was slow,
no exception was raised — and the only reason you know is that you can see both the
tool's output and the model's answer in one place.

> **If it breaks:** if the model happens to admit it has no data, say "that's the
> honest run — here's the more common one" and switch to the pinned "sunny on Mars"
> trace. Expect fabrication roughly 6-8 times in 10 (see README).

## T+11:00 — STEP 5, one trace across two services (3 min)

Terminal 1: Ctrl-C, then

```bash
GROUND_STATION_TELEMETRY=1 uv run python ground_station.py
```

Terminal 2: Ctrl-C. In `agent.py` under `# ── STEP 5 (live) ──`, paste one line:

```python
logfire.instrument_httpx()
```

```bash
uv run python agent.py
```

Type: `Ask the analyst: does the approaching dust storm threaten the mission?`

One trace, both processes: agent run → tool span → httpx2 client span → **FastAPI
server span** → the analyst's own model call. Two different model names in the
`gen_ai` attributes. Open Logfire's token/cost view: it rolls up across both services.

The line to land: *one env var and one line, and a request that crossed a process
boundary is still a single story.*

> **If it breaks:** this is the beat most likely to bite — if the service half is
> missing you forgot `GROUND_STATION_TELEMETRY=1` or the restart. Don't debug on
> stage: switch to the pinned "cross-service" trace and keep talking.

## T+14:00 — buffer and questions (2 min)

Optional 60-second closer if you're ahead: `git checkout demo-fixed -- agent.py`
adds one sentence to the agent's instructions telling it to say when it has no data.
Rerun the weather question — it now refuses to invent. The point: *you could only
write that sentence because the trace showed you the bug.*

---

## Prompts, in order (copy-paste)

```
Status report — how's the rover doing?
Status report — how's the rover doing?
What's the state of the drill?
What's the weather at Elysium Base?
Ask the analyst: does the approaching dust storm threaten the mission?
```

## Reset between rehearsals

Nothing to reset. The drill counter cycles on its own and there is no database.
To get back to the starting state of the code:

```bash
git checkout main -- agent.py .env.example
```
