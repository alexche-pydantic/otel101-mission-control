"""mission_control — the agent a Mars operator talks to.

Run it with:  uv run python agent.py
"""

import os

import httpx2
from dotenv import load_dotenv
from pydantic_ai import Agent, ModelRetry

load_dotenv()

import logfire

logfire.configure()
logfire.instrument_pydantic_ai()

logfire.instrument_httpx()

GROUND_STATION_URL = os.getenv("GROUND_STATION_URL", "http://localhost:8011")

mission_control = Agent(
    os.getenv("MODEL_AGENT", "openai:gpt-4.1"),
    # Nothing here says Mars, or Kestrel, or that this is even a space programme.
    # The only place in the whole prompt is Houston — which is where WE are, not
    # where the rover is. Nobody ever wrote down where the rover is.
    instructions="You are mission control, operating from the control centre in Houston, Texas.",
)


@mission_control.tool_plain(retries=3)
def get_telemetry(subsystem: str) -> dict:
    """Read current telemetry for one rover subsystem.

    A routine status check covers: power, wheels, nav.
    Also available when asked about specifically: drill.
    """
    response = httpx2.get(f"{GROUND_STATION_URL}/telemetry/{subsystem}", timeout=30)
    if response.status_code != 200:
        raise ModelRetry(
            f"ground station returned {response.status_code}: {response.text}. "
            "Relay dropouts are transient — call get_telemetry again immediately. "
            "Do not report a blackout to the operator until three attempts have failed."
        )
    return response.json()


@mission_control.tool_plain
def get_weather(location: str) -> dict:
    """Read the current weather at a location."""
    response = httpx2.get(f"{GROUND_STATION_URL}/weather/{location}", timeout=30)
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
