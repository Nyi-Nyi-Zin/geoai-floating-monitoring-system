import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DataLayer(Base):
    __tablename__ = "data_layers"
    __table_args__ = (
        CheckConstraint(
            "data_kind IN ('raster', 'vector', 'timeseries', 'service')",
            name="ck_data_layers_kind",
        ),
        CheckConstraint(
            "quality_status IN ('verified', 'limited', 'unreviewed', 'deprecated')",
            name="ck_data_layers_quality_status",
        ),
        CheckConstraint(
            "spatial_resolution_m IS NULL OR spatial_resolution_m > 0",
            name="ck_data_layers_resolution_positive",
        ),
        CheckConstraint(
            "temporal_coverage_start IS NULL "
            "OR temporal_coverage_end IS NULL "
            "OR temporal_coverage_start <= temporal_coverage_end",
            name="ck_data_layers_temporal_order",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    layer_key: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    data_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    license_name: Mapped[str] = mapped_column(String(255), nullable=False)
    license_url: Mapped[str | None] = mapped_column(Text)
    attribution: Mapped[str] = mapped_column(Text, nullable=False)
    usage_constraints: Mapped[str | None] = mapped_column(Text)
    coverage: Mapped[Any | None] = mapped_column(
        Geometry(
            geometry_type="GEOMETRY",
            srid=4326,
            spatial_index=False,
        ),
        nullable=True,
    )
    spatial_resolution_m: Mapped[float | None] = mapped_column(Float)
    temporal_coverage_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    temporal_coverage_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    update_frequency: Mapped[str | None] = mapped_column(String(255))
    quality_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    quality_notes: Mapped[str] = mapped_column(Text, nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
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
