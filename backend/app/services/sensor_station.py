import hashlib
import math
from dataclasses import dataclass

from fastapi import HTTPException, status
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.hydro_observation import HydroObservation
from app.models.sensor_station import SensorStation
from app.schemas.geo_asset import PaginationMeta
from app.schemas.hydro_observation import HydroObservationFeature
from app.schemas.sensor_station import (
    SensorReadingCreate,
    SensorStationCollection,
    SensorStationCreate,
    SensorStationFeature,
    SensorStationProperties,
)
from app.services.hydro_observation import _to_feature as observation_to_feature
from app.services.risk_rules import classify_water_level


@dataclass(frozen=True)
class SensorReadingIngestResult:
    feature: HydroObservationFeature
    created: bool


def _station_not_found(station_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "sensor_station_not_found",
            "message": f"Sensor station '{station_id}' was not found.",
        },
    )


def _to_feature(station: SensorStation) -> SensorStationFeature:
    return SensorStationFeature(
        id=station.station_id,
        geometry=to_shape(station.geometry).__geo_interface__,
        properties=SensorStationProperties(
            station_id=station.station_id,
            name=station.name,
            river_name=station.river_name,
            description=station.description,
            status=station.status,
            warning_level_cm=station.warning_level_cm,
            danger_level_cm=station.danger_level_cm,
            critical_level_cm=station.critical_level_cm,
            metadata=station.metadata_json,
            installed_at=station.installed_at,
            last_seen_at=station.last_seen_at,
            created_at=station.created_at,
            updated_at=station.updated_at,
        ),
    )


class SensorStationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: SensorStationCreate) -> SensorStationFeature:
        if self.db.get(SensorStation, payload.station_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "sensor_station_exists",
                    "message": f"Sensor station '{payload.station_id}' already exists.",
                },
            )
        values = payload.model_dump(exclude={"geometry", "metadata"})
        station = SensorStation(
            **values,
            geometry=from_shape(shape(payload.geometry), srid=4326),
            metadata_json=payload.metadata,
        )
        self.db.add(station)
        self.db.commit()
        self.db.refresh(station)
        return _to_feature(station)

    def get(self, station_id: str) -> SensorStationFeature:
        station = self.db.get(SensorStation, station_id)
        if station is None:
            raise _station_not_found(station_id)
        return _to_feature(station)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        station_status: str | None,
    ) -> SensorStationCollection:
        query = select(SensorStation)
        count_query = select(func.count()).select_from(SensorStation)
        if station_status:
            query = query.where(SensorStation.status == station_status)
            count_query = count_query.where(SensorStation.status == station_status)
        total = self.db.scalar(count_query) or 0
        rows = self.db.scalars(
            query.order_by(SensorStation.station_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return SensorStationCollection(
            features=[_to_feature(row) for row in rows],
            meta=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                pages=math.ceil(total / page_size) if total else 0,
            ),
        )

    def ingest_reading(
        self,
        payload: SensorReadingCreate,
    ) -> SensorReadingIngestResult:
        station = self.db.get(SensorStation, payload.station_id)
        if station is None:
            raise _station_not_found(payload.station_id)

        source = payload.source.strip()
        ingestion_key = hashlib.sha256(
            (
                f"{payload.station_id}|{payload.timestamp.isoformat()}|"
                f"{source}"
            ).encode("utf-8")
        ).hexdigest()
        existing = self.db.scalar(
            select(HydroObservation).where(
                HydroObservation.ingestion_key == ingestion_key
            )
        )
        if existing is not None:
            return SensorReadingIngestResult(
                feature=observation_to_feature(existing),
                created=False,
            )

        observation = HydroObservation(
            station_id=station.station_id,
            station_name=station.name,
            observed_at=payload.timestamp,
            rainfall_mm=payload.rainfall_mm,
            water_level_m=(
                payload.water_level_cm / 100
                if payload.water_level_cm is not None
                else None
            ),
            discharge_m3s=None,
            soil_moisture_percent=payload.soil_moisture_percent,
            battery_percent=payload.battery_percent,
            ingestion_key=ingestion_key,
            source=source,
            quality_status="unverified",
            notes=None,
            geometry=station.geometry,
        )
        self.db.add(observation)
        if station.last_seen_at is None or payload.timestamp > station.last_seen_at:
            station.last_seen_at = payload.timestamp
        if station.status == "offline":
            station.status = "active"
        assessment = classify_water_level(
            payload.water_level_cm,
            warning_level_cm=station.warning_level_cm,
            danger_level_cm=station.danger_level_cm,
            critical_level_cm=station.critical_level_cm,
        )
        if assessment.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}:
            self.db.flush()
            self.db.add(
                Alert(
                    station_id=station.station_id,
                    observation_id=observation.id,
                    risk_level=assessment.risk_level,
                    water_level_cm=payload.water_level_cm,
                    threshold_cm=assessment.crossed_threshold_cm,
                    message=(
                        f"{station.name} reported {payload.water_level_cm:.1f} cm. "
                        f"{assessment.explanation}"
                    ),
                )
            )
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            duplicate = self.db.scalar(
                select(HydroObservation).where(
                    HydroObservation.ingestion_key == ingestion_key
                )
            )
            if duplicate is None:
                raise
            return SensorReadingIngestResult(
                feature=observation_to_feature(duplicate),
                created=False,
            )
        self.db.refresh(observation)
        return SensorReadingIngestResult(
            feature=observation_to_feature(observation),
            created=True,
        )
