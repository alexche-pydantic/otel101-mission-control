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


def test_weather_serves_both_sites(client):
    """Seed 2: the service knows Houston and Elysium Base. Neither is faked."""
    houston = client.get("/weather/Houston, Texas").json()
    elysium = client.get("/weather/Elysium Base").json()

    assert houston["site"] == "Houston, TX"
    assert elysium["site"] == "Elysium Base"


def test_houston_weather_is_earth_like_and_elysium_is_not(client):
    """The whole beat rests on these two being unmistakably different planets."""
    houston = client.get("/weather/Houston, Texas").json()
    elysium = client.get("/weather/Elysium Base").json()

    assert houston["air_temp_c"] > 15, "Houston must read as obviously Earth"
    assert -80 <= elysium["air_temp_c"] <= -20, "Elysium must read as obviously Mars"


def test_weather_matches_on_a_partial_location_string(client):
    """The model says 'Houston, Texas'; the station is keyed 'houston'."""
    assert client.get("/weather/Houston, Texas").status_code == 200
    assert client.get("/weather/houston").status_code == 200


def test_unknown_weather_site_is_a_404(client):
    assert client.get("/weather/Baikonur").status_code == 404


def test_weather_is_no_longer_a_telemetry_subsystem():
    """Weather moved to its own tool so the model must choose a location."""
    assert "weather_station" not in ground_station.TELEMETRY


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
