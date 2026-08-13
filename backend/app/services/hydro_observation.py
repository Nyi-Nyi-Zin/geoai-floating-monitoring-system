import math
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.hydro_observation import HydroObservation
from app.schemas.geo_asset import PaginationMeta
from app.schemas.hydro_observation import (
    HydroObservationCollection,
    HydroObservationCreate,
    HydroObservationFeature,
    HydroObservationProperties,
    HydroObservationUpdate,
)


def _not_found(observation_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "hydro_observation_not_found",
            "message": f"Hydrology observation '{observation_id}' was not found.",
        },
    )


def _to_feature(observation: HydroObservation) -> HydroObservationFeature:
    return HydroObservationFeature(
        id=observation.id,
        geometry=to_shape(observation.geometry).__geo_interface__,
        properties=HydroObservationProperties(
            station_id=observation.station_id,
            station_name=observation.station_name,
            observed_at=observation.observed_at,
            rainfall_mm=observation.rainfall_mm,
            water_level_m=observation.water_level_m,
            discharge_m3s=observation.discharge_m3s,
            soil_moisture_percent=observation.soil_moisture_percent,
            battery_percent=observation.battery_percent,
            source=observation.source,
            quality_status=observation.quality_status,
            notes=observation.notes,
            created_at=observation.created_at,
            updated_at=observation.updated_at,
        ),
    )


class HydroObservationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: HydroObservationCreate) -> HydroObservationFeature:
        observation = HydroObservation(
            **payload.model_dump(exclude={"geometry"}),
            geometry=from_shape(shape(payload.geometry), srid=4326),
        )
        self.db.add(observation)
        self.db.commit()
        self.db.refresh(observation)
        return _to_feature(observation)

    def get(self, observation_id: UUID) -> HydroObservationFeature:
        observation = self.db.get(HydroObservation, observation_id)
        if observation is None:
            raise _not_found(observation_id)
        return _to_feature(observation)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        station_id: str | None,
        quality_status: str | None,
        observed_from: datetime | None,
        observed_to: datetime | None,
    ) -> HydroObservationCollection:
        query = select(HydroObservation)
        count_query = select(func.count()).select_from(HydroObservation)
        filters = []
        if station_id:
            filters.append(HydroObservation.station_id == station_id)
        if quality_status:
            filters.append(HydroObservation.quality_status == quality_status)
        if observed_from:
            filters.append(HydroObservation.observed_at >= observed_from)
        if observed_to:
            filters.append(HydroObservation.observed_at <= observed_to)
        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)

        total = self.db.scalar(count_query) or 0
        rows = self.db.scalars(
            query.order_by(HydroObservation.observed_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return HydroObservationCollection(
            features=[_to_feature(row) for row in rows],
            meta=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                pages=math.ceil(total / page_size) if total else 0,
            ),
        )

    def latest(self, limit: int) -> HydroObservationCollection:
        latest_ids = (
            select(HydroObservation.id)
            .distinct(HydroObservation.station_id)
            .order_by(
                HydroObservation.station_id,
                HydroObservation.observed_at.desc(),
            )
            .subquery()
        )
        rows = self.db.scalars(
            select(HydroObservation)
            .join(latest_ids, HydroObservation.id == latest_ids.c.id)
            .order_by(HydroObservation.observed_at.desc())
            .limit(limit)
        ).all()
        total = len(rows)
        return HydroObservationCollection(
            features=[_to_feature(row) for row in rows],
            meta=PaginationMeta(
                page=1,
                page_size=limit,
                total=total,
                pages=1 if total else 0,
            ),
        )

    def update(
        self,
        observation_id: UUID,
        payload: HydroObservationUpdate,
    ) -> HydroObservationFeature:
        observation = self.db.get(HydroObservation, observation_id)
        if observation is None:
            raise _not_found(observation_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(observation, field, value)
        self.db.commit()
        self.db.refresh(observation)
        return _to_feature(observation)
