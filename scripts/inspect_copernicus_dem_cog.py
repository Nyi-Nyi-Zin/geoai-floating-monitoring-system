"""Inspect a bounded Copernicus DEM COG overview read without fitting any model.

This utility confirms that remote COG access can be used for static terrain
summaries. It does not generate risk scores, probabilities, forecasts, or alerts.
"""

from __future__ import annotations

import json

import rasterio


COG_URL = (
    "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/"
    "Copernicus_DSM_COG_10_N16_00_E096_00_DEM/"
    "Copernicus_DSM_COG_10_N16_00_E096_00_DEM.tif"
)


def main() -> None:
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
    ):
        with rasterio.open(COG_URL) as dataset:
            sample = dataset.read(
                1,
                out_shape=(1, 64, 64),
                masked=True,
                resampling=rasterio.enums.Resampling.average,
            )
            payload = {
                "source": COG_URL,
                "crs": str(dataset.crs),
                "width": dataset.width,
                "height": dataset.height,
                "bounds": list(dataset.bounds),
                "sample_shape": list(sample.shape),
                "valid_sample_cells": int(sample.count()),
                "sample_min_m": float(sample.min()),
                "sample_mean_m": float(sample.mean()),
                "sample_max_m": float(sample.max()),
                "safety": "Static source-access diagnostic only; no model, risk score, probability, forecast, or alert is created.",
            }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
