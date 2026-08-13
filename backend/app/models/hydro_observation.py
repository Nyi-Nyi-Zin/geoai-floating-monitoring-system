import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HydroObservation(Base):
    __tablename__ = "hydro_observations"
    __table_args__ = (
        CheckConstraint(
            "rainfall_mm IS NOT NULL OR water_level_m IS NOT NULL "
            "OR discharge_m3s IS NOT NULL",
            name="ck_hydro_observations_has_measurement",
        ),
        CheckConstraint(
            "rainfall_mm IS NULL OR rainfall_mm >= 0",
            name="ck_hydro_observations_rainfall_nonnegative",
        ),
        CheckConstraint(
            "discharge_m3s IS NULL OR discharge_m3s >= 0",
            name="ck_hydro_observations_discharge_nonnegative",
        ),
        CheckConstraint(
            "quality_status IN "
            "('unverified', 'provisional', 'verified', 'rejected')",
            name="ck_hydro_observations_quality_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    station_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    station_name: Mapped[str] = mapped_column(String(255), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    rainfall_mm: Mapped[float | None] = mapped_column(Float)
    water_level_m: Mapped[float | None] = mapped_column(Float)
    discharge_m3s: Mapped[float | None] = mapped_column(Float)
    soil_moisture_percent: Mapped[float | None] = mapped_column(Float)
    battery_percent: Mapped[float | None] = mapped_column(Float)
    ingestion_key: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
    )
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    quality_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unverified",
        server_default="unverified",
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    geometry: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )
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
