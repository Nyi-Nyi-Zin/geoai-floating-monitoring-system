from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.geo_asset import (
    GeoAssetCreate,
    GeoAssetFeature,
    GeoAssetFeatureCollection,
    GeoAssetImportRequest,
    GeoAssetUpdate,
)
from app.services.geo_asset import GeoAssetService

router = APIRouter(prefix="/geo-assets", tags=["geo-assets"])

Page = Annotated[int, Query(ge=1, description="One-based page number")]
PageSize = Annotated[
    int,
    Query(ge=1, le=1000, description="Items per page (maximum 1,000)"),
]


@router.post(
    "",
    response_model=GeoAssetFeature,
    status_code=status.HTTP_201_CREATED,
    summary="Create a spatial asset",
)
def create_geo_asset(
    payload: GeoAssetCreate,
    db: Session = Depends(get_db),
) -> GeoAssetFeature:
    return GeoAssetService(db).create(payload)


@router.get(
    "",
    response_model=GeoAssetFeatureCollection,
    summary="List spatial assets",
)
def list_geo_assets(
    page: Page = 1,
    page_size: PageSize = 20,
    asset_type: str | None = Query(default=None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
) -> GeoAssetFeatureCollection:
    return GeoAssetService(db).list(
        page=page,
        page_size=page_size,
        asset_type=asset_type,
    )


# Static spatial routes must be registered before the UUID route.
@router.get(
    "/within-bounds",
    response_model=GeoAssetFeatureCollection,
    summary="List assets intersecting a WGS84 bounding box",
)
def list_geo_assets_within_bounds(
    min_lon: float = Query(ge=-180, le=180),
    min_lat: float = Query(ge=-90, le=90),
    max_lon: float = Query(ge=-180, le=180),
    max_lat: float = Query(ge=-90, le=90),
    page: Page = 1,
    page_size: PageSize = 20,
    asset_type: str | None = Query(default=None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
) -> GeoAssetFeatureCollection:
    return GeoAssetService(db).within_bounds(
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
        page=page,
        page_size=page_size,
        asset_type=asset_type,
    )


@router.post(
    "/import",
    response_model=GeoAssetFeatureCollection,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk import a prepared GeoJSON FeatureCollection",
)
def import_geo_assets(
    payload: GeoAssetImportRequest,
    db: Session = Depends(get_db),
) -> GeoAssetFeatureCollection:
    return GeoAssetService(db).bulk_create(payload)


@router.get(
    "/{asset_id}",
    response_model=GeoAssetFeature,
    summary="Get a spatial asset",
)
def get_geo_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
) -> GeoAssetFeature:
    return GeoAssetService(db).get(asset_id)


@router.patch(
    "/{asset_id}",
    response_model=GeoAssetFeature,
    summary="Update a spatial asset",
)
def update_geo_asset(
    asset_id: UUID,
    payload: GeoAssetUpdate,
    db: Session = Depends(get_db),
) -> GeoAssetFeature:
    return GeoAssetService(db).update(asset_id, payload)


@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a spatial asset",
)
def delete_geo_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    GeoAssetService(db).delete(asset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
