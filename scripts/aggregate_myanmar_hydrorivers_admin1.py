"""Aggregate HydroRIVERS Asia descriptors by true Myanmar Admin 1 polygons.

The result is a static river-network source summary. It does not build features for a
fitted model, create a flood forecast, calculate probability, or issue an alert.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import shapefile
from pyproj import Geod
from shapely.geometry import shape
from shapely.prepared import prep
from shapely.strtree import STRtree


RIVERS = Path("/home/ubuntu/nationwide-data/hydrorivers/HydroRIVERS_v10_as_shp/HydroRIVERS_v10_as.shp")
ADMIN1 = Path("/home/ubuntu/nationwide-data/mmr_admin_boundaries/mmr_admin1.geojson")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_admin1_hydrorivers_static.json")
GEOD = Geod(ellps="WGS84")


def kilometers(geometry) -> float:
    return abs(GEOD.geometry_length(geometry)) / 1000.0 if not geometry.is_empty else 0.0


def main() -> None:
    admin = json.loads(ADMIN1.read_text(encoding="utf-8"))
    regions = [{
        "pcode": feature["properties"]["adm1_pcode"],
        "name": feature["properties"]["adm1_name"],
        "geometry": shape(feature["geometry"]),
    } for feature in admin["features"]]
    if len(regions) != 18:
        raise RuntimeError(f"Expected 18 Admin 1 regions; received {len(regions)}")
    geometries = [region["geometry"] for region in regions]
    tree = STRtree(geometries)
    prepared = [prep(geometry) for geometry in geometries]
    country_bounds = {
        "west": min(geometry.bounds[0] for geometry in geometries),
        "south": min(geometry.bounds[1] for geometry in geometries),
        "east": max(geometry.bounds[2] for geometry in geometries),
        "north": max(geometry.bounds[3] for geometry in geometries),
    }
    metrics: dict[str, dict[str, float | int]] = defaultdict(lambda: {
        "intersecting_reach_count": 0,
        "clipped_river_length_km": 0.0,
        "longest_clipped_reach_km": 0.0,
        "max_strahler_order": 0,
        "length_weighted_discharge_sum": 0.0,
        "length_weight": 0.0,
    })
    reader = shapefile.Reader(str(RIVERS))
    source_reach_count = 0
    for record in reader.iterShapeRecords(bbox=[country_bounds["west"], country_bounds["south"], country_bounds["east"], country_bounds["north"]]):
        line = shape(record.shape.__geo_interface__)
        candidate_indexes = tree.query(line)
        if not len(candidate_indexes):
            continue
        attributes = record.record.as_dict()
        for index in candidate_indexes:
            region_index = int(index)
            if not prepared[region_index].intersects(line):
                continue
            clipped = line.intersection(geometries[region_index])
            clipped_km = kilometers(clipped)
            if clipped_km <= 0:
                continue
            source_reach_count += 1
            data = metrics[regions[region_index]["pcode"]]
            data["intersecting_reach_count"] += 1
            data["clipped_river_length_km"] += clipped_km
            data["longest_clipped_reach_km"] = max(float(data["longest_clipped_reach_km"]), clipped_km)
            data["max_strahler_order"] = max(int(data["max_strahler_order"]), int(attributes.get("ORD_STRA") or 0))
            discharge = float(attributes.get("DIS_AV_CMS") or 0.0)
            data["length_weighted_discharge_sum"] += discharge * clipped_km
            data["length_weight"] += clipped_km
    output_regions = []
    for region in regions:
        data = metrics[region["pcode"]]
        length = float(data["clipped_river_length_km"])
        output_regions.append({
            "admin1_pcode": region["pcode"],
            "admin1_name": region["name"],
            "intersecting_reach_count": int(data["intersecting_reach_count"]),
            "clipped_river_length_km": round(length, 3),
            "longest_clipped_reach_km": round(float(data["longest_clipped_reach_km"]), 3),
            "max_strahler_order": int(data["max_strahler_order"]),
            "length_weighted_mean_discharge_m3s": round(float(data["length_weighted_discharge_sum"]) / length, 6) if length else None,
        })
    payload = {
        "schema": "deltawatch-myanmar-admin1-hydrorivers-static-v1",
        "source": {
            "provider": "HydroSHEDS",
            "dataset": "HydroRIVERS version 1, Asia shapefile",
            "source_url": "https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_as_shp.zip",
            "source_reach_criteria": "catchment area at least 10 km² or average river flow at least 0.1 m³/sec",
        },
        "method": "True Admin 1 polygon intersection; clipped WGS84 geodesic lengths; source reach attributes retained as static descriptors.",
        "region_count": len(output_regions),
        "regions": output_regions,
        "limits": [
            "HydroRIVERS is a static river-network source and does not provide observed current river stage or flood extent.",
            "The source threshold omits smaller drainage channels and does not replace local drainage/levee surveys.",
            "This aggregation does not create features for a fitted model, risk score, probability, forecast, or alert.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "region_count": len(output_regions), "total_clipped_river_km": round(sum(region["clipped_river_length_km"] for region in output_regions), 3), "intersections": source_reach_count}, indent=2))


if __name__ == "__main__":
    main()
