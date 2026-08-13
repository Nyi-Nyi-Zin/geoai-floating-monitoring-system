import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ForecastRun(Base):
    """Immutable record of a single flood forecast execution."""

    __tablename__ = "forecast_runs"
    __table_args__ = (
        CheckConstraint(
            "forecast_horizon_days >= 1 AND forecast_horizon_days <= 7",
            name="ck_forecast_runs_horizon",
        ),
        CheckConstraint(
            "decision_threshold >= 0 AND decision_threshold <= 1",
            name="ck_forecast_runs_threshold",
        ),
        CheckConstraint(
            "cell_count > 0 AND flagged_cell_count >= 0 "
            "AND flagged_cell_count <= cell_count",
            name="ck_forecast_runs_cell_counts",
        ),
        CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_forecast_runs_status",
        ),
        CheckConstraint(
            "threshold_mode IN ('screening', 'balanced', 'conservative')",
            name="ck_forecast_runs_threshold_mode",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_version: Mapped[str] = mapped_column(
        String(120), nullable=False, unique=True
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("flood_event_ml_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="completed", server_default="completed"
    )
    forecast_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="scenario_forecast",
        server_default="scenario_forecast",
    )
    rainfall_source: Mapped[str] = mapped_column(String(120), nullable=False)
    rainfall_fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    rainfall_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    forecast_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    decision_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    cell_count: Mapped[int] = mapped_column(Integer, nullable=False)
    flagged_cell_count: Mapped[int] = mapped_column(Integer, nullable=False)
    summary_metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ForecastPrediction(Base):
    """Per-cell flood probability for a single forecast run."""

    __tablename__ = "forecast_predictions"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "geo_asset_id",
            name="uq_forecast_predictions_run_asset",
        ),
        CheckConstraint(
            "probability >= 0 AND probability <= 1",
            name="ck_forecast_predictions_probability",
        ),
        CheckConstraint(
            "risk_band IN ('LOW', 'MODERATE', 'HIGH', 'VERY_HIGH')",
            name="ck_forecast_predictions_risk_band",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("forecast_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    geo_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("geo_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_label: Mapped[bool] = mapped_column(Boolean, nullable=False)
    risk_band: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    features: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
