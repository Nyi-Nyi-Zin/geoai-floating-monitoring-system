"""Inspect an authorised GTSM-ERA5-E NetCDF sample without changing model data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset


MAUBIN_LAT = 16.73
MAUBIN_LON = 95.65


def coordinate_pair(dataset: Dataset) -> tuple[str, str] | None:
    names = list(dataset.variables)
    preferred = [
        ("station_y_coordinate", "station_x_coordinate"),
        ("latitude", "longitude"),
        ("lat", "lon"),
        ("y", "x"),
    ]
    for lat_name, lon_name in preferred:
        if lat_name in names and lon_name in names:
            return lat_name, lon_name
    return None


def main(path_value: str) -> None:
    path = Path(path_value)
    with Dataset(path) as dataset:
        variable_shapes = {
            name: list(variable.shape)
            for name, variable in dataset.variables.items()
        }
        report: dict[str, object] = {
            "file": path.name,
            "dimensions": {name: len(dimension) for name, dimension in dataset.dimensions.items()},
            "variables": variable_shapes,
        }
        pair = coordinate_pair(dataset)
        if pair:
            lat_name, lon_name = pair
            latitudes = np.asarray(dataset.variables[lat_name][:], dtype=float).reshape(-1)
            longitudes = np.asarray(dataset.variables[lon_name][:], dtype=float).reshape(-1)
            distance_squared = (latitudes - MAUBIN_LAT) ** 2 + (longitudes - MAUBIN_LON) ** 2
            index = int(np.nanargmin(distance_squared))
            report["nearest_maubin_node"] = {
                "index": index,
                "latitude": round(float(latitudes[index]), 5),
                "longitude": round(float(longitudes[index]), 5),
                "distance_degrees": round(float(np.sqrt(distance_squared[index])), 5),
            }
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
