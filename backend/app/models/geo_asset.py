import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GeoAsset(Base):
    __tablename__ = "geo_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
    )
    description: Mapped[str | None] = mapped_column(Text)
    geometry: Mapped[Any] = mapped_column(
        Geometry(
            geometry_type="GEOMETRY",
            srid=4326,
            spatial_index=False,
        ),
        nullable=False,
    )
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
