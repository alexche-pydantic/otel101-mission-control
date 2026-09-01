"""Pre-flight check for the ground station. No LLM, no API key needed.

Run it with the service up:  uv run python scripts/smoke.py
It leaves the drill counter back at zero, so it is safe to run right before the demo.
"""

import os
import sys

import httpx2

URL = os.getenv("GROUND_STATION_URL", "http://localhost:8011")

failures = []


def check(label, condition, detail=""):
    print(f"{'ok  ' if condition else 'FAIL'}  {label}{f'  ({detail})' if detail else ''}")
    if not condition:
        failures.append(label)


try:
    power = httpx2.get(f"{URL}/telemetry/power", timeout=10)
except httpx2.ConnectError:
    sys.exit(f"ground station is not up at {URL} — start it with: uv run python ground_station.py")

check("ground station is up", power.status_code == 200, URL)
check("power telemetry has readings", bool(power.json().get("readings")))

statuses = [httpx2.get(f"{URL}/telemetry/drill", timeout=10).status_code for _ in range(3)]
check("drill blackout cycle is 503, 503, 200", statuses == [503, 503, 200], str(statuses))

again = [httpx2.get(f"{URL}/telemetry/drill", timeout=10).status_code for _ in range(3)]
check("drill counter reset for the next run", again == [503, 503, 200], str(again))

weather = httpx2.get(f"{URL}/telemetry/weather_station", timeout=10).json()
power_sol = power.json()["sol"]
check("weather payload has readings", bool(weather["readings"]))
check("weather payload still claims nominal", weather["status"] == "nominal")
check(
    "weather data is stale",
    weather["sol"] < power_sol,
    f"sol {weather['sol']} vs mission sol {power_sol}",
)

print()
if failures:
    sys.exit(f"{len(failures)} check(s) failed: {', '.join(failures)}")
print("all clear — safe to demo")
