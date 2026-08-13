import math
from collections import Counter
from uuid import UUID

from fastapi import HTTPException, status
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.data_layer import DataLayer
from app.schemas.data_layer import (
    DataLayerCollection,
    DataLayerCreate,
    DataLayerFeature,
    DataLayerProperties,
    DataLayerUpdate,
)
from app.schemas.geo_asset import PaginationMeta


def _not_found(layer_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "data_layer_not_found",
            "message": f"Data layer '{layer_id}' was not found.",
        },
    )


def _to_feature(layer: DataLayer) -> DataLayerFeature:
    return DataLayerFeature(
        id=layer.id,
        geometry=(
            to_shape(layer.coverage).__geo_interface__
            if layer.coverage is not None
            else None
        ),
        properties=DataLayerProperties(
            layer_key=layer.layer_key,
            name=layer.name,
            category=layer.category,
            data_kind=layer.data_kind,
            provider=layer.provider,
            source_url=layer.source_url,
            license_name=layer.license_name,
            license_url=layer.license_url,
            attribution=layer.attribution,
            usage_constraints=layer.usage_constraints,
            spatial_resolution_m=layer.spatial_resolution_m,
            temporal_coverage_start=layer.temporal_coverage_start,
            temporal_coverage_end=layer.temporal_coverage_end,
            update_frequency=layer.update_frequency,
            quality_status=layer.quality_status,
            quality_notes=layer.quality_notes,
            provenance=layer.provenance,
            is_active=layer.is_active,
            created_at=layer.created_at,
            updated_at=layer.updated_at,
        ),
    )


class DataLayerService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: DataLayerCreate) -> DataLayerFeature:
        if self.db.scalar(
            select(DataLayer.id).where(DataLayer.layer_key == payload.layer_key)
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "data_layer_key_exists",
                    "message": f"Data layer key '{payload.layer_key}' already exists.",
                },
            )
        layer = self._from_payload(payload)
        self.db.add(layer)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "data_layer_key_exists",
                    "message": f"Data layer key '{payload.layer_key}' already exists.",
                },
            ) from None
        self.db.refresh(layer)
        return _to_feature(layer)

    def upsert(self, payload: DataLayerCreate) -> DataLayerFeature:
        layer = self.db.scalar(
            select(DataLayer).where(DataLayer.layer_key == payload.layer_key)
        )
        if layer is None:
            layer = DataLayer(layer_key=payload.layer_key)
            self.db.add(layer)
        self._apply_payload(layer, payload)
        self.db.commit()
        self.db.refresh(layer)
        return _to_feature(layer)

    def get(self, layer_id: UUID) -> DataLayerFeature:
        layer = self.db.get(DataLayer, layer_id)
        if layer is None:
            raise _not_found(layer_id)
        return _to_feature(layer)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        category: str | None,
        quality_status: str | None,
        is_active: bool | None,
    ) -> DataLayerCollection:
        filters = []
        if category:
            filters.append(DataLayer.category == category)
        if quality_status:
            filters.append(DataLayer.quality_status == quality_status)
        if is_active is not None:
            filters.append(DataLayer.is_active == is_active)

        total = (
            self.db.scalar(
                select(func.count()).select_from(DataLayer).where(*filters)
            )
            or 0
        )
        rows = self.db.scalars(
            select(DataLayer)
            .where(*filters)
            .order_by(DataLayer.category, DataLayer.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        quality_counts = Counter(
            self.db.scalars(
                select(DataLayer.quality_status).where(*filters)
            ).all()
        )
        return DataLayerCollection(
            features=[_to_feature(layer) for layer in rows],
            meta=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                pages=math.ceil(total / page_size) if total else 0,
            ),
            quality_counts={
                current_status: quality_counts[current_status]
                for current_status in (
                    "verified",
                    "limited",
                    "unreviewed",
                    "deprecated",
                )
            },
        )

    def update(
        self,
        layer_id: UUID,
        payload: DataLayerUpdate,
    ) -> DataLayerFeature:
        layer = self.db.get(DataLayer, layer_id)
        if layer is None:
            raise _not_found(layer_id)
        changes = payload.model_dump(exclude_unset=True)
        if "coverage" in changes:
            changes["coverage"] = (
                from_shape(shape(changes["coverage"]), srid=4326)
                if changes["coverage"] is not None
                else None
            )
        for field, value in changes.items():
            setattr(layer, field, value)
        if (
            layer.temporal_coverage_start is not None
            and layer.temporal_coverage_end is not None
            and layer.temporal_coverage_start > layer.temporal_coverage_end
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "invalid_temporal_coverage",
                    "message": (
                        "temporal_coverage_start must not be after "
                        "temporal_coverage_end"
                    ),
                },
            )
        self.db.commit()
        self.db.refresh(layer)
        return _to_feature(layer)

    @staticmethod
    def _from_payload(payload: DataLayerCreate) -> DataLayer:
        layer = DataLayer(layer_key=payload.layer_key)
        DataLayerService._apply_payload(layer, payload)
        return layer

    @staticmethod
    def _apply_payload(layer: DataLayer, payload: DataLayerCreate) -> None:
        values = payload.model_dump(exclude={"coverage"})
        for field, value in values.items():
            setattr(layer, field, value)
        layer.coverage = (
            from_shape(shape(payload.coverage), srid=4326)
            if payload.coverage is not None
            else None
        )
