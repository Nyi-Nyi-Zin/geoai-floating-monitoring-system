import uuid
from datetime import date, datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FloodExtent(Base):
    __tablename__ = "flood_extents"
    __table_args__ = (
        CheckConstraint(
            "classification IN ('flood', 'possible_flood')",
            name="ck_flood_extents_classification",
        ),
        CheckConstraint(
            "confidence IN ('high', 'moderate', 'low', 'unknown')",
            name="ck_flood_extents_confidence",
        ),
        CheckConstraint(
            "area_km2 > 0",
            name="ck_flood_extents_area_positive",
        ),
        CheckConstraint(
            "observed_end_date IS NULL OR observed_start_date IS NULL "
            "OR observed_end_date >= observed_start_date",
            name="ck_flood_extents_event_dates",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_id: Mapped[str | None] = mapped_column(String(120), index=True)
    observed_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    observed_start_date: Mapped[date | None] = mapped_column(Date, index=True)
    observed_end_date: Mapped[date | None] = mapped_column(Date, index=True)
    sensor: Mapped[str] = mapped_column(String(100), nullable=False)
    classification: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    confidence: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unknown",
        server_default="unknown",
    )
    field_validated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    license_name: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    geometry: Mapped[Any] = mapped_column(
        Geometry(
            geometry_type="MULTIPOLYGON",
            srid=4326,
            spatial_index=False,
        ),
        nullable=False,
    )
    area_km2: Mapped[float] = mapped_column(Float, nullable=False)
    properties: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
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
