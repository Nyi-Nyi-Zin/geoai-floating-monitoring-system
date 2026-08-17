"""Summarize historical GFD flood coverage by true Myanmar Admin 1 polygons.

This produces event-level observed-source coverage statistics, not a predictive model.
It reads the native flood and permanent-water bands from the acquired GFD rasters and
uses the vetted full Admin 1 polygon geometry for masking.
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


CATALOG = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_gfd_event_catalog.json")
ARCHIVE_AUDIT = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_gfd_archive_audit.json")
ADMIN1 = Path("/home/ubuntu/nationwide-data/mmr_admin_boundaries/mmr_admin1.geojson")
ARCHIVES = Path("/home/ubuntu/deltawatch-gfd-myanmar")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_gfd_admin1_historical_coverage.csv")
SUMMARY = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_gfd_admin1_historical_coverage_summary.json")


def extract_tif(archive_path: Path, destination: Path) -> Path:
    with zipfile.ZipFile(archive_path) as archive:
        tif_name = next(name for name in archive.namelist() if name.lower().endswith(".tif"))
        archive.extract(tif_name, destination)
    return destination / tif_name


def coverage(dataset: rasterio.io.DatasetReader, geometry) -> tuple[str, int, int, float]:
    try:
        data, _ = mask(dataset, [mapping(geometry)], indexes=[1, 5], crop=True, all_touched=False, filled=False)
    except ValueError:
        return "no_raster_overlap", 0, 0, 0.0
    flooded = data[0]
    permanent_water = data[1]
    valid = ~(flooded.mask | permanent_water.mask)
    valid_count = int(valid.sum())
    if not valid_count:
        return "no_valid_source_pixels", 0, 0, 0.0
    flooded_count = int(((flooded.data == 1) & (permanent_water.data == 0) & valid).sum())
    return "observed", valid_count, flooded_count, round(flooded_count / valid_count, 8)


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    audit = json.loads(ARCHIVE_AUDIT.read_text(encoding="utf-8"))
    event_dates = {str(event["event_id"]): event["start_date"] for event in catalog["events"]}
    archives = {Path(record["archive_name"]).name: record for record in audit["records"]}
    admin1 = json.loads(ADMIN1.read_text(encoding="utf-8"))
    regions = [{
        "pcode": feature["properties"]["adm1_pcode"],
        "name": feature["properties"]["adm1_name"],
        "geometry": shape(feature["geometry"]),
    } for feature in admin1["features"]]
    if len(regions) != 18:
        raise RuntimeError(f"Expected 18 Admin 1 polygons, received {len(regions)}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for archive_name, record in sorted(archives.items(), key=lambda item: event_dates[str(item[1]["event_id"])]):
        with tempfile.TemporaryDirectory(prefix="myanmar-gfd-coverage-") as temp_dir:
            tif_path = extract_tif(ARCHIVES / archive_name, Path(temp_dir))
            with rasterio.open(tif_path) as dataset:
                for region in regions:
                    status, valid_pixels, flooded_pixels, flooded_fraction = coverage(dataset, region["geometry"])
                    rows.append({
                        "event_id": record["event_id"],
                        "event_start": event_dates[str(record["event_id"])],
                        "admin1_pcode": region["pcode"],
                        "admin1_name": region["name"],
                        "coverage_status": status,
                        "valid_pixel_count": valid_pixels,
                        "flooded_pixel_count": flooded_pixels,
                        "flooded_fraction": flooded_fraction,
                        "observed_flood_presence": int(flooded_pixels > 0),
                    })
    fields = ["event_id", "event_start", "admin1_pcode", "admin1_name", "coverage_status", "valid_pixel_count", "flooded_pixel_count", "flooded_fraction", "observed_flood_presence"]
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    observed_rows = [row for row in rows if row["coverage_status"] == "observed"]
    positive_rows = [row for row in observed_rows if row["observed_flood_presence"]]
    summary = {
        "schema": "deltawatch-myanmar-gfd-admin1-historical-coverage-v1",
        "events": len(archives),
        "admin1_regions": len(regions),
        "rows": len(rows),
        "observed_rows": len(observed_rows),
        "flood_positive_rows": len(positive_rows),
        "source_method": "GFD native band 1 flood pixels, excluding permanent water in native band 5, masked by true Admin 1 polygons",
        "limits": [
            "Administrative-region flood coverage is an observed historical source summary, not a calibrated per-cell label set.",
            "This summary does not construct features, train a model, report a probability, or issue an alert.",
            "GFD event selection and historical coverage do not establish prospective nationwide performance.",
        ],
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **summary}, indent=2))


if __name__ == "__main__":
    main()
