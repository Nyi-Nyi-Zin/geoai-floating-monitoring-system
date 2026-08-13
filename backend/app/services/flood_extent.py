import math
from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from geoalchemy2.shape import from_shape, to_shape
from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon, shape
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.flood_extent import FloodExtent
from app.schemas.flood_extent import (
    FloodExtentCollection,
    FloodExtentCreate,
    FloodExtentFeature,
    FloodExtentProperties,
    FloodExtentSummary,
)
from app.schemas.geo_asset import PaginationMeta

GEOD = Geod(ellps="WGS84")


def polygon_to_multipolygon(geometry: Polygon | MultiPolygon) -> MultiPolygon:
    return geometry if isinstance(geometry, MultiPolygon) else MultiPolygon([geometry])


def geodesic_area_km2(geometry: Polygon | MultiPolygon) -> float:
    area_m2, _ = GEOD.geometry_area_perimeter(geometry)
    return abs(area_m2) / 1_000_000


def _to_feature(extent: FloodExtent) -> FloodExtentFeature:
    return FloodExtentFeature(
        id=extent.id,
        geometry=to_shape(extent.geometry).__geo_interface__,
        properties=FloodExtentProperties(
            source_key=extent.source_key,
            event_name=extent.event_name,
            event_id=extent.event_id,
            observed_date=extent.observed_date,
            observed_start_date=extent.observed_start_date,
            observed_end_date=extent.observed_end_date,
            sensor=extent.sensor,
            classification=extent.classification,
            confidence=extent.confidence,
            field_validated=extent.field_validated,
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


class FloodExtentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: FloodExtentCreate) -> FloodExtentFeature:
        if self.db.scalar(
            select(FloodExtent.id).where(FloodExtent.source_key == payload.source_key)
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "flood_extent_source_key_exists",
                    "message": f"Flood extent key '{payload.source_key}' already exists.",
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
                    "code": "flood_extent_source_key_exists",
                    "message": f"Flood extent key '{payload.source_key}' already exists.",
                },
            ) from None
        self.db.refresh(extent)
        return _to_feature(extent)

    def upsert(self, payload: FloodExtentCreate) -> FloodExtentFeature:
        extent = self.db.scalar(
            select(FloodExtent).where(FloodExtent.source_key == payload.source_key)
        )
        if extent is None:
            extent = FloodExtent(source_key=payload.source_key)
            self.db.add(extent)
        self._apply_payload(extent, payload)
        self.db.commit()
        self.db.refresh(extent)
        return _to_feature(extent)

    def get(self, extent_id: UUID) -> FloodExtentFeature:
        extent = self.db.get(FloodExtent, extent_id)
        if extent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "flood_extent_not_found",
                    "message": f"Flood extent '{extent_id}' was not found.",
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
        classification: str | None,
    ) -> FloodExtentCollection:
        filters = []
        if start_date is not None:
            filters.append(
                func.coalesce(FloodExtent.observed_end_date, FloodExtent.observed_date)
                >= start_date
            )
        if end_date is not None:
            filters.append(
                func.coalesce(FloodExtent.observed_start_date, FloodExtent.observed_date)
                <= end_date
            )
        if classification is not None:
            filters.append(FloodExtent.classification == classification)

        total = self.db.scalar(
            select(func.count()).select_from(FloodExtent).where(*filters)
        ) or 0
        rows = self.db.scalars(
            select(FloodExtent)
            .where(*filters)
            .order_by(FloodExtent.observed_date.desc(), FloodExtent.event_name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        summary_row = self.db.execute(
            select(
                func.count(
                    func.distinct(
                        func.coalesce(FloodExtent.event_id, FloodExtent.event_name)
                    )
                ),
                func.coalesce(func.sum(FloodExtent.area_km2), 0.0),
                func.min(FloodExtent.observed_date),
                func.max(FloodExtent.observed_date),
                func.count().filter(FloodExtent.field_validated.is_(True)),
            ).where(*filters)
        ).one()
        return FloodExtentCollection(
            features=[_to_feature(row) for row in rows],
            meta=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                pages=math.ceil(total / page_size) if total else 0,
            ),
            summary=FloodExtentSummary(
                total_features=total,
                event_count=summary_row[0] or 0,
                total_area_km2=round(float(summary_row[1] or 0), 3),
                observed_from=summary_row[2],
                observed_to=summary_row[3],
                field_validated_features=summary_row[4] or 0,
            ),
            limitations=[
                "Satellite water classifications can miss inundation beneath dense vegetation or in built-up areas.",
                "Permanent water must be excluded before a polygon is used as a flood label.",
                "Unvalidated extents are training evidence, not operational warnings or guaranteed ground truth.",
            ],
        )

    @staticmethod
    def _from_payload(payload: FloodExtentCreate) -> FloodExtent:
        extent = FloodExtent(source_key=payload.source_key)
        FloodExtentService._apply_payload(extent, payload)
        return extent

    @staticmethod
    def _apply_payload(extent: FloodExtent, payload: FloodExtentCreate) -> None:
        geometry = polygon_to_multipolygon(shape(payload.geometry))
        extent.source_key = payload.source_key
        extent.event_name = payload.event_name
        extent.event_id = payload.event_id
        extent.observed_date = payload.observed_date
        extent.observed_start_date = payload.observed_start_date
        extent.observed_end_date = payload.observed_end_date
        extent.sensor = payload.sensor
        extent.classification = payload.classification
        extent.confidence = payload.confidence
        extent.field_validated = payload.field_validated
        extent.source_name = payload.source_name
        extent.source_url = payload.source_url
        extent.license_name = payload.license_name
        extent.notes = payload.notes
        extent.geometry = from_shape(geometry, srid=4326)
        extent.area_km2 = geodesic_area_km2(geometry)
        extent.properties = payload.properties
