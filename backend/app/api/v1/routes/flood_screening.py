from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.flood_screening import (
    LandCoverSummary,
    ScreeningBand,
    TerrainScreeningCollection,
    TerrainScreeningIndex,
)
from app.services.flood_screening import FloodScreeningService

router = APIRouter(prefix="/flood-screening", tags=["flood-screening"])

Page = Annotated[int, Query(ge=1, description="One-based page number")]
PageSize = Annotated[
    int,
    Query(ge=1, le=6000, description="Items per page (maximum 6,000)"),
]


@router.get(
    "/land-cover/summary",
    response_model=LandCoverSummary,
    summary="Summarize ESA WorldCover classes linked to terrain cells",
)
def land_cover_summary(
    db: Session = Depends(get_db),
) -> LandCoverSummary:
    return FloodScreeningService(db).land_cover_summary()


@router.get(
    "/terrain/index",
    response_model=TerrainScreeningIndex,
    summary="Get compact map-ready terrain screening scores",
)
def terrain_screening_index(
    db: Session = Depends(get_db),
) -> TerrainScreeningIndex:
    return FloodScreeningService(db).terrain_index()


@router.get(
    "/terrain",
    response_model=TerrainScreeningCollection,
    summary="Screen relative terrain susceptibility without claiming prediction",
)
def terrain_screening(
    page: Page = 1,
    page_size: PageSize = 6000,
    band: ScreeningBand | None = None,
    include_geometry: bool = Query(
        default=True,
        description="Set false when joining scores to terrain cells already loaded.",
    ),
    db: Session = Depends(get_db),
) -> TerrainScreeningCollection:
    return FloodScreeningService(db).terrain(
        page=page,
        page_size=page_size,
        band=band,
        include_geometry=include_geometry,
    )
