"""Acquire audited ERA5-based daily rainfall history for Myanmar Admin 1 centroids.

The result is a historical source record for future issue-time features. It does not
create model features, fit a model, produce risk scores, probabilities, or alerts.
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


PARTITIONS = Path("/home/ubuntu/webdev-static-assets/myanmar_admin1_partitions_v1.json")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_admin1_era5_daily_2002_2018.json")
START_DATE = "2002-07-01"
END_DATE = "2018-07-14"
ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"


def fetch_json(params: dict[str, object]) -> dict:
    url = f"{ENDPOINT}?{urlencode(params)}"
    error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(url, timeout=120) as response:
                return json.load(response)
        except Exception as exc:  # Network availability is an external dependency.
            error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Open-Meteo archive request failed after retries: {error}")


def main() -> None:
    partition_seed = json.loads(PARTITIONS.read_text(encoding="utf-8"))
    expected_days = (date.fromisoformat(END_DATE) - date.fromisoformat(START_DATE)).days + 1
    records = []
    for index, partition in enumerate(partition_seed["partitions"], start=1):
        center = partition["source_center"]
        payload = fetch_json({
            "latitude": center["latitude"],
            "longitude": center["longitude"],
            "start_date": START_DATE,
            "end_date": END_DATE,
            "daily": "precipitation_sum",
            "timezone": "UTC",
        })
        daily = payload.get("daily", {})
        dates = daily.get("time", [])
        rainfall = daily.get("precipitation_sum", [])
        if len(dates) != expected_days or len(rainfall) != expected_days:
            raise RuntimeError(f"Unexpected daily coverage for {partition['admin1_pcode']}: {len(dates)} / {expected_days}")
        missing_days = sum(value is None for value in rainfall)
        records.append({
            "admin1_pcode": partition["admin1_pcode"],
            "admin1_name": partition["admin1_name"],
            "requested_center": center,
            "source_gridpoint": {"latitude": payload.get("latitude"), "longitude": payload.get("longitude"), "elevation": payload.get("elevation")},
            "daily": {"time": dates, "precipitation_sum_mm": rainfall},
            "coverage_days": len(dates),
            "missing_days": missing_days,
        })
        print(f"{index}/{len(partition_seed['partitions'])} {partition['admin1_pcode']} {len(dates)} days; missing={missing_days}")
        time.sleep(0.2)
    result = {
        "schema": "deltawatch-myanmar-admin1-era5-daily-rainfall-v1",
        "source": "Open-Meteo archive API, ERA5-based daily precipitation_sum",
        "endpoint": ENDPOINT,
        "date_range": {"start": START_DATE, "end": END_DATE},
        "admin1_region_count": len(records),
        "records": records,
        "limits": [
            "Centroid rainfall is an area proxy, not a full regional gridded rainfall field.",
            "This acquisition is historical input preparation only and does not create features, forecasts, scores, probabilities, or alerts.",
            "Any future model must restrict lag windows to dates strictly before the flood event start date.",
        ],
    }
    OUTPUT.write_text(json.dumps(result), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "regions": len(records), "expected_days": expected_days, "missing_days": sum(record["missing_days"] for record in records)}, indent=2))


if __name__ == "__main__":
    main()
