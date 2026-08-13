from datetime import date

import pytest
from shapely.geometry import box

from scripts.prepare_rainfall_history import (
    aggregate_history,
    grid_samples,
    parse_archive_payload,
    weighted_percentile,
)


def test_grid_samples_are_normalized_and_intersect_boundary() -> None:
    samples = grid_samples(box(95.4, 16.5, 95.9, 16.9))

    assert len(samples) >= 4
    assert sum(item["weight"] for item in samples) == pytest.approx(1)
    assert all(item["weight"] > 0 for item in samples)


def test_parse_and_aggregate_history_calculates_weighted_values() -> None:
    samples = [
        {"latitude": 16.5, "longitude": 95.5, "weight": 0.25},
        {"latitude": 16.75, "longitude": 95.75, "weight": 0.75},
    ]
    payload = [
        {
            "daily": {
                "time": ["2024-07-01", "2024-07-02"],
                "precipitation_sum": [4.0, 2.0],
            }
        },
        {
            "daily": {
                "time": ["2024-07-01", "2024-07-02"],
                "precipitation_sum": [8.0, 6.0],
            }
        },
    ]

    values = parse_archive_payload(payload, samples)
    rows = aggregate_history(values)

    assert rows[0]["observed_date"] == date(2024, 7, 1)
    assert rows[0]["mean_precipitation_mm"] == pytest.approx(7)
    assert rows[0]["max_precipitation_mm"] == 8
    assert rows[0]["p90_precipitation_mm"] == 8
    assert rows[1]["accumulation_3d_mm"] == pytest.approx(12)
    assert rows[1]["accumulation_7d_mm"] == pytest.approx(12)


def test_weighted_percentile_uses_area_weights() -> None:
    assert weighted_percentile([(1.0, 0.85), (10.0, 0.15)], 0.9) == 10.0

