from datetime import date

import pytest
from pydantic import ValidationError
from shapely.geometry import Polygon, mapping

from app.schemas.flood_extent import FloodExtentCreate
from app.services.flood_extent import geodesic_area_km2, polygon_to_multipolygon
from scripts.import_flood_extents import (
    group_feature_collection,
    prepare_extent_geometry,
)
from scripts.import_flood_events import consistent_event_properties, parse_iso_date


def valid_payload(**changes):
    payload = {
        "source_key": "maubin:gfd:event-1:flood",
        "event_name": "Historical flood event 1",
        "observed_date": date(2015, 8, 9),
        "sensor": "MODIS",
        "classification": "flood",
        "confidence": "moderate",
        "field_validated": False,
        "source_name": "Global Flood Database v1",
        "source_url": "https://developers.google.com/earth-engine/datasets/catalog/GLOBAL_FLOOD_DB_MODIS_EVENTS_V1",
        "license_name": "CC BY-NC 4.0",
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


def test_flood_extent_requires_polygonal_wgs84_geometry() -> None:
    with pytest.raises(ValidationError, match="Polygon or MultiPolygon"):
        FloodExtentCreate.model_validate(
            valid_payload(geometry={"type": "Point", "coordinates": [95.6, 16.6]})
        )


def test_flood_extent_requires_https_provenance() -> None:
    with pytest.raises(ValidationError):
        FloodExtentCreate.model_validate(valid_payload(source_url="http://example.test"))


def test_flood_extent_rejects_reversed_event_dates() -> None:
    with pytest.raises(ValidationError, match="on or after"):
        FloodExtentCreate.model_validate(
            valid_payload(
                observed_start_date=date(2015, 8, 10),
                observed_end_date=date(2015, 8, 9),
            )
        )


def test_individual_event_metadata_is_consistent() -> None:
    collection = {
        "features": [
            {
                "properties": {
                    "event_start_date": "2015-08-09",
                    "event_end_date": "2015-08-14",
                    "dfo_main_cause": "Heavy rain",
                }
            },
            {
                "properties": {
                    "event_start_date": "2015-08-09",
                    "event_end_date": "2015-08-14",
                    "dfo_main_cause": "Heavy rain",
                }
            },
        ]
    }

    metadata = consistent_event_properties("1234", collection)

    assert metadata["event_id"] == "1234"
    assert parse_iso_date(metadata["event_start_date"], "start") == date(2015, 8, 9)


def test_individual_event_metadata_rejects_mixed_dates() -> None:
    with pytest.raises(ValueError, match="inconsistent"):
        consistent_event_properties(
            "1234",
            {
                "features": [
                    {
                        "properties": {
                            "event_start_date": "2015-08-09",
                            "event_end_date": "2015-08-14",
                        }
                    },
                    {
                        "properties": {
                            "event_start_date": "2015-08-10",
                            "event_end_date": "2015-08-14",
                        }
                    },
                ]
            },
        )


def test_polygon_normalization_and_area() -> None:
    polygon = Polygon(
        [(95.6, 16.6), (95.61, 16.6), (95.61, 16.61), (95.6, 16.61)]
    )
    multipolygon = polygon_to_multipolygon(polygon)

    assert multipolygon.geom_type == "MultiPolygon"
    assert geodesic_area_km2(multipolygon) > 1


def test_importer_dissolves_and_clips_features() -> None:
    first = Polygon(
        [(95.60, 16.60), (95.62, 16.60), (95.62, 16.62), (95.60, 16.62)]
    )
    second = Polygon(
        [(95.61, 16.61), (95.63, 16.61), (95.63, 16.63), (95.61, 16.63)]
    )
    clip = Polygon(
        [(95.60, 16.60), (95.625, 16.60), (95.625, 16.625), (95.60, 16.625)]
    )
    geometry, source_count = prepare_extent_geometry(
        {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {}, "geometry": mapping(first)},
                {"type": "Feature", "properties": {}, "geometry": mapping(second)},
            ],
        },
        clip,
    )

    assert source_count == 2
    assert geometry.geom_type == "MultiPolygon"
    assert geometry.within(clip)


def test_importer_groups_frequency_property_without_losing_features() -> None:
    payload = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"event_count": 1}},
            {"type": "Feature", "properties": {"event_count": 2}},
            {"type": "Feature", "properties": {"event_count": 1}},
        ],
    }

    groups = group_feature_collection(payload, "event_count")

    assert [value for value, _ in groups] == [1, 2]
    assert [len(group["features"]) for _, group in groups] == [2, 1]


def test_importer_rejects_missing_group_property() -> None:
    with pytest.raises(ValueError, match="missing group property"):
        group_feature_collection(
            {"type": "FeatureCollection", "features": [{"properties": {}}]},
            "event_count",
        )


def test_importer_rejects_empty_polygon_after_clip() -> None:
    polygon = Polygon(
        [(95.60, 16.60), (95.61, 16.60), (95.61, 16.61), (95.60, 16.61)]
    )
    distant_clip = Polygon(
        [(96.0, 17.0), (96.1, 17.0), (96.1, 17.1), (96.0, 17.1)]
    )

    with pytest.raises(ValueError, match="do not overlap"):
        prepare_extent_geometry(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": {}, "geometry": mapping(polygon)}
                ],
            },
            distant_clip,
        )


def test_openapi_lists_flood_extent_endpoints(client) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/flood-extents" in paths
    assert "/api/v1/flood-extents/{extent_id}" in paths
