import pytest
from pydantic import ValidationError

from app.schemas.geo_asset import GeoAssetCreate, GeoAssetImportRequest


def valid_asset(**overrides):
    payload = {
        "name": "Tower MM-001",
        "asset_type": "telecom_tower",
        "description": "Example infrastructure asset.",
        "geometry": {"type": "Point", "coordinates": [96.1951, 16.8661]},
        "properties": {"operator": "example"},
    }
    payload.update(overrides)
    return payload


def test_accepts_valid_wgs84_geojson():
    asset = GeoAssetCreate.model_validate(valid_asset())

    assert asset.geometry["type"] == "Point"
    assert tuple(asset.geometry["coordinates"]) == (96.1951, 16.8661)


@pytest.mark.parametrize(
    ("geometry", "message"),
    [
        ({"type": "Feature", "geometry": None}, "not a Feature"),
        ({"type": "Point", "coordinates": [181, 10]}, "WGS84"),
        (
            {
                "type": "Polygon",
                "coordinates": [
                    [[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]],
                ],
            },
            "Invalid geometry",
        ),
    ],
)
def test_rejects_invalid_geojson(geometry, message):
    with pytest.raises(ValidationError, match=message):
        GeoAssetCreate.model_validate(valid_asset(geometry=geometry))


def test_http_validation_error_is_structured(client):
    response = client.post(
        "/api/v1/geo-assets",
        json=valid_asset(
            geometry={"type": "Point", "coordinates": [200, 95]},
        ),
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["request_id"]


def test_valid_asset_without_database_reports_configuration(client):
    response = client.post("/api/v1/geo-assets", json=valid_asset())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_not_configured"


def test_accepts_prepared_feature_collection():
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[95.6, 16.7], [95.7, 16.8]],
                },
                "properties": {
                    "name": "OSM river way/1",
                    "asset_type": "river_segment",
                    "source_key": "osm:way/1:maubin:1:1:500",
                    "description": "Clipped to Maubin Township.",
                    "metadata": {
                        "source": "OpenStreetMap",
                        "osm_id": "way/1",
                    },
                },
            }
        ],
    }

    result = GeoAssetImportRequest.model_validate(payload)

    assert len(result.features) == 1
    assert result.features[0].properties.asset_type == "river_segment"


def test_bulk_import_rejects_invalid_geometry(client):
    response = client.post(
        "/api/v1/geo-assets/import",
        json={
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [195, 16.7],
                    },
                    "properties": {
                        "name": "Invalid",
                        "asset_type": "river_segment",
                        "source_key": "osm:invalid:1",
                    },
                }
            ],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
