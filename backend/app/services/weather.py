from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.weather import (
    ForecastLocation,
    RainfallForecastDay,
    RainfallForecastHour,
    RainfallForecastResponse,
)

_cache_lock = Lock()
_cache: dict[int, tuple[datetime, RainfallForecastResponse]] = {}


def parse_open_meteo_response(
    payload: dict[str, Any],
    *,
    fetched_at: datetime,
    cached: bool,
) -> RainfallForecastResponse:
    hourly = payload.get("hourly") or {}
    daily = payload.get("daily") or {}
    hourly_times = hourly.get("time") or []
    hourly_precipitation = hourly.get("precipitation") or []
    hourly_probability = hourly.get("precipitation_probability") or []
    daily_times = daily.get("time") or []
    daily_precipitation = daily.get("precipitation_sum") or []
    daily_probability = daily.get("precipitation_probability_max") or []

    if len(hourly_times) != len(hourly_precipitation):
        raise ValueError("Open-Meteo returned inconsistent hourly forecast arrays")
    if len(daily_times) != len(daily_precipitation):
        raise ValueError("Open-Meteo returned inconsistent daily forecast arrays")

    hourly_rows = [
        RainfallForecastHour(
            time=time,
            precipitation_mm=float(precipitation or 0),
            probability_percent=(
                int(hourly_probability[index])
                if index < len(hourly_probability)
                and hourly_probability[index] is not None
                else None
            ),
        )
        for index, (time, precipitation) in enumerate(
            zip(hourly_times, hourly_precipitation, strict=True)
        )
    ]
    daily_rows = [
        RainfallForecastDay(
            date=forecast_date,
            precipitation_sum_mm=float(precipitation or 0),
            probability_max_percent=(
                int(daily_probability[index])
                if index < len(daily_probability)
                and daily_probability[index] is not None
                else None
            ),
        )
        for index, (forecast_date, precipitation) in enumerate(
            zip(daily_times, daily_precipitation, strict=True)
        )
    ]
    return RainfallForecastResponse(
        location=ForecastLocation(
            name="Maubin Township",
            latitude=float(payload["latitude"]),
            longitude=float(payload["longitude"]),
            timezone=str(payload.get("timezone") or "Asia/Yangon"),
        ),
        fetched_at=fetched_at,
        source="Open-Meteo weather forecast",
        attribution_url="https://open-meteo.com/",
        cached=cached,
        hourly=hourly_rows,
        daily=daily_rows,
    )


def get_rainfall_forecast(
    forecast_days: int,
    *,
    client: httpx.Client | None = None,
) -> RainfallForecastResponse:
    if not settings.weather_provider_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "weather_provider_disabled",
                "message": "The weather forecast provider is disabled.",
            },
        )

    now = datetime.now(UTC)
    with _cache_lock:
        cached_entry = _cache.get(forecast_days)
        if cached_entry and now - cached_entry[0] < timedelta(
            seconds=settings.weather_cache_ttl_seconds
        ):
            return cached_entry[1].model_copy(update={"cached": True})

    request_client = client or httpx.Client(timeout=8.0)
    should_close = client is None
    try:
        response = request_client.get(
            settings.open_meteo_base_url,
            params={
                "latitude": settings.maubin_forecast_latitude,
                "longitude": settings.maubin_forecast_longitude,
                "hourly": "precipitation,precipitation_probability",
                "daily": "precipitation_sum,precipitation_probability_max",
                "timezone": "Asia/Yangon",
                "forecast_days": forecast_days,
            },
        )
        response.raise_for_status()
        forecast = parse_open_meteo_response(
            response.json(),
            fetched_at=now,
            cached=False,
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "weather_provider_unavailable",
                "message": "The rainfall forecast could not be retrieved.",
                "details": str(exc),
            },
        ) from exc
    finally:
        if should_close:
            request_client.close()

    with _cache_lock:
        _cache[forecast_days] = (now, forecast)
    return forecast
