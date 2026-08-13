from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.geo_asset import PaginationMeta, validate_geojson_geometry

DataKind = Literal["raster", "vector", "timeseries", "service"]
DataQualityStatus = Literal["verified", "limited", "unreviewed", "deprecated"]


class DataLayerBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    data_kind: DataKind
    provider: str = Field(min_length=1, max_length=255)
    source_url: str = Field(min_length=1, max_length=2000, pattern=r"^https://")
    license_name: str = Field(min_length=1, max_length=255)
    license_url: str | None = Field(
        default=None,
        max_length=2000,
        pattern=r"^https://",
    )
    attribution: str = Field(min_length=1, max_length=5000)
    usage_constraints: str | None = Field(default=None, max_length=10_000)
    spatial_resolution_m: float | None = Field(default=None, gt=0)
    temporal_coverage_start: datetime | None = None
    temporal_coverage_end: datetime | None = None
    update_frequency: str | None = Field(default=None, max_length=255)
    quality_status: DataQualityStatus
    quality_notes: str = Field(min_length=1, max_length=10_000)
    provenance: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    @field_validator("name", "category", "provider", "license_name", "attribution")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value

    @field_validator("temporal_coverage_start", "temporal_coverage_end")
    @classmethod
    def temporal_values_have_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("Temporal coverage must include a timezone offset")
        return value

    @model_validator(mode="after")
    def temporal_range_is_ordered(self) -> "DataLayerBase":
        if (
            self.temporal_coverage_start is not None
            and self.temporal_coverage_end is not None
            and self.temporal_coverage_start > self.temporal_coverage_end
        ):
            raise ValueError(
                "temporal_coverage_start must not be after temporal_coverage_end"
            )
        return self


class DataLayerCreate(DataLayerBase):
    model_config = ConfigDict(extra="forbid")

    layer_key: str = Field(
        min_length=1,
        max_length=150,
        pattern=r"^[a-z0-9][a-z0-9._:-]*$",
    )
    coverage: dict[str, Any] | None = None

    @field_validator("coverage")
    @classmethod
    def coverage_is_valid(
        cls,
        value: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return validate_geojson_geometry(value) if value is not None else None


class DataLayerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    data_kind: DataKind | None = None
    provider: str | None = Field(default=None, min_length=1, max_length=255)
    source_url: str | None = Field(
        default=None,
        min_length=1,
        max_length=2000,
        pattern=r"^https://",
    )
    license_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    license_url: str | None = Field(
        default=None,
        max_length=2000,
        pattern=r"^https://",
    )
    attribution: str | None = Field(default=None, min_length=1, max_length=5000)
    usage_constraints: str | None = Field(default=None, max_length=10_000)
    coverage: dict[str, Any] | None = None
    spatial_resolution_m: float | None = Field(default=None, gt=0)
    temporal_coverage_start: datetime | None = None
    temporal_coverage_end: datetime | None = None
    update_frequency: str | None = Field(default=None, max_length=255)
    quality_status: DataQualityStatus | None = None
    quality_notes: str | None = Field(
        default=None,
        min_length=1,
        max_length=10_000,
    )
    provenance: dict[str, Any] | None = None
    is_active: bool | None = None

    @field_validator("coverage")
    @classmethod
    def coverage_is_valid(
        cls,
        value: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return validate_geojson_geometry(value) if value is not None else None

    @field_validator("temporal_coverage_start", "temporal_coverage_end")
    @classmethod
    def temporal_values_have_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("Temporal coverage must include a timezone offset")
        return value

    @model_validator(mode="after")
    def has_a_change_and_ordered_temporal_range(self) -> "DataLayerUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        if (
            self.temporal_coverage_start is not None
            and self.temporal_coverage_end is not None
            and self.temporal_coverage_start > self.temporal_coverage_end
        ):
            raise ValueError(
                "temporal_coverage_start must not be after temporal_coverage_end"
            )
        return self


class DataLayerProperties(DataLayerBase):
    layer_key: str
    created_at: datetime
    updated_at: datetime


class DataLayerFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: UUID
    geometry: dict[str, Any] | None
    properties: DataLayerProperties


class DataLayerCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[DataLayerFeature]
    meta: PaginationMeta
    quality_counts: dict[DataQualityStatus, int]
