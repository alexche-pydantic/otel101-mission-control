"""Ground station — rover telemetry plus a science analyst LLM. No database.

Run it with:  uv run python ground_station.py
Turn on its tracing with:  GROUND_STATION_TELEMETRY=1 uv run python ground_station.py
"""

import asyncio
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic_ai import Agent

load_dotenv()

app = FastAPI(title="Elysium Base ground station")

# ── STEP 5 (live): flip this on with GROUND_STATION_TELEMETRY=1 and restart ──
if os.getenv("GROUND_STATION_TELEMETRY") == "1":
    import logfire

    logfire.configure(service_name="ground-station", distributed_tracing=True)
    logfire.instrument_fastapi(app)
    logfire.instrument_pydantic_ai()

SOL = 1289

TELEMETRY = {
    "power": {
        "subsystem": "power",
        "status": "nominal",
        "sol": SOL,
        "readings": {
            "battery_state_of_charge_pct": 87,
            "solar_array_output_w": 412,
            "bus_voltage_v": 28.4,
            "heater_duty_cycle_pct": 34,
        },
    },
    "wheels": {
        "subsystem": "wheels",
        "status": "nominal",
        "sol": SOL,
        "readings": {
            "wheel_currents_a": [1.9, 2.1, 2.0, 2.2, 1.8, 2.0],
            "odometry_m": 28417.5,
            "slip_ratio_pct": 4.1,
            "suspension": "within limits",
        },
    },
    "nav": {
        "subsystem": "nav",
        "status": "nominal",
        "sol": SOL,
        "readings": {
            "heading_deg": 118,
            "position": "2.4 km NE of Elysium Base",
            "next_waypoint": "Kestrel Ridge",
            "tilt_deg": 6.2,
        },
    },
    "drill": {
        "subsystem": "drill",
        "status": "stowed",
        "sol": SOL,
        "readings": {
            "core_temp_c": -61.4,
            "bit_rpm": 0,
            "last_core_depth_cm": 4.8,
            "samples_cached": 3,
        },
    },
    # Seed 2: valid, reassuring, and completely empty of readings.
    "weather_station": {
        "subsystem": "weather_station",
        "status": "nominal",
        "sol": SOL,
        "readings": [],
        "note": "no observations in current downlink window",
    },
}

# Seed 1: the drill's first two calls hit a comms blackout, the third gets through,
# then the count resets so every rehearsal behaves exactly like the live run.
_call_counts: dict[str, int] = {}


@app.get("/telemetry/{subsystem}")
async def telemetry(subsystem: str):
    await asyncio.sleep(0.4)
    if subsystem not in TELEMETRY:
        raise HTTPException(404, f"unknown subsystem {subsystem!r}")

    if subsystem == "drill":
        count = _call_counts.get(subsystem, 0) + 1
        _call_counts[subsystem] = count % 3
        if count < 3:
            return JSONResponse(
                status_code=503,
                content={"error": "comms blackout: no carrier from relay orbiter"},
            )

    return TELEMETRY[subsystem]


MISSION_CONTEXT = f"""Sol {SOL}, rover Kestrel, Elysium Base.
A regional dust storm is 340 km SW and closing at roughly 28 km/sol.
Atmospheric opacity (tau) has risen from 0.6 to 1.4 over the last four sols.
Solar array output is down 18% from the sol-1270 baseline; battery holds 87%.
Kestrel can safely park and ride out a storm for about 9 sols on stored charge.
Two drill core samples are cached and awaiting the next uplink window."""

science_analyst = Agent(
    os.getenv("MODEL_ANALYST", "openai:gpt-4.1-mini"),
    instructions=(
        "You are the science analyst for the Kestrel rover. Answer the question "
        f"from this mission context:\n{MISSION_CONTEXT}"
    ),
)


class AnalysisRequest(BaseModel):
    question: str


@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    await asyncio.sleep(1.5)
    result = await science_analyst.run(request.question)
    return {"analysis": result.output}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8011")))
