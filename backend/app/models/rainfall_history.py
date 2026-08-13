import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RainfallHistory(Base):
    __tablename__ = "rainfall_history"
    __table_args__ = (
        UniqueConstraint(
            "source_key",
            "observed_date",
            name="uq_rainfall_history_source_date",
        ),
        CheckConstraint(
            "mean_precipitation_mm >= 0 "
            "AND max_precipitation_mm >= mean_precipitation_mm",
            name="ck_rainfall_history_precipitation_valid",
        ),
        CheckConstraint(
            "p90_precipitation_mm >= 0",
            name="ck_rainfall_history_p90_nonnegative",
        ),
        CheckConstraint(
            "accumulation_3d_mm >= 0 AND accumulation_7d_mm >= 0 "
            "AND accumulation_30d_mm >= 0",
            name="ck_rainfall_history_accumulations_nonnegative",
        ),
        CheckConstraint(
            "grid_cell_count > 0",
            name="ck_rainfall_history_grid_count_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_key: Mapped[str] = mapped_column(String(120), nullable=False)
    observed_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    mean_precipitation_mm: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    max_precipitation_mm: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    p90_precipitation_mm: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    accumulation_3d_mm: Mapped[float] = mapped_column(Float, nullable=False)
    accumulation_7d_mm: Mapped[float] = mapped_column(Float, nullable=False)
    accumulation_30d_mm: Mapped[float] = mapped_column(Float, nullable=False)
    grid_cell_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_resolution_m: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="reanalysis",
        server_default="reanalysis",
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
