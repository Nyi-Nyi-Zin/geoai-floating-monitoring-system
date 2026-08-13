from typing import Literal

from pydantic import BaseModel


class DatabaseHealth(BaseModel):
    status: Literal["healthy", "unhealthy", "not_configured"]
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    service: str
    version: str
    environment: str
    database: DatabaseHealth
