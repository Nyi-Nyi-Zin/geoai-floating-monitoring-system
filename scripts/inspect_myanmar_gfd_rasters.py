"""Inspect acquired GFD raster metadata and conservative Admin 1 overlap.

The script opens one TIFF at a time from each verified ZIP archive. It reports raster
metadata and bounding-box intersections only; it never reads flood pixels to create
labels and never trains or scores a model.
"""

from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

import rasterio


ARCHIVES = Path("/home/ubuntu/deltawatch-gfd-myanmar")
PARTITIONS = Path("/home/ubuntu/webdev-static-assets/myanmar_admin1_partitions_v1.json")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_gfd_raster_metadata.json")


def intersects(first: dict[str, float], second: dict[str, float]) -> bool:
    return not (first["east"] < second["west"] or first["west"] > second["east"] or first["north"] < second["south"] or first["south"] > second["north"])


def inspect_archive(path: Path, partitions: list[dict[str, object]]) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="myanmar-gfd-meta-") as temporary:
        with zipfile.ZipFile(path) as archive:
            tif_name = next(name for name in archive.namelist() if name.lower().endswith(".tif"))
            archive.extract(tif_name, temporary)
        with rasterio.open(Path(temporary) / tif_name) as dataset:
            bounds = {"west": dataset.bounds.left, "south": dataset.bounds.bottom, "east": dataset.bounds.right, "north": dataset.bounds.top}
            overlapping = [partition["admin1_pcode"] for partition in partitions if intersects(bounds, partition["bounds"])]
            return {
                "archive_name": path.name,
                "tif_name": tif_name,
                "crs": str(dataset.crs),
                "width": dataset.width,
                "height": dataset.height,
                "band_count": dataset.count,
                "pixel_size": {"x": dataset.transform.a, "y": abs(dataset.transform.e)},
                "bounds": bounds,
                "admin1_bbox_overlap_count": len(overlapping),
                "admin1_bbox_overlap_pcodes": overlapping,
                "overlap_method": "bounding-box only; later label extraction must use true Admin 1 polygons",
            }


def main() -> None:
    partition_seed = json.loads(PARTITIONS.read_text(encoding="utf-8"))
    partitions = partition_seed["partitions"]
    records = [inspect_archive(path, partitions) for path in sorted(ARCHIVES.glob("DFO_*.zip"))]
    payload = {
        "schema": "deltawatch-myanmar-gfd-raster-metadata-v1",
        "event_count": len(records),
        "records": records,
        "limits": [
            "Raster metadata and bounding-box overlap only; no flood pixels were read for labels.",
            "Bounding-box overlap overstates possible regional coverage and must not be used as a flood label or model feature.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "event_count": len(records), "crs": sorted({record["crs"] for record in records}), "max_overlap": max(record["admin1_bbox_overlap_count"] for record in records)}, indent=2))


if __name__ == "__main__":
    main()
