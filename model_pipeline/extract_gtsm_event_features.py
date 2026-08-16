"""Extract GTSM daily-maximum coastal proxies for Maubin GFD event windows.

The selected grid point is the nearest valid GTSM coastal node to Maubin. It is
not a local gauge, so output metadata retains its offset and labels all values
as coastal forcing proxies. Each feature stops at the calendar day before the
event starts.
"""

from __future__ import annotations

import json
import zipfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from netCDF4 import Dataset, num2date


MAUBIN_LAT = 16.73
MAUBIN_LON = 95.65
ARCHIVES = Path("/home/ubuntu/deltawatch-tide/event_data")
EXTRACTED = Path("/home/ubuntu/deltawatch-tide/extracted")
STATIC = Path("/home/ubuntu/webdev-static-assets")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs")


def extract_archives() -> list[Path]:
    EXTRACTED.mkdir(parents=True, exist_ok=True)
    for archive in sorted(ARCHIVES.glob("gtsm_event_months_*.zip")):
        with zipfile.ZipFile(archive) as source:
            source.extractall(EXTRACTED)
    return sorted(EXTRACTED.glob("*.nc"))


def nearest_node(dataset: Dataset) -> tuple[int, float, float, float]:
    latitudes = np.asarray(dataset.variables["station_y_coordinate"][:], dtype=float)
    longitudes = np.asarray(dataset.variables["station_x_coordinate"][:], dtype=float)
    distance_squared = (latitudes - MAUBIN_LAT) ** 2 + (longitudes - MAUBIN_LON) ** 2
    index = int(np.nanargmin(distance_squared))
    return index, float(latitudes[index]), float(longitudes[index]), float(np.sqrt(distance_squared[index]))


def read_series(path: Path) -> tuple[str, dict[str, float], dict[str, float]]:
    with Dataset(path) as dataset:
        value_name = "surge" if "surge" in dataset.variables else "waterlevel"
        node_index, latitude, longitude, distance = nearest_node(dataset)
        time = dataset.variables["time"]
        timestamps = num2date(time[:], units=time.units, calendar=getattr(time, "calendar", "standard"))
        values = np.asarray(dataset.variables[value_name][:, node_index], dtype=float)
        series = {
            f"{stamp.year:04d}-{stamp.month:02d}-{stamp.day:02d}": round(float(value), 5)
            for stamp, value in zip(timestamps, values)
            if np.isfinite(value)
        }
        node = {
            "index": node_index,
            "latitude": round(latitude, 5),
            "longitude": round(longitude, 5),
            "distance_degrees": round(distance, 5),
        }
    return value_name, series, node


def pre_event(series: dict[str, float], event_start: date, days: int) -> tuple[float | None, float | None]:
    values = [series.get((event_start - timedelta(days=offset)).isoformat()) for offset in range(1, days + 1)]
    present = [value for value in values if value is not None]
    if len(present) != days:
        return None, None
    return round(present[-1], 5), round(max(present), 5)


def main() -> None:
    files = extract_archives()
    waterlevel: dict[str, float] = {}
    surge: dict[str, float] = {}
    node_metadata: dict[str, float] | None = None
    for path in files:
        value_name, series, node = read_series(path)
        node_metadata = node
        if value_name == "surge":
            surge.update(series)
        else:
            waterlevel.update(series)

    hindcast = json.loads((STATIC / "maubin_hindcast_seed.json").read_text(encoding="utf-8"))
    rows = []
    for event in sorted(hindcast["events"], key=lambda item: item["start_date"]):
        event_start = date.fromisoformat(event["start_date"])
        total_1d, total_3d_max = pre_event(waterlevel, event_start, 3)
        surge_1d, surge_3d_max = pre_event(surge, event_start, 3)
        rows.append({
            "event_id": str(event["id"]),
            "event_start": event["start_date"],
            "coastal_total_water_lag_1d_m": total_1d,
            "coastal_total_water_lag_3d_max_m": total_3d_max,
            "coastal_surge_lag_1d_m": surge_1d,
            "coastal_surge_lag_3d_max_m": surge_3d_max,
        })

    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = {
        "source": "CDS GTSM-ERA5-E v3 reanalysis daily maximum",
        "node_type": "nearest valid coastal model node, not a Maubin local gauge",
        "nearest_node": node_metadata,
        "feature_definition": "values use only the one-to-three calendar days preceding each event start",
        "tide_feature_status": "not included separately because the retrieved daily-maximum files provide total water level and surge residual, not an independently interpretable daily tide maximum",
        "events": rows,
        "complete_event_rows": sum(1 for row in rows if all(value is not None for key, value in row.items() if key not in {"event_id", "event_start"})),
    }
    target = OUTPUT / "gtsm_event_window_features.json"
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"target": str(target), "complete_event_rows": report["complete_event_rows"], "nearest_node": node_metadata}, indent=2))


if __name__ == "__main__":
    main()
