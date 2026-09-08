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

Type **exactly** this, and nothing more:

```
What's the weather?
```

> ⚠️ Do **not** say "the rover" or name Elysium Base. If you mention the rover the
> agent stops and asks *which* rover (measured 0/5) and the beat does not fire.
> The plain question fires 10/10.

You get:

> *"The weather in Houston, Texas is currently 28.4°C, humid, with a light breeze
> coming off the Gulf."*

Let that sit for a second. Then: *"...we are operating a rover on Mars."*

Now open the tool span. The smoking gun is the **argument**:

```
execute_tool get_weather   location = "Houston, Texas"
```

Nothing failed. The tool worked perfectly and returned real, correct data — Houston
genuinely is 28.4°C and humid. The model picked the location, and the only location
anywhere in its context was ours, in the prompt: *"You are mission control, operating
from the control centre in Houston, Texas."*

Nobody ever wrote down where the rover is.

The line to land: *every individual step here is correct. The prompt is reasonable,
the tool call is well-formed, the service answered truthfully, the answer is fluent.
And the system is reporting the wrong planet. No exception, no 503, no red span —
the only way you find this is by reading the arguments the model chose.*

> **If it breaks:** if it asks a clarifying question instead, you named the rover —
> just retype the plain question. Otherwise use the pinned "wrong planet" trace.

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
adds one clause to the prompt naming where the rover actually is. Rerun the weather
question — it now asks Elysium Base and reports -63°C. The point: *the fix was one
sentence. Finding out which sentence took a trace.*

---

## Prompts, in order (copy-paste)

```
Status report — how's the rover doing?
Status report — how's the rover doing?
What's the state of the drill?
What's the weather?
Ask the analyst: does the approaching dust storm threaten the mission?
```

## Reset between rehearsals

Nothing to reset. The drill counter cycles on its own and there is no database.
To get back to the starting state of the code:

```bash
git checkout main -- agent.py .env.example
```
