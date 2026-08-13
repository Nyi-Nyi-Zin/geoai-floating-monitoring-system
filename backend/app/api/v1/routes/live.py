from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.services.live_updates import live_updates

router = APIRouter(tags=["live-updates"])


@router.websocket("/ws/live")
async def live_sensor_updates(websocket: WebSocket) -> None:
    origin = websocket.headers.get("origin")
    if origin and origin not in settings.cors_origin_list:
        await websocket.close(code=1008, reason="Origin is not allowed")
        return

    await live_updates.connect(websocket)
    await websocket.send_json(
        {
            "type": "connected",
            "channel": "sensor-readings",
        }
    )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        live_updates.disconnect(websocket)
