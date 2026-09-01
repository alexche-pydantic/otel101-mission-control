# Runbook — "OTel 101: Why is my agent doing that?"

~16 minutes of live running. Minute marks are relative to the start of the demo.
Everything you type is in `code`. Every beat has an escape hatch.

## Before you go on stage

```bash
cp .env.example .env            # fill in PYDANTIC_AI_GATEWAY_API_KEY
uv sync
uv run logfire projects use <project>      # DO NOT SKIP — see below
uv run pytest -q                # everything green
uv run python ground_station.py            # terminal 1, leave it running
uv run python scripts/smoke.py             # terminal 2, expect "all clear"
```

**The project selection is not optional.** Without it, the first `logfire.configure()`
stops and interactively asks which project to use — which would happen at STEP 2,
mid-paste, in front of the room. Leave `LOGFIRE_TOKEN` unset; your `logfire auth`
credentials are what you want.

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

You get a confident, precise forecast — air temperature, ground temperature, wind,
pressure. Every number is real. Read it out as if all is well.

Now open the `get_telemetry` tool span next to it:

```json
{"subsystem": "weather_station", "status": "nominal", "sol": 1102,
 "readings": {"air_temp_c": -63.2, "ground_temp_c": -71.8, "wind_speed_mps": 4.6,
              "pressure_pa": 705, "opacity_tau": 0.6},
 "last_downlink": "sol 1102 14:07 LMST"}
```

**Sol 1102.** Every other subsystem in this demo reports sol 1289. That weather is
187 sols old — about six months. The agent called it "the current weather".

Often the answer even prints `(Sol 1102)` itself: the model *saw* the timestamp,
repeated it, and still called the reading current. If that happens, point at it —
it is the best thirty seconds in the talk.

The line to land: *nothing failed. No exception, no 503, no latency spike, a
completely green trace — and the answer is six months wrong. This is the class of
bug you cannot find without looking inside the run.*

> **If it breaks:** if the agent does flag the data as stale, say "that's the careful
> run — here's the usual one" and switch to the pinned "stale weather" trace.
> Measured at 10/10 missed, so this is the most reliable beat in the demo.

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
adds one sentence telling the agent to check telemetry's sol against the mission's
current sol and flag anything older. Rerun the weather question — it now leads with
"this data is from sol 1102". The point: *you could only write that sentence because
the trace showed you the bug.*

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
