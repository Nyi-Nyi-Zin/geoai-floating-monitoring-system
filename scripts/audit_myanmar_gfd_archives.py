"""Audit public GFD archive sizes for the selected Myanmar metadata catalog.

This script only reads Google Cloud Storage object metadata. It does not download,
extract, or label the flood rasters.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen


CATALOG = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_gfd_event_catalog.json")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_gfd_archive_audit.json")
BUCKET = "gfd_v1_4"


def request_json(url: str) -> dict:
    with urlopen(url, timeout=90) as response:
        return json.load(response)


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    records: list[dict[str, object]] = []
    for event in catalog["events"]:
        event_id = str(event["event_id"])
        payload = request_json(f"https://storage.googleapis.com/storage/v1/b/{BUCKET}/o?prefix={quote(f'DFO_{event_id}_')}")
        items = payload.get("items", [])
        if len(items) != 1:
            raise RuntimeError(f"Expected exactly one GFD archive for event {event_id}; received {len(items)}")
        item = items[0]
        records.append({
            "event_id": event_id,
            "start_date": event["start_date"],
            "archive_name": item["name"],
            "size_bytes": int(item["size"]),
            "content_type": item.get("contentType"),
            "updated": item.get("updated"),
        })
    total_bytes = sum(record["size_bytes"] for record in records)
    payload = {
        "schema": "deltawatch-myanmar-gfd-archive-audit-v1",
        "bucket": BUCKET,
        "event_count": len(records),
        "total_bytes": total_bytes,
        "total_megabytes": round(total_bytes / 1_000_000, 2),
        "records": records,
        "limits": [
            "This is object metadata only; no archive bytes were downloaded.",
            "Archive size does not establish regional label quality, model accuracy, or operational readiness.",
            "Any later extraction must process bounded Admin 1 partitions and retain temporal holdouts.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "event_count": len(records), "total_megabytes": payload["total_megabytes"], "largest_megabytes": round(max(record["size_bytes"] for record in records) / 1_000_000, 2)}, indent=2))


if __name__ == "__main__":
    main()
