from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SensorStation(Base):
    __tablename__ = "sensor_stations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'offline', 'maintenance')",
            name="ck_sensor_stations_status",
        ),
        CheckConstraint(
            "warning_level_cm IS NULL OR warning_level_cm >= 0",
            name="ck_sensor_stations_warning_nonnegative",
        ),
        CheckConstraint(
            "danger_level_cm IS NULL OR danger_level_cm >= 0",
            name="ck_sensor_stations_danger_nonnegative",
        ),
        CheckConstraint(
            "critical_level_cm IS NULL OR critical_level_cm >= 0",
            name="ck_sensor_stations_critical_nonnegative",
        ),
        CheckConstraint(
            "warning_level_cm IS NULL OR danger_level_cm IS NULL "
            "OR warning_level_cm < danger_level_cm",
            name="ck_sensor_stations_warning_before_danger",
        ),
        CheckConstraint(
            "danger_level_cm IS NULL OR critical_level_cm IS NULL "
            "OR danger_level_cm < critical_level_cm",
            name="ck_sensor_stations_danger_before_critical",
        ),
        CheckConstraint(
            "num_nonnulls(warning_level_cm, danger_level_cm, "
            "critical_level_cm) IN (0, 3)",
            name="ck_sensor_stations_thresholds_all_or_none",
        ),
    )

    station_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    river_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="offline",
        server_default="offline",
        index=True,
    )
    geometry: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )
    warning_level_cm: Mapped[float | None] = mapped_column(Float)
    danger_level_cm: Mapped[float | None] = mapped_column(Float)
    critical_level_cm: Mapped[float | None] = mapped_column(Float)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
