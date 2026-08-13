import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(
            "risk_level IN ('MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_alerts_risk_level",
        ),
        CheckConstraint(
            "status IN ('open', 'acknowledged')",
            name="ck_alerts_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    station_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("sensor_stations.station_id"),
        nullable=False,
        index=True,
    )
    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hydro_observations.id"),
        nullable=False,
        unique=True,
    )
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    water_level_cm: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_cm: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        server_default="open",
        index=True,
    )
    acknowledged_by: Mapped[str | None] = mapped_column(String(255))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledgement_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
