"""Calculate 500 m terrain-cell labels from official GFD native flood rasters.

The target is the proportion of valid pixels inside a cell that are flooded while not
classified as permanent water. A cell is positive when this fraction is non-zero.
"""

from __future__ import annotations

import csv
import json
import tempfile
import zipfile
from pathlib import Path

import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping, shape


PROJECT = Path("/home/ubuntu/deltawatch-permanent")
STATIC = Path("/home/ubuntu/webdev-static-assets")
ARCHIVES = Path("/home/ubuntu/deltawatch-gfd-v1")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_tif(archive_path: Path, destination: Path) -> Path:
    with zipfile.ZipFile(archive_path) as archive:
        tif_name = next(name for name in archive.namelist() if name.lower().endswith(".tif"))
        archive.extract(tif_name, destination)
    return destination / tif_name


def cell_measurements(dataset: rasterio.io.DatasetReader, geometry) -> tuple[int, float, int]:
    try:
        data, _ = mask(dataset, [mapping(geometry)], indexes=[1, 5], crop=True, all_touched=True, filled=False)
    except ValueError:
        return 0, 0.0, 0
    flooded = data[0]
    permanent = data[1]
    valid = ~(flooded.mask | permanent.mask)
    valid_count = int(valid.sum())
    if not valid_count:
        return 0, 0.0, 0
    flood_pixels = ((flooded.data == 1) & (permanent.data == 0) & valid)
    fraction = float(flood_pixels.sum() / valid_count)
    return int(flood_pixels.any()), round(fraction, 6), valid_count


def main() -> None:
    spatial = load_json(STATIC / "maubin_spatial_seed.json")
    hindcast = load_json(STATIC / "maubin_hindcast_seed.json")
    cells = [
        {"cell_id": str(feature["properties"]["id"]), "geometry": shape(feature["geometry"])}
        for feature in spatial["features"]
        if feature.get("properties", {}).get("asset_type") == "terrain_cell"
    ]
    events = sorted(hindcast["events"], key=lambda item: item["start_date"])
    manifest = {item["event_id"]: item for item in load_json(OUTPUT / "gfd_object_manifest.json")}
    output_path = OUTPUT / "native_gfd_cell_labels.csv"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    event_summary = []
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_id", "event_start", "cell_id", "flooded_label", "flood_fraction", "valid_pixel_count"])
        writer.writeheader()
        for event in events:
            event_id = str(event["id"])
            archive_path = ARCHIVES / manifest[event_id]["name"]
            with tempfile.TemporaryDirectory(prefix=f"gfd-{event_id}-") as temp_dir:
                tif_path = extract_tif(archive_path, Path(temp_dir))
                positive_cells = 0
                flood_fraction_sum = 0.0
                with rasterio.open(tif_path) as dataset:
                    for cell in cells:
                        label, fraction, valid_pixel_count = cell_measurements(dataset, cell["geometry"])
                        positive_cells += label
                        flood_fraction_sum += fraction
                        writer.writerow({
                            "event_id": event_id,
                            "event_start": event["start_date"],
                            "cell_id": cell["cell_id"],
                            "flooded_label": label,
                            "flood_fraction": fraction,
                            "valid_pixel_count": valid_pixel_count,
                        })
            event_summary.append({
                "event_id": event_id,
                "event_start": event["start_date"],
                "positive_cells": positive_cells,
                "mean_flood_fraction_across_cells": round(flood_fraction_sum / len(cells), 8),
            })
            print(json.dumps(event_summary[-1]))
    (OUTPUT / "native_gfd_label_summary.json").write_text(json.dumps(event_summary, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output_path), "events": len(events), "cells": len(cells), "rows": len(events) * len(cells)}, indent=2))


if __name__ == "__main__":
    main()
