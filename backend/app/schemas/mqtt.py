from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class MQTTStatusResponse(BaseModel):
    enabled: bool
    status: Literal[
        "disabled",
        "connecting",
        "connected",
        "disconnected",
        "error",
    ]
    topic: str
    qos: int
    tls_enabled: bool
    messages_received: int
    readings_created: int
    duplicate_messages: int
    invalid_messages: int
    last_message_at: datetime | None
    last_error: str | None
