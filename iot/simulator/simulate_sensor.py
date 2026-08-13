"""Preview or publish explicitly labelled FloodGuard sensor readings."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Event
from typing import Iterator


@dataclass(frozen=True)
class SimulatorConfig:
    station_id: str
    count: int
    interval_seconds: float
    baseline_water_level_cm: float
    rainfall_mm: float
    water_level_trend_cm: float
    noise_cm: float
    soil_moisture_percent: float
    battery_percent: float
    seed: int | None


def bounded(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


def generate_readings(config: SimulatorConfig) -> Iterator[dict[str, object]]:
    """Yield schema-valid readings with an explicit simulator source."""

    randomizer = random.Random(config.seed)
    water_level = config.baseline_water_level_cm
    soil_moisture = config.soil_moisture_percent
    battery = config.battery_percent
    emitted = 0

    while config.count == 0 or emitted < config.count:
        if emitted:
            water_level += config.water_level_trend_cm
            water_level += randomizer.uniform(-config.noise_cm, config.noise_cm)
            soil_moisture += config.rainfall_mm * 0.02
            soil_moisture += randomizer.uniform(-0.15, 0.15)
            battery -= randomizer.uniform(0.005, 0.02)

        yield {
            "stationId": config.station_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "waterLevelCm": round(bounded(water_level, -2000, 10_000), 2),
            "rainfallMm": round(bounded(config.rainfall_mm, 0, 5000), 2),
            "soilMoisture": round(bounded(soil_moisture, 0, 100), 2),
            "batteryLevel": round(bounded(battery, 0, 100), 2),
            "source": "simulator",
        }
        emitted += 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Preview simulated readings, or publish them to FloodGuard MQTT "
            "only when --publish is supplied."
        )
    )
    parser.add_argument("--station-id", required=True)
    parser.add_argument("--count", type=int, default=5, help="0 means run forever")
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--water-level-cm", type=float, default=100.0)
    parser.add_argument("--rainfall-mm", type=float, default=0.0)
    parser.add_argument("--trend-cm", type=float, default=0.5)
    parser.add_argument("--noise-cm", type=float, default=0.2)
    parser.add_argument("--soil-moisture", type=float, default=60.0)
    parser.add_argument("--battery", type=float, default=95.0)
    parser.add_argument("--seed", type=int)
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Actually send readings. Without this flag, JSON is previewed only.",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("FLOODGUARD_MQTT_HOST", "127.0.0.1"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("FLOODGUARD_MQTT_PORT", "1884")),
    )
    parser.add_argument(
        "--topic",
        default=os.getenv(
            "FLOODGUARD_MQTT_TOPIC",
            "floodguard/stations/{station_id}/readings",
        ),
    )
    parser.add_argument(
        "--username",
        default=os.getenv("FLOODGUARD_MQTT_USERNAME"),
    )
    parser.add_argument(
        "--tls",
        action="store_true",
        default=os.getenv("FLOODGUARD_MQTT_TLS", "").lower()
        in {"1", "true", "yes"},
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if not args.station_id.strip() or "/" in args.station_id:
        raise ValueError("station ID must be non-empty and cannot contain '/'")
    if args.count < 0:
        raise ValueError("count must be zero or greater")
    if args.interval <= 0:
        raise ValueError("interval must be greater than zero")
    if not 1 <= args.port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    if "{station_id}" not in args.topic:
        raise ValueError("topic must include the {station_id} placeholder")
    if args.noise_cm < 0:
        raise ValueError("noise must be zero or greater")
    for name, value in (
        ("soil moisture", args.soil_moisture),
        ("battery", args.battery),
    ):
        if not 0 <= value <= 100:
            raise ValueError(f"{name} must be between 0 and 100")
    if not -2000 <= args.water_level_cm <= 10_000:
        raise ValueError("water level must be between -2000 and 10000 cm")
    if not 0 <= args.rainfall_mm <= 5000:
        raise ValueError("rainfall must be between 0 and 5000 mm")


def open_mqtt_client(args: argparse.Namespace):
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise RuntimeError(
            "Publishing requires paho-mqtt. Install iot/simulator/requirements.txt."
        ) from exc

    password = os.getenv("FLOODGUARD_MQTT_PASSWORD")
    if args.username and not password:
        raise ValueError(
            "FLOODGUARD_MQTT_PASSWORD is required when a username is configured"
        )

    connected = Event()
    connection_error: list[str] = []
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"floodguard-simulator-{os.getpid()}",
        protocol=mqtt.MQTTv311,
    )

    def on_connect(
        _client,
        _userdata,
        _flags,
        reason_code,
        _properties,
    ) -> None:
        if reason_code.is_failure:
            connection_error.append(str(reason_code))
        connected.set()

    client.on_connect = on_connect
    if args.username:
        client.username_pw_set(args.username, password)
    if args.tls:
        client.tls_set()
    client.connect(args.host, args.port, keepalive=60)
    client.loop_start()
    if not connected.wait(timeout=10):
        client.loop_stop()
        client.disconnect()
        raise RuntimeError("MQTT connection timed out")
    if connection_error:
        client.loop_stop()
        client.disconnect()
        raise RuntimeError(f"MQTT connection rejected: {connection_error[0]}")
    return client


def run(args: argparse.Namespace) -> None:
    config = SimulatorConfig(
        station_id=args.station_id.strip(),
        count=args.count,
        interval_seconds=args.interval,
        baseline_water_level_cm=args.water_level_cm,
        rainfall_mm=args.rainfall_mm,
        water_level_trend_cm=args.trend_cm,
        noise_cm=args.noise_cm,
        soil_moisture_percent=args.soil_moisture,
        battery_percent=args.battery,
        seed=args.seed,
    )
    client = open_mqtt_client(args) if args.publish else None
    topic = args.topic.format(station_id=config.station_id)
    mode = "PUBLISH" if client else "PREVIEW"
    print(f"{mode}: {topic}", file=sys.stderr)

    try:
        for index, reading in enumerate(generate_readings(config)):
            payload = json.dumps(reading, separators=(",", ":"))
            if client:
                result = client.publish(topic, payload, qos=1)
                result.wait_for_publish(timeout=10)
                if result.rc != 0:
                    raise RuntimeError(f"MQTT publish failed with code {result.rc}")
            print(payload, flush=True)
            if config.count == 0 or index + 1 < config.count:
                time.sleep(config.interval_seconds)
    except KeyboardInterrupt:
        print("Simulator stopped.", file=sys.stderr)
    finally:
        if client:
            client.disconnect()
            client.loop_stop()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        validate_args(args)
        run(args)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(1, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
