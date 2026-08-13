from fastapi import APIRouter

from app.schemas.mqtt import MQTTStatusResponse
from app.services.mqtt_bridge import mqtt_bridge

router = APIRouter(prefix="/mqtt", tags=["mqtt"])


@router.get(
    "/status",
    response_model=MQTTStatusResponse,
    summary="Get MQTT bridge health without exposing credentials",
)
def mqtt_status() -> MQTTStatusResponse:
    return mqtt_bridge.status()
