"""Measure Seed 2: how often does the agent report the weather in HOUSTON?

    uv run python scripts/wrong_location_rate.py

Needs a model key and the ground station running. Acceptance bar is >=6/10.

Ask the plain question. If you mention the rover, the agent stops and asks which
rover instead — measured 0/5 — and the bug does not fire.

The prompt must not say "mission control": that phrase makes the model reason about
a remote asset and hunt for its location (measured 1/3 instead of 3/3).
"""

import pathlib
import sys

from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
load_dotenv()

from agent import mission_control  # noqa: E402

# The demo asks this AFTER a status report and the drill, in one continuous
# conversation — so that is what we measure. A fresh session is the easy case.
SEQUENCE = ["Subsystem status report.", "What is the state of the drill?"]
QUESTION = "What's the weather?"
RUNS = 10

wrong = 0
for run in range(1, RUNS + 1):
    conversation = []
    for warmup in SEQUENCE:
        conversation = mission_control.run_sync(
            warmup, message_history=conversation
        ).all_messages()
    result = mission_control.run_sync(QUESTION, message_history=conversation)
    locations = [
        part.args
        for message in result.all_messages()
        for part in message.parts
        if getattr(part, "tool_name", None) == "get_weather" and hasattr(part, "args")
    ]
    asked_houston = any("houston" in str(a).lower() for a in locations)
    wrong += asked_houston
    print(f"\n--- run {run}: {'HOUSTON' if asked_houston else 'not houston'} {locations}")
    print(result.output.strip()[:300])

print(f"\nreported the wrong planet's weather: {wrong}/{RUNS}")
print("PASS — record this in the README" if wrong >= 6 else "BELOW BAR — see README")
