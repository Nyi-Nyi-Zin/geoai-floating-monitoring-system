from datetime import UTC, datetime

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.hydro_observation import HydroObservationCreate
from app.schemas.sensor_station import SensorReadingCreate, SensorStationCreate
from app.services.weather import get_rainfall_forecast, parse_open_meteo_response
from app.services.risk_rules import classify_water_level
from app.services.mqtt_bridge import (
    decode_sensor_message,
    station_id_from_topic,
)


def test_hydro_observation_requires_a_measurement() -> None:
    with pytest.raises(ValidationError):
        HydroObservationCreate(
            station_id="MAUBIN-01",
            station_name="Maubin gauge",
            observed_at=datetime.now(UTC),
            source="field team",
            geometry={"type": "Point", "coordinates": [95.643, 16.712]},
        )


def test_hydro_observation_requires_point_geometry() -> None:
    with pytest.raises(ValidationError):
        HydroObservationCreate(
            station_id="MAUBIN-01",
            station_name="Maubin gauge",
            observed_at=datetime.now(UTC),
            water_level_m=2.4,
            source="field team",
            geometry={
                "type": "LineString",
                "coordinates": [[95.64, 16.71], [95.65, 16.72]],
            },
        )


def test_parse_open_meteo_response() -> None:
    result = parse_open_meteo_response(
        {
            "latitude": 16.7,
            "longitude": 95.65,
            "timezone": "Asia/Yangon",
            "hourly": {
                "time": ["2026-07-29T12:00"],
                "precipitation": [1.2],
                "precipitation_probability": [75],
            },
            "daily": {
                "time": ["2026-07-29"],
                "precipitation_sum": [18.4],
                "precipitation_probability_max": [90],
            },
        },
        fetched_at=datetime(2026, 7, 29, 5, tzinfo=UTC),
        cached=False,
    )

    assert result.hourly[0].precipitation_mm == 1.2
    assert result.hourly[0].probability_percent == 75
    assert result.daily[0].precipitation_sum_mm == 18.4
    assert result.location.name == "Maubin Township"


def test_weather_fetch_uses_open_meteo_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["forecast_days"] == "3"
        return httpx.Response(
            200,
            json={
                "latitude": 16.7,
                "longitude": 95.65,
                "timezone": "Asia/Yangon",
                "hourly": {
                    "time": ["2026-07-29T12:00"],
                    "precipitation": [0.6],
                    "precipitation_probability": [60],
                },
                "daily": {
                    "time": ["2026-07-29"],
                    "precipitation_sum": [7.5],
                    "precipitation_probability_max": [80],
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = get_rainfall_forecast(3, client=client)

    assert result.daily[0].precipitation_sum_mm == 7.5
    assert result.cached is False


def test_station_thresholds_must_be_ordered() -> None:
    with pytest.raises(ValidationError):
        SensorStationCreate(
            station_id="MAUBIN-01",
            name="Maubin gauge",
            warning_level_cm=300,
            danger_level_cm=250,
            geometry={"type": "Point", "coordinates": [95.643, 16.712]},
        )


def test_esp32_reading_accepts_documented_camel_case_shape() -> None:
    reading = SensorReadingCreate.model_validate(
        {
            "stationId": "MAUBIN-01",
            "timestamp": "2026-07-29T12:00:00+06:30",
            "waterLevelCm": 185.4,
            "rainfallMm": 4.2,
            "soilMoisture": 72,
            "batteryLevel": 88,
        }
    )

    assert reading.station_id == "MAUBIN-01"
    assert reading.water_level_cm == 185.4
    assert reading.battery_percent == 88


def test_esp32_reading_requires_water_or_rain() -> None:
    with pytest.raises(ValidationError):
        SensorReadingCreate.model_validate(
            {
                "stationId": "MAUBIN-01",
                "timestamp": "2026-07-29T12:00:00+06:30",
                "batteryLevel": 88,
            }
        )


def test_sensor_routes_are_in_openapi(client) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/stations" in paths
    assert "/api/v1/stations/{station_id}/readings" in paths
    assert "/api/v1/readings" in paths
    assert "/api/v1/alerts" in paths
    assert "/api/v1/alerts/{alert_id}/acknowledge" in paths


@pytest.mark.parametrize(
    ("water_level_cm", "expected"),
    [
        (149.9, "LOW"),
        (150, "MEDIUM"),
        (200, "HIGH"),
        (250, "CRITICAL"),
    ],
)
def test_water_level_threshold_classification(
    water_level_cm: float,
    expected: str,
) -> None:
    result = classify_water_level(
        water_level_cm,
        warning_level_cm=150,
        danger_level_cm=200,
        critical_level_cm=250,
    )

    assert result.risk_level == expected


def test_water_level_risk_is_unavailable_without_thresholds() -> None:
    result = classify_water_level(
        220,
        warning_level_cm=None,
        danger_level_cm=None,
        critical_level_cm=None,
    )

    assert result.risk_level == "UNAVAILABLE"


def test_live_websocket_contract(client) -> None:
    with client.websocket_connect("/api/v1/ws/live") as websocket:
        message = websocket.receive_json()

    assert message == {
        "type": "connected",
        "channel": "sensor-readings",
    }


def test_mqtt_topic_station_is_extracted() -> None:
    assert (
        station_id_from_topic(
            "floodguard/stations/+/readings",
            "floodguard/stations/MAUBIN-01/readings",
        )
        == "MAUBIN-01"
    )


def test_mqtt_message_uses_same_sensor_schema() -> None:
    reading = decode_sensor_message(
        b"""
        {
          "stationId": "MAUBIN-01",
          "timestamp": "2026-07-29T12:00:00+06:30",
          "waterLevelCm": 185.4,
          "batteryLevel": 88
        }
        """,
        topic_station_id="MAUBIN-01",
    )

    assert reading.station_id == "MAUBIN-01"
    assert reading.water_level_cm == 185.4


def test_mqtt_rejects_station_topic_mismatch() -> None:
    with pytest.raises(ValueError, match="does not match"):
        decode_sensor_message(
            b"""
            {
              "stationId": "OTHER-01",
              "timestamp": "2026-07-29T12:00:00+06:30",
              "waterLevelCm": 185.4
            }
            """,
            topic_station_id="MAUBIN-01",
        )


def test_mqtt_status_reflects_config_without_exposing_credentials(client) -> None:
    response = client.get("/api/v1/mqtt/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is settings.mqtt_enabled
    assert payload["status"] in {
        "disabled",
        "connecting",
        "connected",
        "disconnected",
        "error",
    }
    assert "username" not in payload
    assert "password" not in payload
