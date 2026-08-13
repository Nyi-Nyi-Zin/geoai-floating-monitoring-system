from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.geo_asset import PaginationMeta, validate_geojson_geometry

FloodClassification = Literal["flood", "possible_flood"]
FloodConfidence = Literal["high", "moderate", "low", "unknown"]


class FloodExtentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str = Field(min_length=1, max_length=255)
    event_name: str = Field(min_length=1, max_length=255)
    event_id: str | None = Field(default=None, min_length=1, max_length=120)
    observed_date: date
    observed_start_date: date | None = None
    observed_end_date: date | None = None
    sensor: str = Field(min_length=1, max_length=100)
    classification: FloodClassification = "flood"
    confidence: FloodConfidence = "unknown"
    field_validated: bool = False
    source_name: str = Field(min_length=1, max_length=255)
    source_url: str = Field(min_length=1, max_length=2000, pattern=r"^https://")
    license_name: str = Field(min_length=1, max_length=255)
    notes: str | None = Field(default=None, max_length=10_000)
    geometry: dict[str, Any]
    properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "source_key",
        "event_name",
        "sensor",
        "source_name",
        "license_name",
    )
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value

    @field_validator("geometry")
    @classmethod
    def geometry_is_polygonal(cls, value: dict[str, Any]) -> dict[str, Any]:
        geometry = validate_geojson_geometry(value)
        if geometry["type"] not in {"Polygon", "MultiPolygon"}:
            raise ValueError("Flood extent geometry must be Polygon or MultiPolygon")
        return geometry

    @model_validator(mode="after")
    def event_dates_are_ordered(self) -> "FloodExtentCreate":
        start = self.observed_start_date or self.observed_date
        if self.observed_end_date is not None and self.observed_end_date < start:
            raise ValueError("observed_end_date must be on or after the event start")
        return self


class FloodExtentProperties(BaseModel):
    source_key: str
    event_name: str
    event_id: str | None
    observed_date: date
    observed_start_date: date | None
    observed_end_date: date | None
    sensor: str
    classification: FloodClassification
    confidence: FloodConfidence
    field_validated: bool
    source_name: str
    source_url: str
    license_name: str
    notes: str | None
    area_km2: float
    metadata: dict[str, Any]
    training_label: Literal[True] = True
    created_at: datetime
    updated_at: datetime


class FloodExtentFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: UUID
    geometry: dict[str, Any]
    properties: FloodExtentProperties


class FloodExtentSummary(BaseModel):
    total_features: int
    event_count: int
    total_area_km2: float
    observed_from: date | None
    observed_to: date | None
    field_validated_features: int


class FloodExtentCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[FloodExtentFeature]
    meta: PaginationMeta
    summary: FloodExtentSummary
    limitations: list[str]
