"""Download the bounded, audited Myanmar GFD archive set with size and SHA-256 checks.

Archives remain in a sandbox-only directory and are never included in the deployed
web project. This acquisition step does not extract labels or train a model.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen


AUDIT = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_gfd_archive_audit.json")
DESTINATION = Path("/home/ubuntu/deltawatch-gfd-myanmar")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def download(record: dict[str, object]) -> dict[str, object]:
    destination = DESTINATION / str(record["archive_name"])
    expected_size = int(record["size_bytes"])
    if destination.exists() and destination.stat().st_size == expected_size:
        return {"event_id": record["event_id"], "status": "cached", "bytes": expected_size, "sha256": sha256(destination)}
    temporary = destination.with_suffix(f"{destination.suffix}.part")
    temporary.unlink(missing_ok=True)
    encoded_name = quote(str(record["archive_name"]), safe="")
    url = f"https://storage.googleapis.com/download/storage/v1/b/gfd_v1_4/o/{encoded_name}?alt=media"
    with urlopen(url, timeout=300) as response, temporary.open("wb") as handle:
        while chunk := response.read(1024 * 1024):
            handle.write(chunk)
    actual_size = temporary.stat().st_size
    if actual_size != expected_size:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Size mismatch for {record['event_id']}: {actual_size} != {expected_size}")
    temporary.replace(destination)
    return {"event_id": record["event_id"], "status": "downloaded", "bytes": actual_size, "sha256": sha256(destination)}


def main() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    DESTINATION.mkdir(parents=True, exist_ok=True)
    records = [download(record) for record in audit["records"]]
    manifest = {
        "schema": "deltawatch-myanmar-gfd-local-archive-manifest-v1",
        "source_audit": str(AUDIT),
        "destination": str(DESTINATION),
        "event_count": len(records),
        "records": records,
        "limits": [
            "Sandbox-only archive manifest; no archives are packaged with the web application.",
            "Acquisition does not create labels, features, model scores, probabilities, or alerts.",
        ],
    }
    (DESTINATION / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"event_count": len(records), "downloaded": sum(item["status"] == "downloaded" for item in records), "cached": sum(item["status"] == "cached" for item in records), "destination": str(DESTINATION)}, indent=2))


if __name__ == "__main__":
    main()
