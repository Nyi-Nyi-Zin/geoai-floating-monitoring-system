"""Build a non-predictive event-region rainfall preparation table for Myanmar.

Rainfall lags end one day before each GFD event begins. Observed flood coverage is a
historical source label for later validation work, not a forecast or model output.
"""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path


RAINFALL = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_admin1_era5_daily_2002_2018.json")
COVERAGE = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_gfd_admin1_historical_coverage.csv")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_admin1_event_rainfall_lags.csv")
MANIFEST = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_admin1_event_rainfall_lags_manifest.json")
LAG_WINDOWS = (1, 3, 7, 14, 30)


def rainfall_lag(series: dict[str, float], event_start: str, window: int) -> float:
    start = date.fromisoformat(event_start)
    values = [series[(start - timedelta(days=offset)).isoformat()] for offset in range(1, window + 1)]
    return round(sum(values), 4)


def main() -> None:
    rainfall = json.loads(RAINFALL.read_text(encoding="utf-8"))
    series_by_region = {
        record["admin1_pcode"]: {day: float(value) for day, value in zip(record["daily"]["time"], record["daily"]["precipitation_sum_mm"]) if value is not None}
        for record in rainfall["records"]
    }
    with COVERAGE.open("r", encoding="utf-8", newline="") as handle:
        coverage_rows = list(csv.DictReader(handle))
    fields = [
        "event_id", "event_start", "admin1_pcode", "admin1_name", "coverage_status", "observed_flood_presence", "flooded_fraction",
        *[f"rainfall_lag_{window}d_mm" for window in LAG_WINDOWS],
    ]
    rows: list[dict[str, object]] = []
    for coverage in coverage_rows:
        pcode = coverage["admin1_pcode"]
        series = series_by_region.get(pcode)
        if not series:
            raise RuntimeError(f"No rainfall series for {pcode}")
        row: dict[str, object] = {key: coverage[key] for key in fields if key in coverage}
        for window in LAG_WINDOWS:
            row[f"rainfall_lag_{window}d_mm"] = rainfall_lag(series, coverage["event_start"], window)
        rows.append(row)
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "schema": "deltawatch-myanmar-admin1-event-rainfall-lags-v1",
        "row_count": len(rows),
        "event_count": len({row["event_id"] for row in rows}),
        "region_count": len({row["admin1_pcode"] for row in rows}),
        "lag_windows_days": list(LAG_WINDOWS),
        "leakage_control": "Each rainfall window ends one calendar day before the GFD event start date.",
        "label_status": "Observed GFD Admin 1 coverage source label only; no score, probability, forecast, or alert is generated.",
        "limits": [
            "Centroid rainfall is a regional area proxy and must not be represented as gridded regional rainfall.",
            "Static terrain, land cover, river network, and flow features are not yet joined.",
            "This table is not a fitted model and cannot establish nationwide predictive accuracy.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **manifest}, indent=2))


if __name__ == "__main__":
    main()
