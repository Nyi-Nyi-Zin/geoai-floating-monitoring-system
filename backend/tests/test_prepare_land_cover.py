from pathlib import Path

import pytest

from scripts.prepare_land_cover import (
    LAND_COVER_DATASET_ID,
    WORLD_COVER_CLASSES,
    read_boundary,
    validate_geotiff,
)


def test_worldcover_legend_contains_expected_flood_relevant_classes() -> None:
    assert WORLD_COVER_CLASSES[40]["name"] == "Cropland"
    assert WORLD_COVER_CLASSES[50]["name"] == "Built-up"
    assert WORLD_COVER_CLASSES[80]["name"] == "Permanent water bodies"
    assert WORLD_COVER_CLASSES[90]["name"] == "Herbaceous wetland"
    assert LAND_COVER_DATASET_ID.endswith("2021-v200")


def test_validate_geotiff_accepts_little_endian_tiff(tmp_path: Path) -> None:
    raster = tmp_path / "land-cover.tif"
    raster.write_bytes(b"II*\x00" + b"\x00" * 8)

    assert validate_geotiff(raster).startswith(b"II*\x00")


def test_validate_geotiff_rejects_non_tiff(tmp_path: Path) -> None:
    raster = tmp_path / "land-cover.tif"
    raster.write_bytes(b"not-a-tiff")

    with pytest.raises(ValueError, match="not a valid TIFF"):
        validate_geotiff(raster)


def test_read_boundary_accepts_single_feature_collection(
    tmp_path: Path,
) -> None:
    boundary = tmp_path / "boundary.geojson"
    boundary.write_text(
        """
        {
          "type": "FeatureCollection",
          "features": [{
            "type": "Feature",
            "properties": {},
            "geometry": {
              "type": "Polygon",
              "coordinates": [[[95.5, 16.5], [95.6, 16.5],
                [95.6, 16.6], [95.5, 16.6], [95.5, 16.5]]]
            }
          }]
        }
        """,
        encoding="utf-8",
    )

    geometry = read_boundary(boundary)

    assert geometry["type"] == "Polygon"
