"""Create authorised GTSM request files for event months plus their antecedent month.

The planner does not download data. It preserves leakage control by retaining the
preceding calendar month needed to calculate pre-event water-level summaries.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


STATIC = Path("/home/ubuntu/webdev-static-assets")
OUTPUT = Path("/home/ubuntu/deltawatch-tide/requests")


def main() -> None:
    payload = json.loads((STATIC / "maubin_hindcast_seed.json").read_text(encoding="utf-8"))
    months_by_year: dict[str, set[str]] = defaultdict(set)
    event_windows: list[dict[str, str]] = []

    for event in payload["events"]:
        event_start = date.fromisoformat(event["start_date"])
        for point in (event_start, *(event_start - timedelta(days=offset) for offset in range(1, 4))):
            months_by_year[str(point.year)].add(f"{point.month:02d}")
        event_windows.append({"event_id": str(event["id"]), "event_start": event["start_date"]})

    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifests = []
    for year, months in sorted(months_by_year.items()):
        request = {
            "inputs": {
                "variable": ["storm_surge_residual", "tidal_elevation", "total_water_level"],
                "experiment": "reanalysis",
                "temporal_aggregation": ["daily_maximum"],
                "year": [year],
                "month": sorted(months),
                "version": ["v3"],
            }
        }
        request_path = OUTPUT / f"gtsm_{year}.json"
        request_path.write_text(json.dumps(request, indent=2), encoding="utf-8")
        manifests.append({"year": year, "months": sorted(months), "request_file": str(request_path)})

    (OUTPUT / "event_request_manifest.json").write_text(
        json.dumps({"events": event_windows, "requests": manifests}, indent=2), encoding="utf-8"
    )
    print(json.dumps({"events": len(event_windows), "year_requests": manifests}, indent=2))


if __name__ == "__main__":
    main()
