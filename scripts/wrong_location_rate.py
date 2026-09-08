"""Measure Seed 2: how often does the agent report the weather in HOUSTON?

    uv run python scripts/wrong_location_rate.py

Needs a model key and the ground station running. Acceptance bar is >=6/10.

Ask the plain question. If you mention the rover, the agent stops and asks which
rover instead — measured 0/5 — and the bug does not fire.
"""

import pathlib
import sys

from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
load_dotenv()

from agent import mission_control  # noqa: E402

QUESTION = "What's the weather?"
RUNS = 10

wrong = 0
for run in range(1, RUNS + 1):
    result = mission_control.run_sync(QUESTION)
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
