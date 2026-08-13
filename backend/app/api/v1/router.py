from fastapi import APIRouter

from app.api.v1.routes import (
    alerts,
    data_layers,
    flood_extents,
    flood_intelligence,
    flood_ml,
    flood_screening,
    forecast,
    geo_assets,
    health,
    hydro_observations,
    live,
    mqtt,
    observed_water_extents,
    sensor_stations,
    weather,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(alerts.router)
api_router.include_router(data_layers.router)
api_router.include_router(flood_extents.router)
api_router.include_router(flood_ml.router)
api_router.include_router(flood_intelligence.router)
api_router.include_router(flood_screening.router)
api_router.include_router(forecast.router)
api_router.include_router(geo_assets.router)
api_router.include_router(hydro_observations.router)
api_router.include_router(live.router)
api_router.include_router(observed_water_extents.router)
api_router.include_router(mqtt.router)
api_router.include_router(sensor_stations.stations_router)
api_router.include_router(sensor_stations.readings_router)
api_router.include_router(weather.router)

