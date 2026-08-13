from datetime import date

import pytest
from pydantic import ValidationError
from shapely.geometry import Polygon, mapping

from app.schemas.observed_water_extent import ObservedWaterExtentCreate


def valid_payload(**changes):
    payload = {
        "source_key": "maubin:observed-water:sentinel-2:2026-08-14:001",
        "name": "Observed water · Sentinel-2 · 2026-08-14",
        "observed_at": date(2026, 8, 14),
        "source": "Sentinel-2",
        "method": "OpenGeoAI water segmentation",
        "confidence_score": 0.82,
        "source_name": "OpenGeoAI",
        "source_url": "https://opengeoai.org/",
        "license_name": "See source dataset licence",
        "geometry": mapping(
            Polygon(
                [
                    (95.60, 16.60),
                    (95.61, 16.60),
                    (95.61, 16.61),
                    (95.60, 16.61),
                    (95.60, 16.60),
                ]
            )
        ),
    }
    payload.update(changes)
    return payload


def test_observed_water_extent_requires_polygonal_geometry() -> None:
    with pytest.raises(ValidationError, match="Polygon or MultiPolygon"):
        ObservedWaterExtentCreate.model_validate(
            valid_payload(geometry={"type": "Point", "coordinates": [95.6, 16.6]})
        )


def test_observed_water_extent_requires_https_provenance() -> None:
    with pytest.raises(ValidationError):
        ObservedWaterExtentCreate.model_validate(
            valid_payload(source_url="http://example.test")
        )


def test_observed_water_extent_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValidationError):
        ObservedWaterExtentCreate.model_validate(valid_payload(confidence_score=1.5))


def test_observed_water_extent_accepts_null_confidence() -> None:
    model = ObservedWaterExtentCreate.model_validate(
        valid_payload(confidence_score=None)
    )
    assert model.confidence_score is None


def test_openapi_lists_observed_water_extent_endpoints(client) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/observed-water-extents" in paths
    assert "/api/v1/observed-water-extents/{extent_id}" in paths
