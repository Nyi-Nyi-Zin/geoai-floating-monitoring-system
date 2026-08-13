import math
from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.observed_water_extent import ObservedWaterExtent
from app.schemas.geo_asset import PaginationMeta
from app.schemas.observed_water_extent import (
    ObservedWaterExtentCollection,
    ObservedWaterExtentCreate,
    ObservedWaterExtentFeature,
    ObservedWaterExtentProperties,
    ObservedWaterExtentSummary,
)
from app.services.flood_extent import geodesic_area_km2, polygon_to_multipolygon

OBSERVED_WATER_LIMITATIONS = [
    "Observed water extent shows satellite-detected open water on the observation date, not mapped river channels.",
    "Seasonal dry channels may show no water while OSM river lines remain visible.",
    "This is a dynamic water-surface snapshot, not a flood event label or operational warning.",
    "Do not use this layer to replace OSM river/canal networks or distance_to_waterway model features.",
]


def _to_feature(extent: ObservedWaterExtent) -> ObservedWaterExtentFeature:
    return ObservedWaterExtentFeature(
        id=extent.id,
        geometry=to_shape(extent.geometry).__geo_interface__,
        properties=ObservedWaterExtentProperties(
            source_key=extent.source_key,
            name=extent.name,
            observed_at=extent.observed_at,
            source=extent.source,
            method=extent.method,
            confidence_score=extent.confidence_score,
            event_id=extent.event_id,
            source_name=extent.source_name,
            source_url=extent.source_url,
            license_name=extent.license_name,
            notes=extent.notes,
            area_km2=round(extent.area_km2, 3),
            metadata=extent.properties,
            created_at=extent.created_at,
            updated_at=extent.updated_at,
        ),
    )


class ObservedWaterExtentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: ObservedWaterExtentCreate) -> ObservedWaterExtentFeature:
        if self.db.scalar(
            select(ObservedWaterExtent.id).where(
                ObservedWaterExtent.source_key == payload.source_key
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "observed_water_extent_source_key_exists",
                    "message": (
                        f"Observed water extent key '{payload.source_key}' already exists."
                    ),
                },
            )
        extent = self._from_payload(payload)
        self.db.add(extent)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "observed_water_extent_source_key_exists",
                    "message": (
                        f"Observed water extent key '{payload.source_key}' already exists."
                    ),
                },
            ) from None
        self.db.refresh(extent)
        return _to_feature(extent)

    def upsert(self, payload: ObservedWaterExtentCreate) -> ObservedWaterExtentFeature:
        extent = self.db.scalar(
            select(ObservedWaterExtent).where(
                ObservedWaterExtent.source_key == payload.source_key
            )
        )
        if extent is None:
            extent = ObservedWaterExtent(source_key=payload.source_key)
            self.db.add(extent)
        self._apply_payload(extent, payload)
        self.db.commit()
        self.db.refresh(extent)
        return _to_feature(extent)

    def get(self, extent_id: UUID) -> ObservedWaterExtentFeature:
        extent = self.db.get(ObservedWaterExtent, extent_id)
        if extent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "observed_water_extent_not_found",
                    "message": f"Observed water extent '{extent_id}' was not found.",
                },
            )
        return _to_feature(extent)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        start_date: date | None,
        end_date: date | None,
        source: str | None,
    ) -> ObservedWaterExtentCollection:
        filters = []
        if start_date is not None:
            filters.append(ObservedWaterExtent.observed_at >= start_date)
        if end_date is not None:
            filters.append(ObservedWaterExtent.observed_at <= end_date)
        if source is not None:
            filters.append(ObservedWaterExtent.source == source)

        total = self.db.scalar(
            select(func.count()).select_from(ObservedWaterExtent).where(*filters)
        ) or 0
        rows = self.db.scalars(
            select(ObservedWaterExtent)
            .where(*filters)
            .order_by(
                ObservedWaterExtent.observed_at.desc(),
                ObservedWaterExtent.name,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        summary_row = self.db.execute(
            select(
                func.count(
                    func.distinct(
                        func.coalesce(
                            ObservedWaterExtent.event_id,
                            ObservedWaterExtent.source_key,
                        )
                    )
                ),
                func.coalesce(func.sum(ObservedWaterExtent.area_km2), 0.0),
                func.min(ObservedWaterExtent.observed_at),
                func.max(ObservedWaterExtent.observed_at),
            ).where(*filters)
        ).one()

        latest = self.db.scalar(
            select(ObservedWaterExtent)
            .where(*filters)
            .order_by(
                ObservedWaterExtent.observed_at.desc(),
                ObservedWaterExtent.updated_at.desc(),
            )
            .limit(1)
        )

        return ObservedWaterExtentCollection(
            features=[_to_feature(row) for row in rows],
            meta=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                pages=math.ceil(total / page_size) if total else 0,
            ),
            summary=ObservedWaterExtentSummary(
                total_features=total,
                observation_count=summary_row[0] or 0,
                total_area_km2=round(float(summary_row[1] or 0), 3),
                observed_from=summary_row[2],
                observed_to=summary_row[3],
                latest_observed_at=latest.observed_at if latest else None,
                latest_source=latest.source if latest else None,
                latest_method=latest.method if latest else None,
            ),
            limitations=OBSERVED_WATER_LIMITATIONS,
        )

    @staticmethod
    def _from_payload(payload: ObservedWaterExtentCreate) -> ObservedWaterExtent:
        extent = ObservedWaterExtent(source_key=payload.source_key)
        ObservedWaterExtentService._apply_payload(extent, payload)
        return extent

    @staticmethod
    def _apply_payload(
        extent: ObservedWaterExtent, payload: ObservedWaterExtentCreate
    ) -> None:
        geometry = polygon_to_multipolygon(shape(payload.geometry))
        extent.source_key = payload.source_key
        extent.name = payload.name
        extent.observed_at = payload.observed_at
        extent.source = payload.source
        extent.method = payload.method
        extent.confidence_score = payload.confidence_score
        extent.event_id = payload.event_id
        extent.source_name = payload.source_name
        extent.source_url = payload.source_url
        extent.license_name = payload.license_name
        extent.notes = payload.notes
        extent.geometry = from_shape(geometry, srid=4326)
        extent.area_km2 = geodesic_area_km2(geometry)
        extent.properties = payload.properties
