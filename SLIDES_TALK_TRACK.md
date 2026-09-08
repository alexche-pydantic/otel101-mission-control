# Cue card v3 · OTel 101 · flipped order · slides in 8:20, hard stop 8:30

New arc: agents in the dark → the monsters → the question to the room → the reveal (the answer existed before agents) → how it works → teaser → live.

**Rules (unchanged)**
- Time promise in the intro: "about eight minutes of slides, then we go live."
- OpenTracing + OpenCensus → merged 2019.
- gen_ai as a unit, now spoken during the DEMO when attributes are on screen: "your framework EMITS the standard names, any OTel tool knows how to READ them."
- Each point once. Watch "basically." "2 AM," not "2 AM in the morning."

---

## 1 · Title · 0:00-0:30
- One-breath intro: 20 years engineering, Pydantic user before employee, Applied AI.
- Hook: production at 2 AM, "what in the world made you do that."
- Time promise + shape.

## 2 · Launched in the dark · 0:30-1:30
- Agents left the notebook; they're a business bet now, someone owns the outcome.
- Tools are API and MCP calls into your REAL services, a layer on the stack you already had.
- The loop is driven by an LLM: non-deterministic, tool A or B on a slight input change.
- Land: we ship them, and we can't see them.

## 3 · The monsters · 1:30-2:30
- Point at two or three, not all: token spend nobody approved, tool sprawl, context overwhelm.
- Keeper: "amazing in capabilities, amazing in the failure modes."
- Land: you can't reason it out from the code, because the code doesn't decide. You have to look.

## 4 · The question · 2:30-3:15
- ASK IT AND PAUSE: "How do you know what your agent is doing right now?"
- Invite chat answers, read two aloud (expect: logs, print, nothing, langsmith).
- The turn: this exact question, seeing a distributed unpredictable system from the outside, was asked AND ANSWERED years before agents existed.

## 5 · The reveal: OpenTelemetry · 3:15-5:15
- Enjoy the reveal beat, don't rush past it.
- Cloud era: Netflix, Twitter, Uber, elastic microservices; breakpoints and one log file stopped holding.
- OpenTracing + OpenCensus → **2019** → OpenTelemetry.
- Three signals: logs (what happened at a point), metrics ("a number in motion"), traces (where, in what order).
- SPAN, 10 sec: one unit of work, start to end. One model call, one tool call.
- Close: odds are your stack already speaks it.

## 6 · The braid · 5:15-6:00
- Left to right: metric ramps, log names it (oom, 12:05), trace locates it and shows the recovery.
- Caption is on the slide: warns, names, locates. One rope.
- Pivot: so how does the data actually move?

## 7 · How the data moves · 6:00-7:30
- App + SDK emits → collector (optional: batch, redact, route, not day one) → backend (Logfire today).
- OTLP once: lean, protobuf over HTTP/gRPC, and it IS the standard. "Boxes are choices, arrows are the standard."
- Ownership once: swap tools, no code change. You own your telemetry.
- THE CLOSER: "if you take one thing from this workshop: OpenTelemetry is an objective good. I want to see my system, and I want to swap providers as my needs develop."

## 8 · Teaser: Mission Control · 7:30-8:20
- The fiction, fast: Mars mission-control agent, rover Kestrel, Pydantic AI, a ground-station service running its own second LLM.
- The plan, three fingers: instrument it in three lines; break it twice; read it all out of the traces, two services, one trace, full mission cost.
- "Let's go." Switch screens.
