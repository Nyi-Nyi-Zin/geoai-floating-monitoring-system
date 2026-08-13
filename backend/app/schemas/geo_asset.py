import math
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.validation import explain_validity

SUPPORTED_GEOMETRY_TYPES = {
    "Point",
    "MultiPoint",
    "LineString",
    "MultiLineString",
    "Polygon",
    "MultiPolygon",
    "GeometryCollection",
}


def validate_geojson_geometry(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseGeometry):
        geometry = value
    elif isinstance(value, dict):
        geometry_type = value.get("type")
        if geometry_type == "Feature":
            raise ValueError("Provide a GeoJSON geometry, not a Feature")
        if geometry_type not in SUPPORTED_GEOMETRY_TYPES:
            supported = ", ".join(sorted(SUPPORTED_GEOMETRY_TYPES))
            raise ValueError(f"Unsupported geometry type; expected one of: {supported}")
        try:
            geometry = shape(value)
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid GeoJSON geometry: {exc}") from exc
    else:
        raise ValueError("Geometry must be a GeoJSON object")

    if geometry.is_empty:
        raise ValueError("Geometry must not be empty")
    if not geometry.is_valid:
        raise ValueError(f"Invalid geometry: {explain_validity(geometry)}")

    min_x, min_y, max_x, max_y = geometry.bounds
    if not all(math.isfinite(number) for number in geometry.bounds):
        raise ValueError("Geometry coordinates must be finite numbers")
    if min_x < -180 or max_x > 180 or min_y < -90 or max_y > 90:
        raise ValueError(
            "Geometry coordinates must use WGS84 longitude [-180, 180] "
            "and latitude [-90, 90]"
        )

    return mapping(geometry)


class GeoAssetBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    asset_type: str = Field(min_length=1, max_length=100)
    source_key: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "asset_type")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value


class GeoAssetCreate(GeoAssetBase):
    geometry: dict[str, Any]

    @field_validator("geometry")
    @classmethod
    def geometry_is_valid(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_geojson_geometry(value)


class GeoAssetImportProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    asset_type: str = Field(min_length=1, max_length=100)
    source_key: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "asset_type")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value


class GeoAssetImportFeature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["Feature"]
    geometry: dict[str, Any]
    properties: GeoAssetImportProperties

    @field_validator("geometry")
    @classmethod
    def geometry_is_valid(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_geojson_geometry(value)


class GeoAssetImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["FeatureCollection"]
    name: str | None = Field(default=None, max_length=255)
    features: list[GeoAssetImportFeature] = Field(min_length=1, max_length=1000)


class GeoAssetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    asset_type: str | None = Field(default=None, min_length=1, max_length=100)
    source_key: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    geometry: dict[str, Any] | None = None
    properties: dict[str, Any] | None = None

    @field_validator("name", "asset_type")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value

    @field_validator("geometry")
    @classmethod
    def geometry_is_valid(
        cls,
        value: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return validate_geojson_geometry(value) if value is not None else None

    @model_validator(mode="after")
    def has_at_least_one_change(self) -> "GeoAssetUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        return self


class GeoAssetFeatureProperties(BaseModel):
    name: str
    asset_type: str
    source_key: str | None
    description: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class GeoAssetFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: UUID
    geometry: dict[str, Any]
    properties: GeoAssetFeatureProperties


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    pages: int


class GeoAssetFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[GeoAssetFeature]
    meta: PaginationMeta
