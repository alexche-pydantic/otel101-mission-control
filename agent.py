"""mission_control — the agent a Mars operator talks to.

Run it with:  uv run python agent.py
"""

import os

import httpx2
from dotenv import load_dotenv
from pydantic_ai import Agent, ModelRetry

load_dotenv()

# ── STEP 2 (live): paste the three lines below this comment ──
# import logfire
# logfire.configure()
# logfire.instrument_pydantic_ai()

# ── STEP 5 (live): paste this one line to join both services in one trace ──
# logfire.instrument_httpx()

GROUND_STATION_URL = os.getenv("GROUND_STATION_URL", "http://localhost:8011")

mission_control = Agent(
    os.getenv("MODEL_AGENT", "openai:gpt-4.1"),
    instructions=(
        "You are mission control for the rover Kestrel at Elysium Base on Mars. "
        "Answer the operator using the rover's telemetry and the science analyst."
    ),
)


@mission_control.tool_plain(retries=3)
def get_telemetry(subsystem: str) -> dict:
    """Read current telemetry for one rover subsystem.

    Subsystems: power, wheels, nav, drill, weather_station.
    """
    response = httpx2.get(f"{GROUND_STATION_URL}/telemetry/{subsystem}", timeout=30)
    if response.status_code != 200:
        raise ModelRetry(
            f"ground station returned {response.status_code}: {response.text}"
        )
    return response.json()


@mission_control.tool_plain
def request_analysis(question: str) -> str:
    """Ask the ground station's science analyst to interpret mission data."""
    response = httpx2.post(
        f"{GROUND_STATION_URL}/analyze", json={"question": question}, timeout=60
    )
    return response.json()["analysis"]


if __name__ == "__main__":
    mission_control.to_cli_sync(prog_name="mission-control")
