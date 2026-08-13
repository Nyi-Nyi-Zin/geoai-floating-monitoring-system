from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.hydro_observation import (
    HydroObservationCollection,
    HydroObservationCreate,
    HydroObservationFeature,
    HydroObservationUpdate,
    QualityStatus,
)
from app.services.hydro_observation import HydroObservationService

router = APIRouter(prefix="/hydro-observations", tags=["hydro-observations"])

Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=500)]


@router.post(
    "",
    response_model=HydroObservationFeature,
    status_code=status.HTTP_201_CREATED,
    summary="Record a rainfall, river-level, or discharge observation",
)
def create_hydro_observation(
    payload: HydroObservationCreate,
    db: Session = Depends(get_db),
) -> HydroObservationFeature:
    return HydroObservationService(db).create(payload)


@router.get(
    "",
    response_model=HydroObservationCollection,
    summary="List hydrometeorology observations",
)
def list_hydro_observations(
    page: Page = 1,
    page_size: PageSize = 100,
    station_id: str | None = Query(default=None, min_length=1, max_length=100),
    quality_status: QualityStatus | None = None,
    observed_from: datetime | None = None,
    observed_to: datetime | None = None,
    db: Session = Depends(get_db),
) -> HydroObservationCollection:
    return HydroObservationService(db).list(
        page=page,
        page_size=page_size,
        station_id=station_id,
        quality_status=quality_status,
        observed_from=observed_from,
        observed_to=observed_to,
    )


@router.get(
    "/latest",
    response_model=HydroObservationCollection,
    summary="Get the latest observation from each station",
)
def latest_hydro_observations(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> HydroObservationCollection:
    return HydroObservationService(db).latest(limit)


@router.get(
    "/{observation_id}",
    response_model=HydroObservationFeature,
    summary="Get a hydrometeorology observation",
)
def get_hydro_observation(
    observation_id: UUID,
    db: Session = Depends(get_db),
) -> HydroObservationFeature:
    return HydroObservationService(db).get(observation_id)


@router.patch(
    "/{observation_id}",
    response_model=HydroObservationFeature,
    summary="Review an observation quality flag or notes",
)
def update_hydro_observation(
    observation_id: UUID,
    payload: HydroObservationUpdate,
    db: Session = Depends(get_db),
) -> HydroObservationFeature:
    return HydroObservationService(db).update(observation_id, payload)
