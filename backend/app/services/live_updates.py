from fastapi import WebSocket


class LiveUpdateManager:
    """Best-effort in-process live channel for the single-worker local MVP.

    Production multi-worker deployments should replace this fan-out with a
    shared broker such as Redis or MQTT while keeping the same event contract.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        stale: list[WebSocket] = []
        for websocket in tuple(self._connections):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)


live_updates = LiveUpdateManager()
