from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.data_layer import DataLayerCreate, DataLayerUpdate


def valid_layer_payload() -> dict:
    return {
        "layer_key": "test:dem:v1",
        "name": "Test elevation",
        "category": "elevation",
        "data_kind": "raster",
        "provider": "Test provider",
        "source_url": "https://example.com/source",
        "license_name": "Test licence",
        "license_url": "https://example.com/license",
        "attribution": "Test attribution",
        "spatial_resolution_m": 30,
        "quality_status": "verified",
        "quality_notes": "Source metadata reviewed for this test.",
        "coverage": {
            "type": "Polygon",
            "coordinates": [
                [
                    [95.4, 16.5],
                    [95.8, 16.5],
                    [95.8, 16.9],
                    [95.4, 16.9],
                    [95.4, 16.5],
                ]
            ],
        },
    }


def test_data_layer_accepts_auditable_metadata_and_coverage() -> None:
    layer = DataLayerCreate.model_validate(valid_layer_payload())

    assert layer.layer_key == "test:dem:v1"
    assert layer.spatial_resolution_m == 30
    assert layer.coverage is not None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("layer_key", "Invalid Key"),
        ("source_url", "http://insecure.example.com"),
        ("spatial_resolution_m", 0),
        ("quality_status", "good"),
        ("data_kind", "spreadsheet"),
    ],
)
def test_data_layer_rejects_invalid_catalog_fields(
    field: str,
    value: object,
) -> None:
    payload = valid_layer_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        DataLayerCreate.model_validate(payload)


def test_data_layer_rejects_reversed_temporal_coverage() -> None:
    payload = valid_layer_payload()
    now = datetime.now(UTC)
    payload["temporal_coverage_start"] = now
    payload["temporal_coverage_end"] = now - timedelta(days=1)

    with pytest.raises(ValidationError):
        DataLayerCreate.model_validate(payload)


def test_data_layer_update_requires_a_change() -> None:
    with pytest.raises(ValidationError):
        DataLayerUpdate()


def test_openapi_lists_data_layer_catalog(client) -> None:
    openapi = client.get("/openapi.json").json()

    assert "/api/v1/data-layers" in openapi["paths"]
    assert "/api/v1/data-layers/{layer_id}" in openapi["paths"]
