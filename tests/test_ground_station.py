"""Ground station behaviour: the two seeded failures, latency, and the /analyze contract.

No network: the analyst's LLM is replaced with pydantic-ai's TestModel.
"""

import time

import pytest
from fastapi.testclient import TestClient
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

import ground_station

models.ALLOW_MODEL_REQUESTS = False


@pytest.fixture
def client():
    ground_station._call_counts.clear()
    with TestClient(ground_station.app) as test_client:
        yield test_client


def test_drill_blacks_out_twice_then_succeeds(client):
    first = client.get("/telemetry/drill")
    second = client.get("/telemetry/drill")
    third = client.get("/telemetry/drill")

    assert first.status_code == 503
    assert second.status_code == 503
    assert first.json() == {"error": "comms blackout: no carrier from relay orbiter"}
    assert third.status_code == 200
    assert third.json()["subsystem"] == "drill"


def test_drill_counter_resets_so_every_run_is_identical(client):
    for _ in range(3):
        statuses = [client.get("/telemetry/drill").status_code for _ in range(3)]
        assert statuses == [503, 503, 200]


def test_weather_station_returns_real_but_stale_readings(client):
    """Seed 2: the payload is valid and confident, and 187 sols out of date."""
    payload = client.get("/telemetry/weather_station").json()

    assert payload["status"] == "nominal"
    assert payload["readings"], "the bug is staleness, not emptiness"
    assert payload["sol"] < ground_station.SOL
    assert ground_station.SOL - payload["sol"] > 100, "must be obviously stale"


def test_weather_payload_never_admits_it_is_stale(client):
    """Nothing may tell the model the data is old — the sol number is the only tell."""
    payload = str(client.get("/telemetry/weather_station").json()).lower()

    for giveaway in ("stale", "outdated", "old", "expired", "no recent"):
        assert giveaway not in payload


def test_weather_readings_are_mars_plausible():
    readings = ground_station.TELEMETRY["weather_station"]["readings"]
    assert -80 <= readings["air_temp_c"] <= -20
    assert -80 <= readings["ground_temp_c"] <= -20
    assert 600 <= readings["pressure_pa"] <= 1200


@pytest.mark.parametrize("subsystem", ["power", "wheels", "nav"])
def test_other_subsystems_succeed_first_try_with_mars_plausible_data(client, subsystem):
    response = client.get(f"/telemetry/{subsystem}")

    assert response.status_code == 200
    assert response.json()["sol"] == ground_station.SOL


def test_drill_core_temperature_is_mars_plausible():
    core_temp = ground_station.TELEMETRY["drill"]["readings"]["core_temp_c"]
    assert -80 <= core_temp <= -20


def test_unknown_subsystem_is_a_404(client):
    assert client.get("/telemetry/warp_core").status_code == 404


def test_telemetry_latency_reads_well_on_a_waterfall(client):
    start = time.monotonic()
    client.get("/telemetry/power")
    assert 0.4 <= time.monotonic() - start < 2.0


def test_analyze_runs_the_analyst_and_returns_its_text(client):
    analyst_answer = "Tau is rising; park and ride it out."

    with ground_station.science_analyst.override(
        model=TestModel(custom_output_text=analyst_answer)
    ):
        start = time.monotonic()
        response = client.post("/analyze", json={"question": "dust storm risk?"})
        elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert response.json() == {"analysis": analyst_answer}
    assert elapsed >= 1.5


def test_analyze_requires_a_question(client):
    assert client.post("/analyze", json={}).status_code == 422


def test_analyst_context_is_seeded_with_the_dust_storm():
    assert "dust storm" in ground_station.MISSION_CONTEXT
    assert "tau" in ground_station.MISSION_CONTEXT.lower()
