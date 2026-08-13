from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime

from geoalchemy2.shape import to_shape
from sqlalchemy import Float, cast, func, select
from sqlalchemy.orm import Session

from app.models.geo_asset import GeoAsset
from app.schemas.flood_screening import (
    LandCoverClassSummary,
    LandCoverSummary,
    ScreeningBand,
    ScreeningFactor,
    TerrainScreeningCollection,
    TerrainScreeningFeature,
    TerrainScreeningIndex,
    TerrainScreeningIndexItem,
    TerrainScreeningMethodology,
    TerrainScreeningProperties,
    TerrainScreeningSummary,
)
from app.schemas.geo_asset import PaginationMeta

METHODOLOGY_VERSION = "terrain-screening-v1"
FACTOR_WEIGHTS = {
    "low_elevation": 0.55,
    "waterway_proximity": 0.30,
    "flatness": 0.15,
}
LAND_COVER_DATASET_ID = "maubin-esa-worldcover-10m-2021-v200"
LAND_COVER_CLASSES = {
    10: ("Tree cover", "#006400"),
    20: ("Shrubland", "#ffbb22"),
    30: ("Grassland", "#ffff4c"),
    40: ("Cropland", "#f096ff"),
    50: ("Built-up", "#fa0000"),
    60: ("Bare / sparse vegetation", "#b4b4b4"),
    70: ("Snow and ice", "#f0f0f0"),
    80: ("Permanent water bodies", "#0064c8"),
    90: ("Herbaceous wetland", "#0096a0"),
    95: ("Mangroves", "#00cf75"),
    100: ("Moss and lichen", "#fae6a0"),
}


@dataclass(frozen=True)
class ScreeningInputs:
    elevation_mean_m: float
    elevation_percentile: float
    distance_to_waterway_m: float
    distance_percentile: float
    local_relief_m: float
    relief_percentile: float


@dataclass(frozen=True)
class ScreeningResult:
    score: float
    band: ScreeningBand
    factors: list[ScreeningFactor]


def screening_band(score: float) -> ScreeningBand:
    if score >= 75:
        return "VERY_HIGH"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MODERATE"
    return "LOWER"


def calculate_screening(inputs: ScreeningInputs) -> ScreeningResult:
    """Calculate a relative, explainable terrain index—not flood probability."""

    factor_values = {
        "low_elevation": max(0.0, min(100.0, 100 - inputs.elevation_percentile)),
        "waterway_proximity": max(
            0.0,
            min(100.0, 100 - inputs.distance_percentile),
        ),
        "flatness": max(0.0, min(100.0, 100 - inputs.relief_percentile)),
    }
    factor_details = {
        "low_elevation": (
            "Low relative elevation",
            inputs.elevation_mean_m,
            "m",
            "Lower cells receive a higher screening contribution.",
        ),
        "waterway_proximity": (
            "Waterway proximity",
            inputs.distance_to_waterway_m,
            "m",
            "Cells nearer mapped rivers or canals receive a higher contribution.",
        ),
        "flatness": (
            "Local flatness",
            inputs.local_relief_m,
            "m relief",
            "Flatter cells receive a higher screening contribution.",
        ),
    }
    factors: list[ScreeningFactor] = []
    for key in ("low_elevation", "waterway_proximity", "flatness"):
        label, observed_value, unit, interpretation = factor_details[key]
        normalized = factor_values[key]
        weight = FACTOR_WEIGHTS[key]
        factors.append(
            ScreeningFactor(
                key=key,
                label=label,
                normalized_score=round(normalized, 1),
                weight=weight,
                contribution=round(normalized * weight, 1),
                observed_value=round(observed_value, 2),
                unit=unit,
                interpretation=interpretation,
            )
        )

    score = round(sum(factor.contribution for factor in factors), 1)
    return ScreeningResult(
        score=score,
        band=screening_band(score),
        factors=factors,
    )


def methodology() -> TerrainScreeningMethodology:
    return TerrainScreeningMethodology(
        version=METHODOLOGY_VERSION,
        title="Relative terrain and drainage susceptibility screening",
        weights=FACTOR_WEIGHTS,
        band_thresholds={
            "LOWER": "score below 25",
            "MODERATE": "score from 25 to below 50",
            "HIGH": "score from 50 to below 75",
            "VERY_HIGH": "score 75 or above",
        },
        input_data=[
            "Copernicus DEM GLO-30 elevation summarized to 500 m cells",
            "OpenStreetMap mapped rivers and canals",
            "Maubin Township boundary",
        ],
        limitations=[
            "This relative index is not flood probability, depth, or arrival time.",
            "It does not include levees, drainage capacity, buildings, soil, tides, "
            "river stage, observed rainfall, or historical flood labels.",
            "OpenStreetMap waterways may be incomplete and the DEM is a surface "
            "model summarized to 500 m cells.",
            "Use field verification and official warnings for operational decisions.",
        ],
    )


