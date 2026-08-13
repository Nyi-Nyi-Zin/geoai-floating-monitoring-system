from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rainfall_history import RainfallHistory
from app.schemas.rainfall_history import (
    RainfallHistoryDay,
    RainfallHistoryResponse,
    RainfallHistorySummary,
)

SOURCE_KEY = "copernicus:era5:maubin:daily-v1"
SOURCE_NAME = "Copernicus ERA5 reanalysis via Open-Meteo"
SOURCE_RESOLUTION_M = 25_000
ATTRIBUTION = "ERA5 data by ECMWF/Copernicus; API delivery by Open-Meteo"


class RainfallHistoryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_history(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        limit: int,
    ) -> RainfallHistoryResponse:
        statement = select(RainfallHistory).where(
            RainfallHistory.source_key == SOURCE_KEY
        )
        if start_date is not None:
            statement = statement.where(
                RainfallHistory.observed_date >= start_date
            )
        if end_date is not None:
            statement = statement.where(
                RainfallHistory.observed_date <= end_date
            )
        rows = list(
            self.db.scalars(
                statement.order_by(
                    RainfallHistory.observed_date.desc()
                ).limit(limit)
            )
        )
        rows.reverse()

        daily = [
            RainfallHistoryDay(
                date=row.observed_date,
                mean_precipitation_mm=round(
                    row.mean_precipitation_mm,
                    2,
                ),
                max_precipitation_mm=round(
                    row.max_precipitation_mm,
                    2,
                ),
                p90_precipitation_mm=round(
                    row.p90_precipitation_mm,
                    2,
                ),
                accumulation_3d_mm=round(row.accumulation_3d_mm, 2),
                accumulation_7d_mm=round(row.accumulation_7d_mm, 2),
                accumulation_30d_mm=round(row.accumulation_30d_mm, 2),
            )
            for row in rows
        ]
        peak_daily = max(
            rows,
            key=lambda row: row.mean_precipitation_mm,
            default=None,
        )
        peak_7d = max(
            rows,
            key=lambda row: row.accumulation_7d_mm,
            default=None,
        )
        summary = RainfallHistorySummary(
            start_date=rows[0].observed_date if rows else None,
            end_date=rows[-1].observed_date if rows else None,
            days=len(rows),
            wet_days=sum(
                row.mean_precipitation_mm >= 1.0 for row in rows
            ),
            total_mean_precipitation_mm=round(
                sum(row.mean_precipitation_mm for row in rows),
                2,
            ),
            peak_daily_mean_mm=round(
                peak_daily.mean_precipitation_mm,
                2,
            )
            if peak_daily
            else 0.0,
            peak_daily_mean_date=(
                peak_daily.observed_date if peak_daily else None
            ),
            peak_7d_mm=round(peak_7d.accumulation_7d_mm, 2)
            if peak_7d
            else 0.0,
            peak_7d_end_date=peak_7d.observed_date if peak_7d else None,
        )
        return RainfallHistoryResponse(
            status="available" if rows else "unavailable",
            source_key=SOURCE_KEY,
            source_name=SOURCE_NAME,
            model="ERA5",
            source_resolution_m=SOURCE_RESOLUTION_M,
            grid_cell_count=(
                max((row.grid_cell_count for row in rows), default=0)
            ),
            daily=daily,
            summary=summary,
            attribution=ATTRIBUTION,
            limitations=[
                "ERA5 is model reanalysis, not a Maubin rain-gauge record.",
                "The source grid is about 25 km; values must not be interpreted "
                "as independent 500 m terrain-cell measurements.",
                "Area-weighted township rainfall is calibration input, not a "
                "flood probability or warning by itself.",
            ],
        )
