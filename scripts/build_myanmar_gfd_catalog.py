"""Build a transparent Myanmar historical-event catalog from public GFD QC metadata.

The result lists eligible historical event metadata only. It does not download rasters,
derive cell labels, train a model, or issue any prediction.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path


SOURCE = Path("/home/ubuntu/nationwide-data/gfd/gfd_qcdatabase_2019_08_01.csv")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_gfd_event_catalog.json")
COUNTRY_NAMES = {"myanmar", "burma"}


def parse_date(value: str) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    return datetime.strptime(value, "%m/%d/%Y").date().isoformat()


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing downloaded GFD QC metadata: {SOURCE}")
    events: list[dict[str, object]] = []
    with SOURCE.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            country = (row.get("Country") or "").strip()
            glide = (row.get("GlideNumber") or "").strip()
            if country.casefold() not in COUNTRY_NAMES and not glide.endswith("-MMR"):
                continue
            events.append({
                "event_id": str(row["ID"]).strip(),
                "threshold_type": (row.get("ThreshType") or "").strip(),
                "country_recorded": country,
                "glide_number": glide or None,
                "start_date": parse_date(row.get("Began") or ""),
                "end_date": parse_date(row.get("Ended") or ""),
                "centroid": {"longitude": float(row["long"]), "latitude": float(row["lat"])},
                "area_recorded_km2": float(row["Area"]) if (row.get("Area") or "").strip() else None,
                "validation_source": (row.get("Validation") or "").strip() or None,
                "main_cause": (row.get("MainCause") or "").strip() or None,
                "severity": float(row["Severity"]) if (row.get("Severity") or "").strip() else None,
            })
    events.sort(key=lambda event: (event["start_date"] or "", event["event_id"]))
    unique_ids = {event["event_id"] for event in events}
    if len(unique_ids) != len(events):
        raise RuntimeError("GFD Myanmar catalog contains duplicate event IDs")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "deltawatch-myanmar-gfd-event-catalog-v1",
        "source": {
            "dataset": "Global Flood Database quality-control database",
            "repository": "https://github.com/cloudtostreet/MODIS_GlobalFloodDatabase",
            "file": "data/gfd_qcdatabase_2019_08_01.csv",
            "selection": "Country is Myanmar or Burma, or GLIDE identifier ends with -MMR",
            "historical_coverage": "2000-2018; source labels are historical and not real-time flood evidence",
        },
        "event_count": len(events),
        "events": events,
        "limits": [
            "Catalog selection is based on source metadata and is not a complete census of Myanmar floods.",
            "No flood-raster archive, cell label, feature table, model score, probability, or alert is produced by this step.",
            "Cross-border event geometry and country labels must be handled explicitly during any later regional validation.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "event_count": len(events), "event_ids": [event["event_id"] for event in events]}, indent=2))


if __name__ == "__main__":
    main()