class FloodScreeningService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def land_cover_summary(self) -> LandCoverSummary:
        rows = self.db.scalars(
            select(GeoAsset.properties).where(
                GeoAsset.asset_type == "terrain_cell",
                GeoAsset.properties.has_key(  # noqa: W601
                    "land_cover_dataset_id"
                ),
            )
        ).all()
        class_counts: Counter[int] = Counter()
        total_pixels = 0
        for properties in rows:
            pixel_count = int(properties.get("land_cover_pixel_count", 0))
            percentages = properties.get("land_cover_percentages", {})
            total_pixels += pixel_count
            for raw_code, percentage in percentages.items():
                class_counts[int(raw_code)] += round(
                    pixel_count * float(percentage) / 100
                )

        counted_pixels = sum(class_counts.values())
        classes = [
            LandCoverClassSummary(
                class_code=code,
                class_name=LAND_COVER_CLASSES.get(
                    code,
                    ("Unknown", "#888888"),
                )[0],
                color=LAND_COVER_CLASSES.get(
                    code,
                    ("Unknown", "#888888"),
                )[1],
                pixel_count=count,
                percentage=(
                    round(100 * count / counted_pixels, 2)
                    if counted_pixels
                    else 0.0
                ),
            )
            for code, count in class_counts.most_common()
        ]
        return LandCoverSummary(
            status="available" if rows else "unavailable",
            dataset_id=LAND_COVER_DATASET_ID,
            source_name="ESA WorldCover 10 m 2021 v200",
            reference_year=2021,
            source_resolution_m=10,
            cells_enriched=len(rows),
            total_pixels=total_pixels,
            classes=classes,
            attribution=(
                "© ESA WorldCover project / Contains modified Copernicus "
                "Sentinel data (2021) processed by ESA WorldCover consortium"
            ),
            limitations=[
                "WorldCover is a 2021 global classification, not current flood "
                "water or a local drainage survey.",
                "Class shares are descriptive inputs and are not yet weighted "
                "inside the terrain susceptibility score.",
                "Per-cell class percentages are rounded to two decimals before "
                "this township summary is reconstructed.",
            ],
        )

    def terrain(
        self,
        *,
        page: int,
        page_size: int,
        band: ScreeningBand | None,
        include_geometry: bool,
    ) -> TerrainScreeningCollection:
        distance = cast(
            GeoAsset.properties["distance_to_waterway_m"].astext,
            Float,
        )
        relief = cast(
            GeoAsset.properties["local_relief_m"].astext,
            Float,
        )
        rows = self.db.execute(
            select(
                GeoAsset,
                (
                    func.percent_rank().over(order_by=distance) * 100
                ).label("distance_percentile"),
                (
                    func.percent_rank().over(order_by=relief) * 100
                ).label("relief_percentile"),
            ).where(
                GeoAsset.asset_type == "terrain_cell",
                GeoAsset.properties.has_key("elevation_percentile"),  # noqa: W601
                GeoAsset.properties.has_key("distance_to_waterway_m"),  # noqa: W601
                GeoAsset.properties.has_key("local_relief_m"),  # noqa: W601
            )
        ).all()

        scored: list[tuple[GeoAsset, ScreeningResult]] = []
        for asset, distance_percentile, relief_percentile in rows:
            properties = asset.properties
            result = calculate_screening(
                ScreeningInputs(
                    elevation_mean_m=float(properties["elevation_mean_m"]),
                    elevation_percentile=float(properties["elevation_percentile"]),
                    distance_to_waterway_m=float(
                        properties["distance_to_waterway_m"]
                    ),
                    distance_percentile=float(distance_percentile),
                    local_relief_m=float(properties["local_relief_m"]),
                    relief_percentile=float(relief_percentile),
                )
            )
            scored.append((asset, result))

        scored.sort(key=lambda item: (-item[1].score, str(item[0].id)))
        all_band_counts: Counter[ScreeningBand] = Counter(
            result.band for _, result in scored
        )
        filtered = [
            item for item in scored if band is None or item[1].band == band
        ]
        total = len(filtered)
        start = (page - 1) * page_size
        page_rows = filtered[start : start + page_size]
        features = [
            self._to_feature(
                asset,
                result,
                include_geometry=include_geometry,
            )
            for asset, result in page_rows
        ]
        mean_score = (
            round(sum(result.score for _, result in scored) / len(scored), 1)
            if scored
            else 0.0
        )
        return TerrainScreeningCollection(
            features=features,
            meta=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                pages=math.ceil(total / page_size) if total else 0,
            ),
            summary=TerrainScreeningSummary(
                total_cells=len(scored),
                returned_cells=len(features),
                mean_score=mean_score,
                band_counts={
                    current_band: all_band_counts[current_band]
                    for current_band in (
                        "LOWER",
                        "MODERATE",
                        "HIGH",
                        "VERY_HIGH",
                    )
                },
                generated_at=datetime.now(UTC),
            ),
            methodology=methodology(),
        )

    def terrain_index(self) -> TerrainScreeningIndex:
        """Return map-ready scores without geometry or repeated factor prose."""

        elevation_mean = cast(
            GeoAsset.properties["elevation_mean_m"].astext,
            Float,
        )
        elevation_percentile = cast(
            GeoAsset.properties["elevation_percentile"].astext,
            Float,
        )
        distance = cast(
            GeoAsset.properties["distance_to_waterway_m"].astext,
            Float,
        )
        relief = cast(
            GeoAsset.properties["local_relief_m"].astext,
            Float,
        )
        rows = self.db.execute(
            select(
                GeoAsset.id,
                elevation_mean.label("elevation_mean_m"),
                elevation_percentile.label("elevation_percentile"),
                distance.label("distance_to_waterway_m"),
                (
                    func.percent_rank().over(order_by=distance) * 100
                ).label("distance_percentile"),
                relief.label("local_relief_m"),
                (
                    func.percent_rank().over(order_by=relief) * 100
                ).label("relief_percentile"),
            ).where(
                GeoAsset.asset_type == "terrain_cell",
                GeoAsset.properties.has_key("elevation_percentile"),  # noqa: W601
                GeoAsset.properties.has_key("distance_to_waterway_m"),  # noqa: W601
                GeoAsset.properties.has_key("local_relief_m"),  # noqa: W601
            )
        ).mappings()

        items: list[TerrainScreeningIndexItem] = []
        for row in rows:
            result = calculate_screening(
                ScreeningInputs(
                    elevation_mean_m=float(row["elevation_mean_m"]),
                    elevation_percentile=float(row["elevation_percentile"]),
                    distance_to_waterway_m=float(row["distance_to_waterway_m"]),
                    distance_percentile=float(row["distance_percentile"]),
                    local_relief_m=float(row["local_relief_m"]),
                    relief_percentile=float(row["relief_percentile"]),
                )
            )
            factors = {factor.key: factor for factor in result.factors}
            items.append(
                TerrainScreeningIndexItem(
                    id=row["id"],
                    screening_score=result.score,
                    screening_band=result.band,
                    low_elevation_score=factors["low_elevation"].normalized_score,
                    waterway_proximity_score=factors[
                        "waterway_proximity"
                    ].normalized_score,
                    flatness_score=factors["flatness"].normalized_score,
                )
            )

        items.sort(key=lambda item: (-item.screening_score, str(item.id)))
        counts: Counter[ScreeningBand] = Counter(
            item.screening_band for item in items
        )
        mean_score = (
            round(sum(item.screening_score for item in items) / len(items), 1)
            if items
            else 0.0
        )
        return TerrainScreeningIndex(
            items=items,
            summary=TerrainScreeningSummary(
                total_cells=len(items),
                returned_cells=len(items),
                mean_score=mean_score,
                band_counts={
                    current_band: counts[current_band]
                    for current_band in (
                        "LOWER",
                        "MODERATE",
                        "HIGH",
                        "VERY_HIGH",
                    )
                },
                generated_at=datetime.now(UTC),
            ),
            methodology=methodology(),
        )

    @staticmethod
    def _to_feature(
        asset: GeoAsset,
        result: ScreeningResult,
        *,
        include_geometry: bool,
    ) -> TerrainScreeningFeature:
        properties = asset.properties
        return TerrainScreeningFeature(
            id=asset.id,
            geometry=(
                to_shape(asset.geometry).__geo_interface__
                if include_geometry
                else None
            ),
            properties=TerrainScreeningProperties(
                name=asset.name,
                source_key=asset.source_key,
                screening_score=result.score,
                screening_band=result.band,
                factors=result.factors,
                elevation_mean_m=float(properties["elevation_mean_m"]),
                elevation_percentile=float(properties["elevation_percentile"]),
                distance_to_waterway_m=float(
                    properties["distance_to_waterway_m"]
                ),
                local_relief_m=float(properties["local_relief_m"]),
                source_resolution_m=int(properties["source_resolution_m"]),
                cell_size_m=int(properties["cell_size_m"]),
                methodology_version=METHODOLOGY_VERSION,
            ),
        )
