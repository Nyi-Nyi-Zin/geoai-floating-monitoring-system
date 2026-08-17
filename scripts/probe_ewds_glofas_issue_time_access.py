"""Perform a smallest-bounded official EWDS GloFAS forecast access probe.

The probe requests one control-forecast lead time over a sub-degree area around a
documented Myanmar representative location. It writes an access/provenance audit
only. It never loads values into a model or creates predictions, probabilities,
scores, forecasts, alerts, or life-safety decisions.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import cdsapi


EWDS_ENDPOINT = "https://ewds.climate.copernicus.eu/api"
DATASET = "cems-glofas-forecast"
OUTPUT_DIR = Path("/home/ubuntu/deltawatch-model-outputs")
MANIFEST = OUTPUT_DIR / "myanmar_ewds_glofas_issue_time_probe.json"
# A small envelope around the MMR017 representative location. EWDS area order is north, west, south, east.
AREA = [16.8, 95.5, 16.7, 95.6]


def classify_error(error: Exception) -> str:
    message = str(error).lower()
    if "terms" in message or "licence" in message or "license" in message:
        return "dataset_terms_not_accepted"
    if "401" in message or "403" in message or "unauthor" in message or "forbidden" in message:
        return "credential_or_endpoint_access_rejected"
    if "not found" in message or "no data" in message or "invalid" in message:
        return "request_contract_or_data_availability_rejected"
    return "retrieval_unavailable_or_unclassified"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("CDS_API_KEY")
    requested_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    issue_date = date.today() - timedelta(days=3)
    request = {
        "system_version": ["operational"],
        "hydrological_model": ["lisflood"],
        "product_type": ["control_forecast"],
        "variable": "river_discharge_in_the_last_24_hours",
        "year": [issue_date.strftime("%Y")],
        "month": [issue_date.strftime("%m")],
        "day": [issue_date.strftime("%d")],
        "leadtime_hour": ["24"],
        "data_format": "grib2",
        "download_format": "zip",
        "area": AREA,
    }
    manifest = {
        "schema": "deltawatch-ewds-glofas-issue-time-access-probe-v1",
        "source": {"dataset": DATASET, "endpoint": EWDS_ENDPOINT, "documentation": "https://ewds.climate.copernicus.eu/datasets/cems-glofas-forecast"},
        "requested_at_utc": requested_at,
        "issue_date_utc": issue_date.isoformat(),
        "request": request,
        "location_context": {"admin1_pcode": "MMR017", "request_area_north_west_south_east": AREA},
        "safety": "Monitoring only: this probe contains no model fitting, score, probability, prediction, forecast, predicted label, alert, or life-safety decision.",
        "access_status": "not_attempted",
        "issue_time_feature_authorized": False,
    }
    if not token:
        manifest.update({"access_status": "access_blocked", "blocker": "credential_not_available"})
        MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2))
        return
    target = OUTPUT_DIR / f"ewds_glofas_issue_time_probe_{issue_date.isoformat()}.zip"
    try:
        client = cdsapi.Client(url=EWDS_ENDPOINT, key=token, quiet=True, progress=False)
        client.retrieve(DATASET, request, str(target))
        manifest.update({
            "access_status": "retrieval_succeeded",
            "artifact_path": str(target),
            "artifact_bytes": target.stat().st_size if target.exists() else None,
            "issue_time_feature_authorized": False,
            "next_gate": "Inspect downloaded metadata and prove retained issue-date lineage before any feature authorization.",
        })
    except Exception as error:  # External authentication and dataset acceptance are expected decision gates.
        manifest.update({"access_status": "access_blocked", "blocker": classify_error(error)})
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
