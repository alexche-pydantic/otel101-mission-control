# Runbook — "OTel 101: Why is my agent doing that?"

~16 minutes of live running. The arc is **show the bug first, sit in the confusion,
then let the trace answer it in five seconds.** Everything you type is in `code`.

> ### ⚠️ Type the prompts exactly as written
>
> The opening bug is sensitive to what is already in the conversation:
>
> - **Ask the weather question first, in a fresh session.** That is 8/8. Asked later
>   in a long conversation it drops to 5/6.
> - **Never type the word "rover."** The agent then hunts for the rover's location
>   instead of falling back on Houston: 0/5, against 6/6 without it.
> - Say "rover" out loud as much as you like. Just don't type it.

## Before you go on stage

```bash
cp .env.example .env            # fill in PYDANTIC_AI_GATEWAY_API_KEY
uv sync
uv run logfire projects use <project>      # DO NOT SKIP
uv run pytest -q                # everything green
uv run python ground_station.py            # terminal 1, leave it running
uv run python scripts/smoke.py             # terminal 2, expect "all clear"
```

**The project selection is not optional.** Without it the first `logfire.configure()`
stops and asks which project to use — which would happen at STEP 2, mid-paste, in
front of the room. Leave `LOGFIRE_TOKEN` unset; your `logfire auth` credentials are
what you want.

Once, the day before:

```bash
GROUND_STATION_TELEMETRY=1 uv run python ground_station.py   # terminal 1
uv run python scripts/seed_traces.py                         # terminal 2
```

Four finished traces land in Logfire. **Pin them.** They are the fallback for every
beat. Then restart the ground station *without* `GROUND_STATION_TELEMETRY`, and
`git checkout main -- agent.py .env.example`.

Two terminals: **1** = ground station (silent), **2** = the agent. Browser on Logfire.

---

## 1 · T+0:00 — the bug, with nothing to see (3 min)

```bash
uv run python agent.py
```

Type:

```
What's the weather?
```

You get something like:

> *"The weather in Houston, Texas is currently 28.4°C, humid, with a light breeze
> coming off the Gulf."*

Read it out warmly, as if it's a good answer. Pause. Then:

> *"That's a perfectly good answer. We are operating a rover on Mars."*

Now the important part — **do not fix it yet.** Sit in it:

> *"So what happened? Did the weather service return bad data? Did the model make it
> up? Did a tool fail silently? Did someone put Houston in a prompt two years ago?
> Look at the terminal — that's everything I have. One line of output. Nothing
> crashed, nothing went red, no exception, no stack trace. The tests pass. The
> service is healthy. The bill looks normal."*

> *"How would you debug this? Add print statements and hope it reproduces?"*

That discomfort is the whole talk. Let it sit before you move.

> **If it breaks:** if it answers about Mars instead, you're not in a fresh session —
> Ctrl-C, rerun, ask it as the first question. Ground station down? Terminal 1.

## 2 · T+3:00 — three lines, and the answer (3 min)

Ctrl-C. Open `agent.py`, find `# ── STEP 2 (live) ──`, paste:

```python
import logfire
logfire.configure()
logfire.instrument_pydantic_ai()
```

> *"Three lines. No collector, no config file, no changes to anything else."*

```bash
uv run python agent.py
```

Same question:

```
What's the weather?
```

A Logfire URL prints. Click it. Open the run, open the `get_weather` tool span, and
show the arguments:

```
execute_tool get_weather
  gen_ai.tool.call.arguments = {"location": "Houston, Texas"}
  gen_ai.tool.call.result    = {"site": "Houston, TX", "air_temp_c": 28.4, ...}
```

> *"There it is. The model asked for Houston. The weather service did its job
> perfectly — Houston really is 28.4°C and humid. Every step is individually correct.
> The bug is that nobody ever wrote down where the gear actually is, and the only
> place named anywhere in the prompt is where WE are."*

Show the prompt in the model span next to it — one sentence, Houston in it, Mars
nowhere.

> *"Five seconds from 'no idea' to the exact cause. That's the whole value
> proposition, and it cost three lines."*

> **If it breaks:** `git checkout demo-instrumented -- agent.py` has all four lines
> already in. Or use the pinned "wrong planet" trace.

## 3 · T+6:00 — what else is in there (2 min)

While you're in the trace: open a model span and walk the `gen_ai.*` attributes —
model name, the full prompt, the response, input and output tokens, the cost. Then
the timeline: where the time actually went.

> *"Nobody wrote a line of logging for any of this."*

> **If it breaks:** any pinned trace works.

## 4 · T+8:00 — a different kind of failure (3 min)

```
What's the state of the drill?
```

Slower this time. In Logfire: **three** `get_telemetry` spans, the first two red —
503, `comms blackout: no carrier from relay orbiter` — with model activity between
them, then a success.

> *"Same shape of question, completely different problem. The first was the model
> making a reasonable choice with missing context. This is the service falling over
> and the agent retrying until it got through. Without the trace, both just look like
> 'the agent is being weird today'."*

> **If it breaks:** the counter self-resets every three calls — just ask again.

## 5 · T+11:00 — across two services (3 min)

Terminal 1: Ctrl-C, then — **the most common way this demo fails, don't skip it:**

```bash
GROUND_STATION_TELEMETRY=1 uv run python ground_station.py
```

Terminal 2: Ctrl-C. Paste under `# ── STEP 5 (live) ──`:

```python
logfire.instrument_httpx()
```

```bash
uv run python agent.py
```

```
Ask the analyst: does the approaching dust storm threaten the mission?
```

One trace, both processes: `mission_control` → tool span → httpx2 client span →
**FastAPI server span** → `science_analyst` → a *different* model. Open the
token/cost view: it rolls up across both services.

> *"One line and one environment variable, and a request that crossed a process
> boundary is still one story — with the bill attached."*

> **If it breaks:** a missing service half means the env var or the restart. Don't
> debug live: switch to the pinned "cross-service" trace and keep talking.

## 6 · T+14:00 — the fix, and questions (2 min)

```bash
git checkout demo-fixed -- agent.py
```

Two sentences added to the prompt, naming where the gear actually is. Rerun, ask the
weather question — now it asks Elysium Base and reports -63.2°C.

> *"The fix was two sentences. Working out WHICH two sentences is the part that
> needed a trace."*

---

## Prompts, in order (copy-paste)

```
What's the weather?
What's the weather?
What's the state of the drill?
Ask the analyst: does the approaching dust storm threaten the mission?
```

If you want a clean happy-path answer at any point, use `Subsystem status report.` —
**not** a bare "Status report.", which makes the agent volunteer the Houston weather.

## Reset between rehearsals

```bash
git checkout main -- agent.py .env.example
```

Nothing else to reset: the drill counter self-cycles and there is no database.
