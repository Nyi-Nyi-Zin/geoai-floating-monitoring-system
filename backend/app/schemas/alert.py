from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.geo_asset import PaginationMeta

RiskLevel = Literal["MEDIUM", "HIGH", "CRITICAL"]
AlertStatus = Literal["open", "acknowledged"]


class AlertResponse(BaseModel):
    id: UUID
    station_id: str
    observation_id: UUID
    risk_level: RiskLevel
    water_level_cm: float
    threshold_cm: float
    message: str
    status: AlertStatus
    acknowledged_by: str | None
    acknowledged_at: datetime | None
    acknowledgement_notes: str | None
    created_at: datetime


class AlertCollection(BaseModel):
    items: list[AlertResponse]
    meta: PaginationMeta


class AlertAcknowledge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acknowledged_by: str = Field(min_length=1, max_length=255)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("acknowledged_by")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value
