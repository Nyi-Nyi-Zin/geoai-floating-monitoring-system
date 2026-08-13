from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.flood_extent import (
    FloodClassification,
    FloodExtentCollection,
    FloodExtentCreate,
    FloodExtentFeature,
)
from app.services.flood_extent import FloodExtentService

router = APIRouter(prefix="/flood-extents", tags=["flood-extents"])
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=500)]


@router.post(
    "",
    response_model=FloodExtentFeature,
    status_code=status.HTTP_201_CREATED,
    summary="Store a provenance-aware historical flood extent",
)
def create_flood_extent(
    payload: FloodExtentCreate,
    db: Session = Depends(get_db),
) -> FloodExtentFeature:
    return FloodExtentService(db).create(payload)


@router.get(
    "",
    response_model=FloodExtentCollection,
    summary="List historical flood labels for mapping and model training",
)
def list_flood_extents(
    page: Page = 1,
    page_size: PageSize = 100,
    start_date: date | None = None,
    end_date: date | None = None,
    classification: FloodClassification | None = None,
    db: Session = Depends(get_db),
) -> FloodExtentCollection:
    return FloodExtentService(db).list(
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        classification=classification,
    )


@router.get(
    "/{extent_id}",
    response_model=FloodExtentFeature,
    summary="Get one historical flood extent and its provenance",
)
def get_flood_extent(
    extent_id: UUID,
    db: Session = Depends(get_db),
) -> FloodExtentFeature:
    return FloodExtentService(db).get(extent_id)
