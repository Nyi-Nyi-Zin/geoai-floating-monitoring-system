"""Build static Admin 1 terrain summaries from Copernicus DEM GLO-30 remote COGs.

This script streams a 100 by 100 overview for only the one-degree tiles that
intersect the Myanmar Admin 1 envelope. Source rasters are not stored in the web
project. The result is static geographic context only and must not be used to
create a flood-risk output until separate validation and promotion gates are met.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from shapely.geometry import Point, box, shape
from shapely.prepared import prep
from shapely.strtree import STRtree


ADMIN1 = Path("/home/ubuntu/nationwide-data/mmr_admin_boundaries/mmr_admin1.geojson")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_admin1_copernicus_dem_static.json")
COG_BASE = "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com"
OVERVIEW_SIDE = 100


def tile_asset_url(latitude: int, longitude: int) -> str:
    lat_direction, lat_value = ("N", latitude) if latitude >= 0 else ("S", abs(latitude))
    lon_direction, lon_value = ("E", longitude) if longitude >= 0 else ("W", abs(longitude))
    identifier = f"Copernicus_DSM_COG_10_{lat_direction}{lat_value:02d}_00_{lon_direction}{lon_value:03d}_00"
    return f"{COG_BASE}/{identifier}_DEM/{identifier}_DEM.tif"


def finite_values(values: list[float]) -> list[float]:
    return [value for value in values if math.isfinite(value)]


def main() -> None:
    source = json.loads(ADMIN1.read_text(encoding="utf-8"))
    regions = [{
        "admin1_pcode": feature["properties"]["adm1_pcode"],
        "admin1_name": feature["properties"]["adm1_name"],
        "geometry": shape(feature["geometry"]),
    } for feature in source["features"]]
    if len(regions) != 18:
        raise RuntimeError(f"Expected 18 Admin 1 polygons, received {len(regions)}")
    geometries = [region["geometry"] for region in regions]
    tree = STRtree(geometries)
    prepared = [prep(geometry) for geometry in geometries]
    values_by_region: dict[int, list[float]] = {index: [] for index in range(len(regions))}
    bounds = [geometry.bounds for geometry in geometries]
    west, south = math.floor(min(item[0] for item in bounds)), math.floor(min(item[1] for item in bounds))
    east, north = math.ceil(max(item[2] for item in bounds)), math.ceil(max(item[3] for item in bounds))
    attempted_tiles: list[str] = []
    succeeded_tiles: list[str] = []
    unavailable_tiles: list[dict[str, str]] = []

    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
        for latitude in range(south, north):
            for longitude in range(west, east):
                if not len(tree.query(box(longitude, latitude, longitude + 1, latitude + 1))):
                    continue
                url = tile_asset_url(latitude, longitude)
                attempted_tiles.append(url)
                try:
                    with rasterio.open(url) as dataset:
                        band = dataset.read(
                            1,
                            out_shape=(1, OVERVIEW_SIDE, OVERVIEW_SIDE),
                            masked=True,
                            resampling=Resampling.average,
                        )
                        succeeded_tiles.append(url)
                        transform = dataset.transform * dataset.transform.scale(
                            dataset.width / OVERVIEW_SIDE, dataset.height / OVERVIEW_SIDE
                        )
                        valid_mask = ~np.ma.getmaskarray(band)
                        for row, column in zip(*np.where(valid_mask)):
                            longitude_center, latitude_center = rasterio.transform.xy(transform, int(row), int(column), offset="center")
                            point = Point(longitude_center, latitude_center)
                            for index in tree.query(point):
                                region_index = int(index)
                                if prepared[region_index].contains(point):
                                    values_by_region[region_index].append(float(band[row, column]))
                except Exception as error:  # public GLO-30 coverage can omit released tiles
                    unavailable_tiles.append({"url": url, "error": type(error).__name__})

    result_regions = []
    for index, region in enumerate(regions):
        samples = finite_values(values_by_region[index])
        if not samples:
            raise RuntimeError(f"No valid DEM overview samples for {region['admin1_pcode']}")
        elevations = np.asarray(samples, dtype=float)
        p10, p50, p90 = np.percentile(elevations, [10, 50, 90])
        result_regions.append({
            "admin1_pcode": region["admin1_pcode"],
            "admin1_name": region["admin1_name"],
            "overview_sample_count": int(elevations.size),
            "mean_elevation_m": round(float(elevations.mean()), 3),
            "median_elevation_m": round(float(p50), 3),
            "p10_elevation_m": round(float(p10), 3),
            "p90_elevation_m": round(float(p90), 3),
            "regional_relief_p90_p10_m": round(float(p90 - p10), 3),
            "minimum_overview_elevation_m": round(float(elevations.min()), 3),
            "maximum_overview_elevation_m": round(float(elevations.max()), 3),
        })
    payload = {
        "schema": "deltawatch-myanmar-admin1-copernicus-dem-static-v1",
        "source": {
            "provider": "Copernicus DEM",
            "dataset": "GLO-30 Public, 2021 release",
            "catalog": "https://copernicus-dem-30m-stac.s3.eu-central-1.amazonaws.com/",
            "asset_base": COG_BASE,
            "crs": "EPSG:4326",
            "native_tile_size_degrees": 1,
            "native_resolution_m": 30,
            "elevation_description": "Orthometric heights in meters; source is a digital surface model that can include buildings, infrastructure, and vegetation.",
        },
        "method": {
            "admin_geometry": "OCHA/HDX MIMU source Admin 1 polygons",
            "tile_selection": "All one-degree GLO-30 public COG tiles in the Admin 1 envelope; no raster assets persisted in the web project.",
            "sampling": f"Per-tile {OVERVIEW_SIDE}x{OVERVIEW_SIDE} average-resampled overview values assigned by point-in-polygon at sample-cell centers.",
            "statistics": "Mean, median, 10th and 90th percentile elevations; regional relief equals P90 minus P10 over the sampled region.",
        },
        "tile_audit": {
            "attempted_tile_count": len(attempted_tiles),
            "succeeded_tile_count": len(succeeded_tiles),
            "unavailable_tile_count": len(unavailable_tiles),
            "unavailable_tiles": unavailable_tiles,
        },
        "region_count": len(result_regions),
        "regions": result_regions,
        "limits": [
            "This is a coarse static overview aggregation, not a full-resolution terrain analysis or local drainage survey.",
            "Copernicus GLO-30 is a digital surface model, not a bare-earth terrain model.",
            "The source does not provide rainfall, river stage, current flood extent, flood probability, forecast, risk score, or alert.",
            "No model is fitted and no predictive or life-safety output is created by this script.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT),
        "regions": len(result_regions),
        "attempted_tiles": len(attempted_tiles),
        "succeeded_tiles": len(succeeded_tiles),
        "unavailable_tiles": len(unavailable_tiles),
    }, indent=2))


if __name__ == "__main__":
    main()
