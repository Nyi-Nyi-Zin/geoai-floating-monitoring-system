"""Download only the 17 officially resolved GFD archives needed for Maubin labels."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import urlopen


PROJECT = Path("/home/ubuntu/deltawatch-permanent")
MANIFEST = Path("/home/ubuntu/deltawatch-model-outputs/gfd_object_manifest.json")
DESTINATION = Path("/home/ubuntu/deltawatch-gfd-v1")


def main() -> None:
    records = json.loads(MANIFEST.read_text(encoding="utf-8"))
    DESTINATION.mkdir(parents=True, exist_ok=True)
    downloaded = []
    for record in records:
        destination = DESTINATION / record["name"]
        expected_size = int(record["size_bytes"])
        if destination.exists() and destination.stat().st_size == expected_size:
            downloaded.append({"event_id": record["event_id"], "status": "cached", "bytes": expected_size})
            continue
        with urlopen(record["media_url"], timeout=300) as response, destination.open("wb") as handle:
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)
        actual_size = destination.stat().st_size
        if actual_size != expected_size:
            destination.unlink(missing_ok=True)
            raise RuntimeError(f"Size mismatch for event {record['event_id']}: {actual_size} != {expected_size}")
        downloaded.append({"event_id": record["event_id"], "status": "downloaded", "bytes": actual_size})
    print(json.dumps({"destination": str(DESTINATION), "files": downloaded}, indent=2))


if __name__ == "__main__":
    main()
