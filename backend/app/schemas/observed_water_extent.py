from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.geo_asset import PaginationMeta, validate_geojson_geometry


class ObservedWaterExtentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    observed_at: date
    source: str = Field(min_length=1, max_length=100)
    method: str = Field(min_length=1, max_length=255)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    event_id: str | None = Field(default=None, min_length=1, max_length=120)
    source_name: str = Field(min_length=1, max_length=255)
    source_url: str = Field(min_length=1, max_length=2000, pattern=r"^https://")
    license_name: str = Field(min_length=1, max_length=255)
    notes: str | None = Field(default=None, max_length=10_000)
    geometry: dict[str, Any]
    properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_key", "name", "source", "method", "source_name", "license_name")
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
            raise ValueError(
                "Observed water extent geometry must be Polygon or MultiPolygon"
            )
        return geometry


class ObservedWaterExtentProperties(BaseModel):
    source_key: str
    name: str
    observed_at: date
    source: str
    method: str
    confidence_score: float | None
    event_id: str | None
    source_name: str
    source_url: str
    license_name: str
    notes: str | None
    area_km2: float
    metadata: dict[str, Any]
    product_type: Literal["observed_water_extent"] = "observed_water_extent"
    created_at: datetime
    updated_at: datetime


class ObservedWaterExtentFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: UUID
    geometry: dict[str, Any]
    properties: ObservedWaterExtentProperties


class ObservedWaterExtentSummary(BaseModel):
    total_features: int
    observation_count: int
    total_area_km2: float
    observed_from: date | None
    observed_to: date | None
    latest_observed_at: date | None
    latest_source: str | None
    latest_method: str | None


class ObservedWaterExtentCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[ObservedWaterExtentFeature]
    meta: PaginationMeta
    summary: ObservedWaterExtentSummary
    limitations: list[str]
