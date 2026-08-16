"""Download authorised GTSM-ERA5-E data for planned Maubin flood-event windows.

Reads JSON request files made by plan_gtsm_event_requests.py, uses the secured
CDS_API_KEY environment variable, and stores only source archives outside the
deployable project tree.
"""

from __future__ import annotations

import json
import os
import time
import zipfile
from pathlib import Path

import requests


REQUESTS_DIR = Path("/home/ubuntu/deltawatch-tide/requests")
DOWNLOAD_DIR = Path("/home/ubuntu/deltawatch-tide/event_data")
PROCESS_URL = (
    "https://cds.climate.copernicus.eu/api/retrieve/v1/processes/"
    "sis-water-level-change-timeseries-cmip6/execution"
)


def auth_headers() -> dict[str, str]:
    token = os.environ.get("CDS_API_KEY")
    if not token:
        raise RuntimeError("CDS_API_KEY is not configured")
    return {"PRIVATE-TOKEN": token, "Content-Type": "application/json"}


def request_result_url(session: requests.Session, request: dict) -> str:
    last_error: requests.RequestException | None = None
    response: requests.Response | None = None
    for attempt in range(1, 4):
        try:
            response = session.post(PROCESS_URL, headers=auth_headers(), json=request, timeout=300)
            response.raise_for_status()
            break
        except requests.RequestException as error:
            last_error = error
            if attempt == 3:
                raise
            time.sleep(30 * attempt)
    if response is None:
        raise RuntimeError(f"CDS request could not be submitted: {last_error}")
    job = response.json()
    job_id = job["jobID"]
    monitor_url = f"https://cds.climate.copernicus.eu/api/retrieve/v1/jobs/{job_id}"
    for _ in range(80):
        status_response = session.get(monitor_url, headers=auth_headers(), timeout=90)
        status_response.raise_for_status()
        status = status_response.json()
        state = status.get("status")
        if state == "successful":
            return f"{monitor_url}/results"
        if state in {"failed", "dismissed"}:
            raise RuntimeError(f"CDS job {job_id} finished with status {state}")
        time.sleep(15)
    raise TimeoutError(f"CDS job {job_id} did not complete within the polling limit")


def download_year(session: requests.Session, request_path: Path) -> dict[str, object]:
    year = request_path.stem.removeprefix("gtsm_")
    target = DOWNLOAD_DIR / f"gtsm_event_months_{year}.zip"
    if target.exists() and zipfile.is_zipfile(target):
        return {"year": year, "status": "existing", "archive": str(target)}

    request = json.loads(request_path.read_text(encoding="utf-8"))
    results_url = request_result_url(session, request)
    results_response = session.get(results_url, headers=auth_headers(), timeout=90)
    results_response.raise_for_status()
    asset_url = results_response.json()["asset"]["value"]["href"]
    with session.get(asset_url, stream=True, timeout=300) as asset_response:
        asset_response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in asset_response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    if not zipfile.is_zipfile(target):
        target.unlink(missing_ok=True)
        raise RuntimeError(f"CDS downloaded an invalid archive for {year}")
    return {"year": year, "status": "downloaded", "archive": str(target)}


def main() -> None:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    request_paths = sorted(REQUESTS_DIR.glob("gtsm_20*.json"))
    if not request_paths:
        raise FileNotFoundError("No planned GTSM request files found")

    with requests.Session() as session:
        outcomes = [download_year(session, request_path) for request_path in request_paths]
    manifest = {"source": "CDS GTSM-ERA5-E v3 daily maximum", "outcomes": outcomes}
    (DOWNLOAD_DIR / "download_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
