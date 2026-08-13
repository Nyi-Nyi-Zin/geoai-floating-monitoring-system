from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class RainfallForecastHour(BaseModel):
    time: datetime
    precipitation_mm: float
    probability_percent: int | None


class RainfallForecastDay(BaseModel):
    date: date
    precipitation_sum_mm: float
    probability_max_percent: int | None


class ForecastLocation(BaseModel):
    name: str
    latitude: float
    longitude: float
    timezone: str


class RainfallForecastResponse(BaseModel):
    status: Literal["available"] = "available"
    location: ForecastLocation
    fetched_at: datetime
    source: str
    attribution_url: str
    cached: bool
    hourly: list[RainfallForecastHour]
    daily: list[RainfallForecastDay]
