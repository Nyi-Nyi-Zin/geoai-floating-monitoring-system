"""Aggregate static ESA WorldCover 2021 v200 context by Myanmar Admin 1 polygons.

The process uses categorical mode-resampled COG overviews of only WorldCover tiles
intersecting Myanmar. It does not fit a model or create any flood-risk output.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from shapely.geometry import Point, shape
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely.strtree import STRtree


ADMIN1 = Path("/home/ubuntu/nationwide-data/mmr_admin_boundaries/mmr_admin1.geojson")
GRID = Path("/home/ubuntu/nationwide-data/worldcover/esa_worldcover_2020_grid.geojson")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_admin1_worldcover_static.json")
COG_BASE = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map"
OVERVIEW_SIDE = 120
LAND_COVER_CLASSES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}


def tile_url(tile: str) -> str:
    return f"{COG_BASE}/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"


def main() -> None:
    source = json.loads(ADMIN1.read_text(encoding="utf-8"))
    regions = [{
        "admin1_pcode": feature["properties"]["adm1_pcode"],
        "admin1_name": feature["properties"]["adm1_name"],
        "geometry": shape(feature["geometry"]),
    } for feature in source["features"]]
    if len(regions) != 18:
        raise RuntimeError(f"Expected 18 Admin 1 polygons, received {len(regions)}")
    country = unary_union([region["geometry"] for region in regions])
    grid = json.loads(GRID.read_text(encoding="utf-8"))
    tiles = [feature["properties"]["ll_tile"] for feature in grid["features"] if shape(feature["geometry"]).intersects(country)]
    if not tiles:
        raise RuntimeError("No official WorldCover grid tiles intersect Myanmar")

    geometries = [region["geometry"] for region in regions]
    tree = STRtree(geometries)
    prepared = [prep(geometry) for geometry in geometries]
    counts_by_region: dict[int, Counter[int]] = {index: Counter() for index in range(len(regions))}
    attempted_tiles: list[str] = []
    succeeded_tiles: list[str] = []
    unavailable_tiles: list[dict[str, str]] = []

    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
        for tile in tiles:
            url = tile_url(tile)
            attempted_tiles.append(url)
            try:
                with rasterio.open(url) as dataset:
                    band = dataset.read(
                        1,
                        out_shape=(1, OVERVIEW_SIDE, OVERVIEW_SIDE),
                        masked=True,
                        resampling=Resampling.mode,
                    )
                    succeeded_tiles.append(url)
                    transform = dataset.transform * dataset.transform.scale(
                        dataset.width / OVERVIEW_SIDE, dataset.height / OVERVIEW_SIDE
                    )
                    valid_mask = ~np.ma.getmaskarray(band)
                    for row, column in zip(*np.where(valid_mask)):
                        code = int(band[row, column])
                        if code not in LAND_COVER_CLASSES:
                            continue
                        longitude, latitude = rasterio.transform.xy(transform, int(row), int(column), offset="center")
                        point = Point(longitude, latitude)
                        for index in tree.query(point):
                            region_index = int(index)
                            if prepared[region_index].contains(point):
                                counts_by_region[region_index][code] += 1
            except Exception as error:  # record unavailable public assets rather than silently substituting data
                unavailable_tiles.append({"url": url, "error": type(error).__name__})

    output_regions = []
    for index, region in enumerate(regions):
        counts = counts_by_region[index]
        sample_count = sum(counts.values())
        if not sample_count:
            raise RuntimeError(f"No valid WorldCover overview samples for {region['admin1_pcode']}")
        dominant_code, dominant_count = counts.most_common(1)[0]
        output_regions.append({
            "admin1_pcode": region["admin1_pcode"],
            "admin1_name": region["admin1_name"],
            "overview_sample_count": sample_count,
            "dominant_land_cover_code": dominant_code,
            "dominant_land_cover": LAND_COVER_CLASSES[dominant_code],
            "dominant_land_cover_share": round(dominant_count / sample_count, 6),
            "class_sample_counts": {str(code): counts.get(code, 0) for code in LAND_COVER_CLASSES},
            "class_sample_shares": {str(code): round(counts.get(code, 0) / sample_count, 6) for code in LAND_COVER_CLASSES},
        })
    payload = {
        "schema": "deltawatch-myanmar-admin1-worldcover-static-v1",
        "source": {
            "provider": "ESA WorldCover",
            "dataset": "WorldCover 2021 v200 Map",
            "dataset_doi": "https://doi.org/10.5281/zenodo.7254221",
            "public_bucket": "s3://esa-worldcover/v200/2021/map",
            "tile_grid_source": "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v100/2020/esa_worldcover_2020_grid.geojson",
            "license": "CC BY 4.0",
            "native_resolution_m": 10,
            "crs": "WGS84",
        },
        "method": {
            "admin_geometry": "OCHA/HDX MIMU source Admin 1 polygons",
            "tile_selection": "Official WorldCover grid tiles whose true geometry intersects the Admin 1 union; raster COG assets are not persisted in the web project.",
            "sampling": f"Per-tile {OVERVIEW_SIDE}x{OVERVIEW_SIDE} categorical mode-resampled overview values assigned by point-in-polygon at sample-cell centers.",
            "statistics": "Per-class overview sample counts and shares; dominant class is the largest static overview share.",
        },
        "tile_audit": {
            "attempted_tile_count": len(attempted_tiles),
            "succeeded_tile_count": len(succeeded_tiles),
            "unavailable_tile_count": len(unavailable_tiles),
            "unavailable_tiles": unavailable_tiles,
        },
        "class_legend": {str(code): label for code, label in LAND_COVER_CLASSES.items()},
        "region_count": len(output_regions),
        "regions": output_regions,
        "limits": [
            "This is a coarse static overview aggregation; it is not a parcel-scale land-cover assessment or operational land-use update feed.",
            "WorldCover 2021 v200 provides land cover, not rain, river stage, current flood extent, flood probability, forecast, risk score, or alert.",
            "No model is fitted and no predictive or life-safety output is created by this script.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT),
        "regions": len(output_regions),
        "attempted_tiles": len(attempted_tiles),
        "succeeded_tiles": len(succeeded_tiles),
        "unavailable_tiles": len(unavailable_tiles),
    }, indent=2))


if __name__ == "__main__":
    main()
