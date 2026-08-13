from pathlib import Path

import pytest

from scripts.prepare_terrain_grid import dataset_id, validate_geotiff


def test_dataset_id_includes_cell_size() -> None:
    assert dataset_id(500) == "maubin-copdem-glo30-500m-v1"


def test_validate_geotiff_accepts_little_endian_header(tmp_path: Path) -> None:
    raster = tmp_path / "terrain.tif"
    raster.write_bytes(b"II*\x00" + b"\x00" * 8)

    assert validate_geotiff(raster).startswith(b"II*\x00")


def test_validate_geotiff_rejects_other_files(tmp_path: Path) -> None:
    raster = tmp_path / "terrain.tif"
    raster.write_bytes(b"not-a-tiff")

    with pytest.raises(ValueError, match="not a valid TIFF"):
        validate_geotiff(raster)
