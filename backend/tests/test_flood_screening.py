from unittest.mock import MagicMock

import pytest

from app.services.flood_screening import (
    FACTOR_WEIGHTS,
    FloodScreeningService,
    ScreeningInputs,
    calculate_screening,
    methodology,
    screening_band,
)


def test_screening_score_exposes_weighted_contributions() -> None:
    result = calculate_screening(
        ScreeningInputs(
            elevation_mean_m=0.5,
            elevation_percentile=10,
            distance_to_waterway_m=80,
            distance_percentile=20,
            local_relief_m=0.1,
            relief_percentile=30,
        )
    )

    assert result.score == pytest.approx(84.0)
    assert result.band == "VERY_HIGH"
    assert sum(factor.contribution for factor in result.factors) == pytest.approx(
        result.score
    )
    assert {factor.key for factor in result.factors} == {
        "low_elevation",
        "waterway_proximity",
        "flatness",
    }


def test_screening_extremes_are_bounded() -> None:
    highest = calculate_screening(
        ScreeningInputs(
            elevation_mean_m=0,
            elevation_percentile=-50,
            distance_to_waterway_m=0,
            distance_percentile=-10,
            local_relief_m=0,
            relief_percentile=-1,
        )
    )
    lower = calculate_screening(
        ScreeningInputs(
            elevation_mean_m=20,
            elevation_percentile=150,
            distance_to_waterway_m=5000,
            distance_percentile=110,
            local_relief_m=10,
            relief_percentile=200,
        )
    )

    assert highest.score == 100
    assert highest.band == "VERY_HIGH"
    assert lower.score == 0
    assert lower.band == "LOWER"


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0, "LOWER"),
        (24.9, "LOWER"),
        (25, "MODERATE"),
        (49.9, "MODERATE"),
        (50, "HIGH"),
        (74.9, "HIGH"),
        (75, "VERY_HIGH"),
        (100, "VERY_HIGH"),
    ],
)
def test_screening_band_boundaries(score: float, expected: str) -> None:
    assert screening_band(score) == expected


def test_methodology_is_explicit_about_limits() -> None:
    details = methodology()

    assert sum(FACTOR_WEIGHTS.values()) == pytest.approx(1)
    assert details.version == "terrain-screening-v1"
    assert any("not flood probability" in item for item in details.limitations)


def test_land_cover_summary_aggregates_enriched_cells() -> None:
    db = MagicMock()
    db.scalars.return_value.all.return_value = [
        {
            "land_cover_pixel_count": 100,
            "land_cover_percentages": {"40": 60, "80": 40},
        },
        {
            "land_cover_pixel_count": 50,
            "land_cover_percentages": {"40": 20, "90": 80},
        },
    ]

    summary = FloodScreeningService(db).land_cover_summary()

    assert summary.status == "available"
    assert summary.cells_enriched == 2
    assert summary.total_pixels == 150
    assert [(item.class_code, item.pixel_count) for item in summary.classes] == [
        (40, 70),
        (80, 40),
        (90, 40),
    ]
    assert any("not current flood water" in item for item in summary.limitations)


def test_openapi_lists_terrain_screening_endpoint(client) -> None:
    openapi = client.get("/openapi.json").json()

    assert "/api/v1/flood-screening/terrain" in openapi["paths"]
    assert "/api/v1/flood-screening/land-cover/summary" in openapi["paths"]
