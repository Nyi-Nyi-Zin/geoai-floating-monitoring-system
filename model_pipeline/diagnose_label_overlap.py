"""Compare cell-event overlap thresholds with the established v6 validation label count."""

from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import shape


STATIC = Path("/home/ubuntu/webdev-static-assets")
VALIDATION_EVENT_IDS = {"4283", "4355", "4365"}
THRESHOLDS = [0.0, 0.001, 0.01, 0.025, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    spatial = load(STATIC / "maubin_spatial_seed.json")
    hindcast = load(STATIC / "maubin_hindcast_seed.json")
    cells = [shape(feature["geometry"]) for feature in spatial["features"] if feature.get("properties", {}).get("asset_type") == "terrain_cell"]
    events = [event for event in hindcast["events"] if str(event["id"]) in VALIDATION_EVENT_IDS]
    results = []
    for threshold in THRESHOLDS:
        total = 0
        per_event = {}
        for event in events:
            geometry = shape(event["geometry"])
            positive = 0
            for cell in cells:
                overlap = geometry.intersection(cell).area / cell.area
                if overlap > threshold:
                    positive += 1
            per_event[str(event["id"])] = positive
            total += positive
        results.append({"minimum_overlap_fraction": threshold, "total": total, "per_event": per_event, "difference_from_v6_positives": total - 1174})
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
