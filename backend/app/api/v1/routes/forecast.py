from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.forecast import (
    ForecastPredictionIndex,
    ForecastRunCreate,
    ForecastRunList,
    ForecastRunSummary,
)
from app.services.forecast import ForecastService

router = APIRouter(prefix="/flood-forecast", tags=["flood-forecast"])


@router.post(
    "/runs",
    response_model=ForecastRunSummary,
    status_code=201,
    summary="Execute a new flood forecast run",
    description=(
        "Triggers a live flood forecast by fetching the latest Open-Meteo "
        "rainfall forecast, combining it with ERA5 historical rainfall, "
        "and running inference on all terrain cells using the trained event "
        "model. Results are persisted as an immutable forecast run."
    ),
)
def create_forecast_run(
    body: ForecastRunCreate | None = None,
    db: Session = Depends(get_db),
) -> ForecastRunSummary:
    request = body or ForecastRunCreate()
    return ForecastService(db).execute_forecast_run(request)


@router.get(
    "/runs",
    response_model=ForecastRunList,
    summary="List past forecast runs",
)
def list_forecast_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ForecastRunList:
    return ForecastService(db).list_runs(limit=limit)


@router.get(
    "/runs/latest",
    response_model=ForecastRunSummary,
    summary="Get the latest completed forecast run summary",
)
def latest_forecast_run(
    db: Session = Depends(get_db),
) -> ForecastRunSummary:
    return ForecastService(db).latest_run_summary()


@router.get(
    "/runs/{run_id}",
    response_model=ForecastPredictionIndex,
    summary="Get a specific forecast run with all predictions",
)
def get_forecast_run(
    run_id: str,
    db: Session = Depends(get_db),
) -> ForecastPredictionIndex:
    return ForecastService(db).get_run_predictions(run_id)


@router.get(
    "/predictions/index",
    response_model=ForecastPredictionIndex,
    summary="Get the latest forecast predictions for map display",
    description=(
        "Returns the latest completed forecast run's per-cell predictions "
        "in a format suitable for dashboard map layer rendering."
    ),
)
def forecast_prediction_index(
    db: Session = Depends(get_db),
) -> ForecastPredictionIndex:
    return ForecastService(db).get_run_predictions()
