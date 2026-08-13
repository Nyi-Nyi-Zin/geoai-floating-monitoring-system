from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.geo_asset import PaginationMeta, validate_geojson_geometry

StationStatus = Literal["active", "offline", "maintenance"]


def _validate_point(value: dict[str, Any]) -> dict[str, Any]:
    geometry = validate_geojson_geometry(value)
    if geometry["type"] != "Point":
        raise ValueError("Sensor station geometry must be a GeoJSON Point")
    return geometry


class SensorStationBase(BaseModel):
    station_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    river_name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    status: StationStatus = "offline"
    warning_level_cm: float | None = Field(default=None, ge=0, le=100_000)
    danger_level_cm: float | None = Field(default=None, ge=0, le=100_000)
    critical_level_cm: float | None = Field(default=None, ge=0, le=100_000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    installed_at: datetime | None = None

    @field_validator("station_id", "name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value

    @model_validator(mode="after")
    def thresholds_are_ordered(self) -> "SensorStationBase":
        threshold_count = sum(
            value is not None
            for value in (
                self.warning_level_cm,
                self.danger_level_cm,
                self.critical_level_cm,
            )
        )
        if threshold_count not in (0, 3):
            raise ValueError(
                "warning, danger, and critical thresholds must be set together"
            )
        if (
            self.warning_level_cm is not None
            and self.danger_level_cm is not None
            and self.warning_level_cm >= self.danger_level_cm
        ):
            raise ValueError("warning_level_cm must be below danger_level_cm")
        if (
            self.danger_level_cm is not None
            and self.critical_level_cm is not None
            and self.danger_level_cm >= self.critical_level_cm
        ):
            raise ValueError("danger_level_cm must be below critical_level_cm")
        return self


class SensorStationCreate(SensorStationBase):
    model_config = ConfigDict(extra="forbid")
    geometry: dict[str, Any]

    @field_validator("geometry")
    @classmethod
    def geometry_is_point(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_point(value)


class SensorStationProperties(SensorStationBase):
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SensorStationFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: str
    geometry: dict[str, Any]
    properties: SensorStationProperties


class SensorStationCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[SensorStationFeature]
    meta: PaginationMeta


class SensorReadingCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    station_id: str = Field(alias="stationId", min_length=1, max_length=100)
    timestamp: datetime
    water_level_cm: float | None = Field(
        default=None,
        alias="waterLevelCm",
        ge=-2000,
        le=10_000,
    )
    rainfall_mm: float | None = Field(
        default=None,
        alias="rainfallMm",
        ge=0,
        le=5000,
    )
    soil_moisture_percent: float | None = Field(
        default=None,
        alias="soilMoisture",
        ge=0,
        le=100,
    )
    battery_percent: float | None = Field(
        default=None,
        alias="batteryLevel",
        ge=0,
        le=100,
    )
    source: str = Field(default="esp32", min_length=1, max_length=255)

    @field_validator("timestamp")
    @classmethod
    def timestamp_has_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone offset")
        return value

    @model_validator(mode="after")
    def has_hydrology_measurement(self) -> "SensorReadingCreate":
        if self.water_level_cm is None and self.rainfall_mm is None:
            raise ValueError("waterLevelCm or rainfallMm is required")
        return self
