from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.geo_asset import PaginationMeta, validate_geojson_geometry

QualityStatus = Literal["unverified", "provisional", "verified", "rejected"]


def _validate_point(value: dict) -> dict:
    geometry = validate_geojson_geometry(value)
    if geometry["type"] != "Point":
        raise ValueError("Hydrology station geometry must be a GeoJSON Point")
    return geometry


class HydroObservationBase(BaseModel):
    station_id: str = Field(min_length=1, max_length=100)
    station_name: str = Field(min_length=1, max_length=255)
    observed_at: datetime
    rainfall_mm: float | None = Field(default=None, ge=0, le=5000)
    water_level_m: float | None = Field(default=None, ge=-20, le=100)
    discharge_m3s: float | None = Field(default=None, ge=0, le=1_000_000)
    soil_moisture_percent: float | None = Field(default=None, ge=0, le=100)
    battery_percent: float | None = Field(default=None, ge=0, le=100)
    source: str = Field(min_length=1, max_length=255)
    quality_status: QualityStatus = "unverified"
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("station_id", "station_name", "source")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value

    @field_validator("observed_at")
    @classmethod
    def observed_at_has_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone offset")
        return value

    @model_validator(mode="after")
    def has_measurement(self) -> "HydroObservationBase":
        if (
            self.rainfall_mm is None
            and self.water_level_m is None
            and self.discharge_m3s is None
        ):
            raise ValueError(
                "At least one rainfall, water-level, or discharge value is required"
            )
        return self


class HydroObservationCreate(HydroObservationBase):
    model_config = ConfigDict(extra="forbid")
    geometry: dict

    @field_validator("geometry")
    @classmethod
    def geometry_is_point(cls, value: dict) -> dict:
        return _validate_point(value)


class HydroObservationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quality_status: QualityStatus | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def has_change(self) -> "HydroObservationUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        return self


class HydroObservationProperties(HydroObservationBase):
    created_at: datetime
    updated_at: datetime


class HydroObservationFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: UUID
    geometry: dict
    properties: HydroObservationProperties


class HydroObservationCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[HydroObservationFeature]
    meta: PaginationMeta
