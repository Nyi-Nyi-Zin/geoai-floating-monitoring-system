from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.geo_asset import PaginationMeta

ScreeningBand = Literal["LOWER", "MODERATE", "HIGH", "VERY_HIGH"]


class ScreeningFactor(BaseModel):
    key: Literal["low_elevation", "waterway_proximity", "flatness"]
    label: str
    normalized_score: float
    weight: float
    contribution: float
    observed_value: float
    unit: str
    interpretation: str


class TerrainScreeningProperties(BaseModel):
    name: str
    source_key: str | None
    screening_score: float
    screening_band: ScreeningBand
    factors: list[ScreeningFactor]
    elevation_mean_m: float
    elevation_percentile: float
    distance_to_waterway_m: float
    local_relief_m: float
    source_resolution_m: int
    cell_size_m: int
    methodology_version: Literal["terrain-screening-v1"]
    screening_only: Literal[True] = True


class TerrainScreeningFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: UUID
    geometry: dict | None
    properties: TerrainScreeningProperties


class TerrainScreeningSummary(BaseModel):
    total_cells: int
    returned_cells: int
    mean_score: float
    band_counts: dict[ScreeningBand, int]
    generated_at: datetime


class TerrainScreeningMethodology(BaseModel):
    version: Literal["terrain-screening-v1"]
    title: str
    weights: dict[str, float]
    band_thresholds: dict[str, str]
    input_data: list[str]
    limitations: list[str]


class TerrainScreeningCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[TerrainScreeningFeature]
    meta: PaginationMeta
    summary: TerrainScreeningSummary
    methodology: TerrainScreeningMethodology


class TerrainScreeningIndexItem(BaseModel):
    id: UUID
    screening_score: float
    screening_band: ScreeningBand
    low_elevation_score: float
    waterway_proximity_score: float
    flatness_score: float


class TerrainScreeningIndex(BaseModel):
    items: list[TerrainScreeningIndexItem]
    summary: TerrainScreeningSummary
    methodology: TerrainScreeningMethodology


class LandCoverClassSummary(BaseModel):
    class_code: int
    class_name: str
    color: str
    pixel_count: int
    percentage: float


class LandCoverSummary(BaseModel):
    status: Literal["available", "unavailable"]
    dataset_id: str
    source_name: str
    reference_year: int
    source_resolution_m: int
    cells_enriched: int
    total_pixels: int
    classes: list[LandCoverClassSummary]
    attribution: str
    limitations: list[str]
