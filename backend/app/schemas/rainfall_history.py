from datetime import date
from typing import Literal

from pydantic import BaseModel


class RainfallHistoryDay(BaseModel):
    date: date
    mean_precipitation_mm: float
    max_precipitation_mm: float
    p90_precipitation_mm: float
    accumulation_3d_mm: float
    accumulation_7d_mm: float
    accumulation_30d_mm: float


class RainfallHistorySummary(BaseModel):
    start_date: date | None
    end_date: date | None
    days: int
    wet_days: int
    total_mean_precipitation_mm: float
    peak_daily_mean_mm: float
    peak_daily_mean_date: date | None
    peak_7d_mm: float
    peak_7d_end_date: date | None


class RainfallHistoryResponse(BaseModel):
    status: Literal["available", "unavailable"]
    source_key: str
    source_name: str
    model: Literal["ERA5"]
    source_resolution_m: int
    grid_cell_count: int
    daily: list[RainfallHistoryDay]
    summary: RainfallHistorySummary
    attribution: str
    limitations: list[str]
