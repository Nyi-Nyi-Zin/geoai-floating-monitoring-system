from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from threading import Lock
from typing import Any

import paho.mqtt.client as mqtt
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError

from app.core.config import settings
from app.db.session import SessionLocal
from app.schemas.mqtt import MQTTStatusResponse
from app.schemas.sensor_station import SensorReadingCreate
from app.services.live_updates import live_updates
from app.services.sensor_station import SensorStationService

logger = logging.getLogger(__name__)


def station_id_from_topic(subscription: str, topic: str) -> str | None:
    subscription_parts = subscription.split("/")
    topic_parts = topic.split("/")
    if len(subscription_parts) != len(topic_parts):
        return None
    captured: str | None = None
    for expected, actual in zip(subscription_parts, topic_parts, strict=True):
        if expected == "+":
            captured = actual
        elif expected != actual:
            return None
    return captured


def decode_sensor_message(
    payload: bytes,
    *,
    topic_station_id: str | None = None,
) -> SensorReadingCreate:
    reading = SensorReadingCreate.model_validate_json(payload)
    if topic_station_id and reading.station_id != topic_station_id:
        raise ValueError(
            "Payload stationId does not match the station identifier in the topic"
        )
    return reading


class MQTTBridge:
    def __init__(self) -> None:
        self._client: mqtt.Client | None = None
        self._event_loop: asyncio.AbstractEventLoop | None = None
        self._lock = Lock()
        self._status = "disabled" if not settings.mqtt_enabled else "disconnected"
        self._messages_received = 0
        self._readings_created = 0
        self._duplicate_messages = 0
        self._invalid_messages = 0
        self._last_message_at: datetime | None = None
        self._last_error: str | None = None

    def start(self, event_loop: asyncio.AbstractEventLoop) -> None:
        if not settings.mqtt_enabled:
            return
        if SessionLocal is None:
            self._set_error("DATABASE_URL is required when MQTT is enabled.")
            return

        self._event_loop = event_loop
        try:
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=settings.mqtt_client_id,
                protocol=mqtt.MQTTv311,
                reconnect_on_failure=True,
            )
            client.on_connect = self._on_connect
            client.on_disconnect = self._on_disconnect
            client.on_message = self._on_message
            client.reconnect_delay_set(min_delay=1, max_delay=30)
            if settings.mqtt_username:
                client.username_pw_set(
                    settings.mqtt_username,
                    settings.mqtt_password or None,
                )
            if settings.mqtt_tls_enabled:
                client.tls_set()
            with self._lock:
                self._status = "connecting"
                self._last_error = None
            client.connect_async(
                settings.mqtt_broker_host,
                settings.mqtt_broker_port,
                settings.mqtt_keepalive_seconds,
            )
            client.loop_start()
            self._client = client
        except Exception:
            logger.exception("MQTT bridge failed to start")
            self._set_error("MQTT bridge could not start.")

    def stop(self) -> None:
        client = self._client
        self._client = None
        if client is not None:
            try:
                client.disconnect()
            finally:
                client.loop_stop()
        with self._lock:
            self._status = (
                "disabled" if not settings.mqtt_enabled else "disconnected"
            )

    def status(self) -> MQTTStatusResponse:
        with self._lock:
            return MQTTStatusResponse(
                enabled=settings.mqtt_enabled,
                status=self._status,
                topic=settings.mqtt_topic,
                qos=settings.mqtt_qos,
                tls_enabled=settings.mqtt_tls_enabled,
                messages_received=self._messages_received,
                readings_created=self._readings_created,
                duplicate_messages=self._duplicate_messages,
                invalid_messages=self._invalid_messages,
                last_message_at=self._last_message_at,
                last_error=self._last_error,
            )

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: Any,
        _flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        if reason_code.is_failure:
            self._set_error("MQTT broker rejected the connection.")
            return
        result, _message_id = client.subscribe(
            settings.mqtt_topic,
            qos=settings.mqtt_qos,
        )
        with self._lock:
            if result == mqtt.MQTT_ERR_SUCCESS:
                self._status = "connected"
                self._last_error = None
            else:
                self._status = "error"
                self._last_error = "MQTT topic subscription failed."

    def _on_disconnect(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        _disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        with self._lock:
            if self._client is not None:
                self._status = "disconnected"
                if reason_code.is_failure:
                    self._last_error = "MQTT connection was lost; reconnecting."

    def _on_message(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        now = datetime.now(UTC)
        with self._lock:
            self._messages_received += 1
            self._last_message_at = now

        topic_station_id = station_id_from_topic(
            settings.mqtt_topic,
            message.topic,
        )
        try:
            reading = decode_sensor_message(
                message.payload,
                topic_station_id=topic_station_id,
            )
        except (ValidationError, ValueError) as exc:
            if isinstance(exc, ValidationError):
                errors = exc.errors()
                reason = str(errors[0].get("msg", "schema validation failed"))
            else:
                reason = str(exc)
            logger.warning(
                "Rejected invalid MQTT sensor message on %s: %s",
                message.topic,
                reason,
            )
            with self._lock:
                self._invalid_messages += 1
                self._last_error = f"Invalid MQTT message rejected: {reason}"
            return

        if SessionLocal is None:
            self._set_error("Database session is unavailable.")
            return

        db = SessionLocal()
        try:
            result = SensorStationService(db).ingest_reading(reading)
            with self._lock:
                if result.created:
                    self._readings_created += 1
                else:
                    self._duplicate_messages += 1
                self._last_error = None
            if result.created and self._event_loop is not None:
                asyncio.run_coroutine_threadsafe(
                    live_updates.broadcast(
                        {
                            "type": "sensor_reading",
                            "data": jsonable_encoder(result.feature),
                        }
                    ),
                    self._event_loop,
                )
        except Exception:
            logger.exception("MQTT sensor message could not be stored")
            self._set_error("MQTT sensor message could not be stored.")
        finally:
            db.close()

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._status = "error"
            self._last_error = message


mqtt_bridge = MQTTBridge()
