# Talk outline — "OTel 101: Why is my agent doing that?"

The structure of the ~8 minutes of slides that precede the live demo, with the
points each section makes and roughly how long each takes. Written so the talk can
be re-run, adapted, or simply read as an argument without having been in the room.

The live portion is in **[DEMO_SCRIPT.md](DEMO_SCRIPT.md)**.

**The arc:** agents are shipped blind → the failure modes that follow → a question to
the room → the reveal that the question was answered years before agents → how the
plumbing works → what we're about to watch break.

---

## 1 · Opening · 0:00–0:30

Set the scene with the experience everyone recognises: something in production does
something inexplicable, and the first question is *"what in the world made you do
that?"*

Promise the shape up front — roughly eight minutes of slides, then live code — so
nobody spends the talk wondering how long the theory runs.

## 2 · Launched in the dark · 0:30–1:30

- Agents have left the notebook. They're a business bet now, and someone owns the
  outcome.
- Their tools are ordinary API and MCP calls into real services — a new layer on the
  stack you already had, not a separate world.
- The loop is driven by an LLM, so it is non-deterministic: a slight change in input
  can send it down tool A instead of tool B.

**The point:** we ship these, and we can't see inside them.

## 3 · The failure modes · 1:30–2:30

Pick two or three rather than listing everything — token spend nobody approved, tool
sprawl, context overwhelm.

> *"Amazing in capabilities, amazing in the failure modes."*

**The point:** you can't reason this out from reading the code, because the code isn't
what decides. You have to look at what actually happened.

## 4 · The question · 2:30–3:15

Ask the room, and leave silence for it:

> **"How do you know what your agent is doing right now?"**

Answers tend to be some mix of logs, print statements, nothing, or a vendor tool.

**The turn:** this exact question — how to see a distributed, unpredictable system
from the outside — was asked *and answered* years before agents existed.

## 5 · OpenTelemetry · 3:15–5:15

The cloud era hit the same wall first. Netflix, Twitter, Uber, elastic microservices:
breakpoints and a single log file stopped being enough.

- **OpenTracing + OpenCensus → merged in 2019 → OpenTelemetry.**
- **Three signals:** logs (what happened at a point in time), metrics (a number in
  motion), traces (where something happened, and in what order).
- **A span** is one unit of work, start to end — one model call, one tool call. Traces
  are made of spans.

**The point:** odds are your stack already speaks this.

## 6 · How the three signals work together · 5:15–6:00

Read left to right: the metric ramps and warns you something is wrong; the log names
it (an OOM at 12:05); the trace locates it and shows the recovery.

Warns, names, locates — three strands of one rope.

## 7 · How the data moves · 6:00–7:30

```
app + SDK  →  collector (optional)  →  backend
```

- The SDK emits from your application.
- A collector can batch, redact, and route — genuinely useful, but not a day-one
  requirement.
- The backend is where you read it. Logfire in this workshop; that's a choice, not a
  constraint.

**OTLP** is the wire protocol: lean, protobuf over HTTP or gRPC, and it *is* the
standard. The boxes are choices; the arrows are the standard.

That's what ownership means here — swap tools without changing code. Your telemetry
is yours.

> **The one thing worth keeping:** OpenTelemetry is an objective good. You want to see
> your system, and you want to be able to change providers as your needs develop.

## 8 · What we're about to break · 7:30–8:20

The demo, set up quickly:

- A mission-control agent for a Mars rover, built with Pydantic AI.
- A separate ground-station service that runs its own, cheaper LLM.
- Two processes, so the traces have somewhere to cross.

The plan, in three parts: **instrument it in three lines; break it twice; read both
failures out of the traces** — two services, one trace, and the cost of the whole
mission.

Then switch screens and run it. → **[DEMO_SCRIPT.md](DEMO_SCRIPT.md)**

---

## A note on the `gen_ai` semantic conventions

Worth saying while the attributes are on screen during the demo rather than in the
slides: your framework *emits* the standard attribute names, and any OpenTelemetry
tool knows how to *read* them. That's the whole point of a convention — the
instrumentation and the tool that displays it don't have to come from the same vendor.
