from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.concurrency import run_in_threadpool
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.hydro_observation import (
    HydroObservationCollection,
    HydroObservationFeature,
)
from app.schemas.sensor_station import (
    SensorReadingCreate,
    SensorStationCollection,
    SensorStationCreate,
    SensorStationFeature,
    StationStatus,
)
from app.services.hydro_observation import HydroObservationService
from app.services.sensor_station import SensorStationService
from app.services.live_updates import live_updates

stations_router = APIRouter(prefix="/stations", tags=["sensor-stations"])
readings_router = APIRouter(prefix="/readings", tags=["sensor-readings"])

Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=500)]


@stations_router.post(
    "",
    response_model=SensorStationFeature,
    status_code=status.HTTP_201_CREATED,
    summary="Register a physical flood-monitoring station",
)
def create_sensor_station(
    payload: SensorStationCreate,
    db: Session = Depends(get_db),
) -> SensorStationFeature:
    return SensorStationService(db).create(payload)


@stations_router.get(
    "",
    response_model=SensorStationCollection,
    summary="List registered sensor stations",
)
def list_sensor_stations(
    page: Page = 1,
    page_size: PageSize = 100,
    station_status: StationStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> SensorStationCollection:
    return SensorStationService(db).list(
        page=page,
        page_size=page_size,
        station_status=station_status,
    )


@stations_router.get(
    "/{station_id}",
    response_model=SensorStationFeature,
    summary="Get a sensor station",
)
def get_sensor_station(
    station_id: str,
    db: Session = Depends(get_db),
) -> SensorStationFeature:
    return SensorStationService(db).get(station_id)


@stations_router.get(
    "/{station_id}/readings",
    response_model=HydroObservationCollection,
    summary="List time-ordered readings for one station",
)
def list_station_readings(
    station_id: str,
    page: Page = 1,
    page_size: PageSize = 100,
    db: Session = Depends(get_db),
) -> HydroObservationCollection:
    SensorStationService(db).get(station_id)
    return HydroObservationService(db).list(
        page=page,
        page_size=page_size,
        station_id=station_id,
        quality_status=None,
        observed_from=None,
        observed_to=None,
    )


@readings_router.post(
    "",
    response_model=HydroObservationFeature,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest an idempotent ESP32 sensor reading",
)
async def ingest_sensor_reading(
    payload: SensorReadingCreate,
    db: Session = Depends(get_db),
) -> HydroObservationFeature:
    result = await run_in_threadpool(
        SensorStationService(db).ingest_reading,
        payload,
    )
    if result.created:
        await live_updates.broadcast(
            {
                "type": "sensor_reading",
                "data": jsonable_encoder(result.feature),
            }
        )
    return result.feature
