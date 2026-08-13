from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.flood_ml import (
    FloodEventMlEvaluationReport,
    FloodEventMlModelSummary,
    FloodEventMlPredictionIndex,
    FloodEventReadiness,
    FloodMlModelSummary,
    FloodMlPredictionIndex,
)
from app.services.flood_ml import FloodMlService

router = APIRouter(prefix="/flood-ml", tags=["flood-ml"])


@router.get(
    "/models/latest",
    response_model=FloodMlModelSummary,
    summary="Get the latest trained historical susceptibility model",
)
def latest_model(db: Session = Depends(get_db)) -> FloodMlModelSummary:
    return FloodMlService(db).latest_model()


@router.get(
    "/predictions/index",
    response_model=FloodMlPredictionIndex,
    summary="Get compact terrain-cell historical susceptibility probabilities",
)
def prediction_index(db: Session = Depends(get_db)) -> FloodMlPredictionIndex:
    return FloodMlService(db).prediction_index()


@router.get(
    "/event-readiness",
    response_model=FloodEventReadiness,
    summary="Check readiness for event-date and rainfall-aligned model training",
)
def event_readiness(db: Session = Depends(get_db)) -> FloodEventReadiness:
    return FloodMlService(db).event_readiness()


@router.get(
    "/event-models/latest",
    response_model=FloodEventMlModelSummary,
    summary="Get the latest experimental rainfall-aligned event model",
)
def latest_event_model(db: Session = Depends(get_db)) -> FloodEventMlModelSummary:
    return FloodMlService(db).latest_event_model()


@router.get(
    "/event-models/evaluation",
    response_model=FloodEventMlEvaluationReport,
    summary="Get rolling CV, per-event, and false-alarm evaluation for the event model",
)
def event_model_evaluation(
    db: Session = Depends(get_db),
) -> FloodEventMlEvaluationReport:
    return FloodMlService(db).event_model_evaluation()


@router.get(
    "/event-predictions/index",
    response_model=FloodEventMlPredictionIndex,
    summary="Get historical event hindcast probabilities for terrain cells",
)
def event_prediction_index(
    event_id: str | None = None,
    threshold_mode: Literal["screening", "balanced", "conservative"] = "conservative",
    db: Session = Depends(get_db),
) -> FloodEventMlPredictionIndex:
    return FloodMlService(db).event_prediction_index(event_id, threshold_mode)
