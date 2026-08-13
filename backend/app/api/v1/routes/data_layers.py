from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.data_layer import (
    DataLayerCollection,
    DataLayerCreate,
    DataLayerFeature,
    DataLayerUpdate,
    DataQualityStatus,
)
from app.services.data_layer import DataLayerService

router = APIRouter(prefix="/data-layers", tags=["data-layers"])

Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=500)]


@router.post(
    "",
    response_model=DataLayerFeature,
    status_code=status.HTTP_201_CREATED,
    summary="Register an auditable spatial or environmental data layer",
)
def create_data_layer(
    payload: DataLayerCreate,
    db: Session = Depends(get_db),
) -> DataLayerFeature:
    return DataLayerService(db).create(payload)


@router.get(
    "",
    response_model=DataLayerCollection,
    summary="List data layers with provenance and quality status",
)
def list_data_layers(
    page: Page = 1,
    page_size: PageSize = 100,
    category: str | None = Query(default=None, min_length=1, max_length=100),
    quality_status: DataQualityStatus | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
) -> DataLayerCollection:
    return DataLayerService(db).list(
        page=page,
        page_size=page_size,
        category=category,
        quality_status=quality_status,
        is_active=is_active,
    )


@router.get(
    "/{layer_id}",
    response_model=DataLayerFeature,
    summary="Get one data layer's provenance record",
)
def get_data_layer(
    layer_id: UUID,
    db: Session = Depends(get_db),
) -> DataLayerFeature:
    return DataLayerService(db).get(layer_id)


@router.patch(
    "/{layer_id}",
    response_model=DataLayerFeature,
    summary="Update quality, provenance, or lifecycle metadata",
)
def update_data_layer(
    layer_id: UUID,
    payload: DataLayerUpdate,
    db: Session = Depends(get_db),
) -> DataLayerFeature:
    return DataLayerService(db).update(layer_id, payload)
