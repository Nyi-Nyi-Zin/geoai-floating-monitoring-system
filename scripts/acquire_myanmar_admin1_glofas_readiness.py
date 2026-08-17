"""Acquire a bounded, non-predictive GloFAS-backed flow-readiness snapshot.

The Open-Meteo Flood API documents its river-discharge series as GloFAS v4
reanalysis and forecast data. This script records a short current request at the
18 existing Myanmar Admin 1 representative locations. It preserves the returned
grid coordinates and request timestamp, but does not claim an official GloFAS
forecast issue time; therefore it cannot authorize a model feature, score,
probability, prediction, forecast, or alert.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


PARTITIONS = Path("/home/ubuntu/webdev-static-assets/myanmar_admin1_partitions_v1.json")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_admin1_glofas_readiness_snapshot.json")
ENDPOINT = "https://flood-api.open-meteo.com/v1/flood"
DAILY_VARIABLES = ["river_discharge", "river_discharge_mean", "river_discharge_p75"]


def fetch_json(params: dict[str, object]) -> dict:
    query = urlencode(params)
    with urlopen(f"{ENDPOINT}?{query}", timeout=120) as response:
        return json.load(response)


def main() -> None:
    partitions = json.loads(PARTITIONS.read_text(encoding="utf-8"))["partitions"]
    requested_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    records: list[dict] = []
    for index, partition in enumerate(partitions, start=1):
        center = partition["source_center"]
        payload = fetch_json(
            {
                "latitude": center["latitude"],
                "longitude": center["longitude"],
                "daily": ",".join(DAILY_VARIABLES),
                "past_days": 1,
                "forecast_days": 7,
                "timezone": "GMT",
                "cell_selection": "nearest",
            }
        )
        if payload.get("error"):
            raise RuntimeError(f"Flood API error for {partition['admin1_pcode']}: {payload.get('reason')}")
        daily = payload.get("daily", {})
        dates = daily.get("time", [])
        if len(dates) != 8:
            raise RuntimeError(f"Expected 1 past + 7 forecast days for {partition['admin1_pcode']}, received {len(dates)}")
        if not all(len(daily.get(variable, [])) == len(dates) for variable in DAILY_VARIABLES):
            raise RuntimeError(f"Incomplete discharge variables for {partition['admin1_pcode']}")
        record = {
            "admin1_pcode": partition["admin1_pcode"],
            "admin1_name": partition["admin1_name"],
            "requested_center": center,
            "returned_source_gridpoint": {"latitude": payload.get("latitude"), "longitude": payload.get("longitude")},
            "generation_time_ms": payload.get("generationtime_ms"),
            "daily_units": payload.get("daily_units", {}),
            "daily": {"time": dates, **{variable: daily.get(variable, []) for variable in DAILY_VARIABLES}},
        }
        records.append(record)
        print(f"{index}/{len(partitions)} {partition['admin1_pcode']} source={record['returned_source_gridpoint']} days={len(dates)}")
    result = {
        "schema": "deltawatch-myanmar-admin1-glofas-readiness-snapshot-v1",
        "source": {
            "provider": "Open-Meteo Flood API",
            "upstream_dataset": "GloFAS v4 as documented by Open-Meteo",
            "endpoint": ENDPOINT,
            "documentation": "https://open-meteo.com/en/docs/flood-api",
            "request_time_utc": requested_at,
            "cell_selection": "nearest",
        },
        "request": {"past_days": 1, "forecast_days": 7, "daily_variables": DAILY_VARIABLES, "region_count": len(records)},
        "records": records,
        "issue_time_readiness": {
            "official_issue_timestamp_present": False,
            "usable_as_issue_time_model_feature": False,
            "reason": "The proxy response does not expose an official GloFAS model issue timestamp or retained forecast-run identifier. It is a source-availability readiness snapshot only.",
        },
        "safety": "Monitoring only: this acquisition does not fit a model or create a score, probability, forecast, predicted label, alert, or life-safety decision.",
        "limits": [
            "The API may select the largest or nearest represented river grid cell near the representative point; it is not a local river gauge.",
            "The GloFAS-backed proxy is river-flow context only and does not represent flash flooding, coastal flooding, tide, drainage, levees, or inundation extent.",
            "A future national model still requires archived official issue-time lineage and prospective inputs matched to verified outcomes.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "regions": len(records), "issue_time_feature_authorized": False}, indent=2))


if __name__ == "__main__":
    main()
