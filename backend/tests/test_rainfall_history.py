from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.rainfall_history import RainfallHistoryService


def rainfall_row(
    observed_date: date,
    mean_mm: float,
    accumulation_7d_mm: float,
):
    return SimpleNamespace(
        observed_date=observed_date,
        mean_precipitation_mm=mean_mm,
        max_precipitation_mm=mean_mm + 2,
        p90_precipitation_mm=mean_mm + 1,
        accumulation_3d_mm=mean_mm,
        accumulation_7d_mm=accumulation_7d_mm,
        accumulation_30d_mm=accumulation_7d_mm,
        grid_cell_count=6,
    )


def test_rainfall_history_summary_exposes_peaks_and_limits() -> None:
    db = MagicMock()
    db.scalars.return_value = [
        rainfall_row(date(2024, 7, 2), 12.0, 18.0),
        rainfall_row(date(2024, 7, 1), 5.0, 5.0),
    ]

    result = RainfallHistoryService(db).list_history(
        start_date=None,
        end_date=None,
        limit=366,
    )

    assert result.status == "available"
    assert [item.date for item in result.daily] == [
        date(2024, 7, 1),
        date(2024, 7, 2),
    ]
    assert result.summary.total_mean_precipitation_mm == 17
    assert result.summary.peak_daily_mean_date == date(2024, 7, 2)
    assert result.summary.peak_7d_mm == 18
    assert any("not a Maubin rain-gauge" in item for item in result.limitations)


def test_openapi_lists_rainfall_history_endpoint(client) -> None:
    openapi = client.get("/openapi.json").json()

    assert "/api/v1/weather/rainfall-history" in openapi["paths"]
