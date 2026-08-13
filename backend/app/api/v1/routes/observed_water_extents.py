from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.observed_water_extent import (
    ObservedWaterExtentCollection,
    ObservedWaterExtentCreate,
    ObservedWaterExtentFeature,
)
from app.services.observed_water_extent import ObservedWaterExtentService

router = APIRouter(
    prefix="/observed-water-extents",
    tags=["observed-water-extents"],
)
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=500)]


@router.post(
    "",
    response_model=ObservedWaterExtentFeature,
    status_code=status.HTTP_201_CREATED,
    summary="Store a satellite-observed water extent snapshot",
)
def create_observed_water_extent(
    payload: ObservedWaterExtentCreate,
    db: Session = Depends(get_db),
) -> ObservedWaterExtentFeature:
    return ObservedWaterExtentService(db).create(payload)


@router.get(
    "",
    response_model=ObservedWaterExtentCollection,
    summary="List observed water surface snapshots for map display",
)
def list_observed_water_extents(
    page: Page = 1,
    page_size: PageSize = 100,
    start_date: date | None = None,
    end_date: date | None = None,
    source: str | None = None,
    db: Session = Depends(get_db),
) -> ObservedWaterExtentCollection:
    return ObservedWaterExtentService(db).list(
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        source=source,
    )


@router.get(
    "/{extent_id}",
    response_model=ObservedWaterExtentFeature,
    summary="Get one observed water extent and its provenance",
)
def get_observed_water_extent(
    extent_id: UUID,
    db: Session = Depends(get_db),
) -> ObservedWaterExtentFeature:
    return ObservedWaterExtentService(db).get(extent_id)
