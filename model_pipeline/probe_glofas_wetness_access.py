"""Submit a minimal authorized GloFAS soil-wetness retrieval probe.

The probe requests only July 2018 over a small Maubin bounding box.  It is used
to validate CEMS/EWDS licence access and file structure before any 2002–2018
acquisition.  No values are added to the model in this script.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests


PROCESS_URL = "https://ewds.climate.copernicus.eu/api/retrieve/v1/processes/cems-glofas-historical/execution"
OUTPUT = Path("/home/ubuntu/deltawatch-wetness/probe")


def headers() -> dict[str, str]:
    token = os.environ.get("CDS_API_KEY")
    if not token:
        raise RuntimeError("CDS_API_KEY is not configured")
    return {"PRIVATE-TOKEN": token, "Content-Type": "application/json"}


def main() -> None:
    request = {
        "system_version": ["version_5_0"],
        "hydrological_model": ["lisflood"],
        "product_type": ["consolidated"],
        "timespan": ["time_mean"],
        "variable": ["soil_wetness_index"],
        "year": ["2018"],
        "month": ["07"],
        "day": [f"{day:02d}" for day in range(1, 32)],
        "area": [16.95, 95.45, 16.45, 95.95],
        "data_format": "netcdf",
        "download_format": "unarchived",
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "glofas_wetness_probe_request.json").write_text(json.dumps(request, indent=2), encoding="utf-8")

    with requests.Session() as session:
        response = session.post(PROCESS_URL, headers=headers(), json=request, timeout=120)
        response.raise_for_status()
        job = response.json()
        job_id = job["jobID"]
        job_url = f"https://ewds.climate.copernicus.eu/api/retrieve/v1/jobs/{job_id}"

        for _ in range(40):
            status_response = session.get(job_url, headers=headers(), timeout=90)
            status_response.raise_for_status()
            status = status_response.json()
            if status.get("status") == "successful":
                result = session.get(f"{job_url}/results", headers=headers(), timeout=90)
                result.raise_for_status()
                asset_url = result.json()["asset"]["value"]["href"]
                downloaded = session.get(asset_url, timeout=300)
                downloaded.raise_for_status()
                target = OUTPUT / "glofas_wetness_probe_2018_07.nc"
                target.write_bytes(downloaded.content)
                print(json.dumps({"status": "successful", "job_id": job_id, "target": str(target), "bytes": target.stat().st_size}, indent=2))
                return
            if status.get("status") in {"failed", "dismissed"}:
                raise RuntimeError(json.dumps(status, indent=2))
            time.sleep(15)

    raise TimeoutError("GloFAS wetness probe did not finish within the polling window")


if __name__ == "__main__":
    main()
