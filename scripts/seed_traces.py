"""Pre-populate the Logfire project with all four demo scenarios — the presenter's backup.

Needs OPENAI_API_KEY and LOGFIRE_TOKEN, and the ground station running with its own
telemetry on:

    GROUND_STATION_TELEMETRY=1 uv run python ground_station.py
    uv run python scripts/seed_traces.py

This is the fully instrumented state (STEP 2 + STEP 5) applied from the outside, so
agent.py itself stays bare for the live paste.
"""

import os
import pathlib
import sys

import httpx
import logfire
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
load_dotenv()

logfire.configure(service_name="mission-control", distributed_tracing=True)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx()

from agent import GROUND_STATION_URL, mission_control  # noqa: E402

SCENARIOS = [
    ("happy path", "Status report — how's the rover doing?"),
    ("comms blackout", "What's the state of the drill?"),
    ("sunny on Mars", "What's the weather at Elysium Base?"),
    (
        "cross-service",
        "Ask the analyst: does the approaching dust storm threaten the mission?",
    ),
]

try:
    httpx.get(f"{GROUND_STATION_URL}/telemetry/power", timeout=10)
except httpx.ConnectError:
    sys.exit(f"ground station is not up at {GROUND_STATION_URL}")

if os.getenv("GROUND_STATION_TELEMETRY") != "1":
    print(
        "note: run the ground station with GROUND_STATION_TELEMETRY=1, otherwise the "
        "cross-service trace will only show the agent's half.\n"
    )

for label, prompt in SCENARIOS:
    print(f"\n=== {label}: {prompt}")
    with logfire.span("seed scenario: {label}", label=label):
        print(mission_control.run_sync(prompt).output)

logfire.force_flush()
print("\nseeded — open the Logfire project and pin these four traces before the talk")
