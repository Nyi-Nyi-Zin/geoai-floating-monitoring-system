"""Resolve public Google Cloud Storage objects for the Maubin GFD event IDs."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen


PROJECT = Path("/home/ubuntu/deltawatch-permanent")
STATIC = Path("/home/ubuntu/webdev-static-assets")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs")
EVENT_IDS = ["2041", "2276", "2473", "2507", "2859", "3068", "3125", "3134", "3169", "3208", "3302", "3530", "4283", "4355", "4365", "4632", "4666"]


def request_json(url: str) -> dict:
    with urlopen(url, timeout=90) as response:
        return json.load(response)


def main() -> None:
    records = []
    for event_id in EVENT_IDS:
        prefix = f"DFO_{event_id}_"
        payload = request_json(f"https://storage.googleapis.com/storage/v1/b/gfd_v1_4/o?prefix={quote(prefix)}")
        items = payload.get("items", [])
        if len(items) != 1:
            raise RuntimeError(f"Expected one GFD object for event {event_id}; received {len(items)}")
        item = items[0]
        records.append({
            "event_id": event_id,
            "name": item["name"],
            "size_bytes": int(item["size"]),
            "media_url": f"https://storage.googleapis.com/download/storage/v1/b/gfd_v1_4/o/{quote(item['name'], safe='')}?alt=media",
        })
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "gfd_object_manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps({"event_count": len(records), "total_bytes": sum(item["size_bytes"] for item in records), "objects": records}, indent=2))


if __name__ == "__main__":
    main()
