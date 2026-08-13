from datetime import date
from typing import Annotated

from fastapi import Depends
from fastapi import APIRouter, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.rainfall_history import RainfallHistoryResponse
from app.schemas.weather import RainfallForecastResponse
from app.services.rainfall_history import RainfallHistoryService
from app.services.weather import get_rainfall_forecast

router = APIRouter(prefix="/weather", tags=["weather"])

HistoryDate = Annotated[
    date | None,
    Query(description="Optional inclusive date in YYYY-MM-DD format"),
]


@router.get(
    "/rainfall-history",
    response_model=RainfallHistoryResponse,
    summary="Get area-weighted Maubin ERA5 historical rainfall",
)
def rainfall_history(
    start_date: HistoryDate = None,
    end_date: HistoryDate = None,
    limit: int = Query(default=366, ge=1, le=10_000),
    db: Session = Depends(get_db),
) -> RainfallHistoryResponse:
    return RainfallHistoryService(db).list_history(
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


@router.get(
    "/rainfall-forecast",
    response_model=RainfallForecastResponse,
    summary="Get a real weather-model rainfall forecast for Maubin",
)
def rainfall_forecast(
    forecast_days: int = Query(default=7, ge=1, le=7),
) -> RainfallForecastResponse:
    return get_rainfall_forecast(forecast_days)
