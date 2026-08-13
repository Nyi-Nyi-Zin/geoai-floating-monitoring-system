from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a prepared GeoJSON FeatureCollection through the API."
    )
    parser.add_argument("file", type=Path)
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000/api/v1/geo-assets/import",
    )
    return parser.parse_args()


def load_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "FeatureCollection":
        raise ValueError("Import file must be a GeoJSON FeatureCollection")
    return {
        "type": "FeatureCollection",
        "features": payload.get("features", []),
    }


def main() -> None:
    args = parse_args()
    response = httpx.post(
        args.api_url,
        json=load_payload(args.file),
        timeout=120,
    )
    response.raise_for_status()
    result = response.json()
    print(f"Imported {result['meta']['total']} GeoAssets.")


if __name__ == "__main__":
    main()
