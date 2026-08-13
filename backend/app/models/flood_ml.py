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


class FloodMlModel(Base):
    __tablename__ = "flood_ml_models"
    __table_args__ = (
        CheckConstraint(
            "training_rows > 0 AND positive_rows >= 0 AND negative_rows >= 0",
            name="ck_flood_ml_models_training_counts",
        ),
        CheckConstraint(
            "positive_rows + negative_rows = training_rows",
            name="ck_flood_ml_models_class_counts",
        ),
        CheckConstraint(
            "target_threshold >= 0 AND target_threshold <= 1",
            name="ck_flood_ml_models_target_threshold",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_version: Mapped[str] = mapped_column(
        String(120), nullable=False, unique=True
    )
    algorithm: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="trained", server_default="trained"
    )
    target_name: Mapped[str] = mapped_column(String(120), nullable=False)
    target_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    training_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    positive_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    negative_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    feature_names: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    feature_importance: Mapped[dict[str, float]] = mapped_column(
        JSONB, nullable=False
    )
    methodology: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    artifact_path: Mapped[str | None] = mapped_column(Text)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class FloodMlPrediction(Base):
    __tablename__ = "flood_ml_predictions"
    __table_args__ = (
        UniqueConstraint(
            "model_id",
            "geo_asset_id",
            name="uq_flood_ml_predictions_model_asset",
        ),
        CheckConstraint(
            "probability >= 0 AND probability <= 1",
            name="ck_flood_ml_predictions_probability",
        ),
        CheckConstraint(
            "risk_band IN ('LOW', 'MODERATE', 'HIGH', 'VERY_HIGH')",
            name="ck_flood_ml_predictions_risk_band",
        ),
        CheckConstraint(
            "flooded_fraction >= 0 AND flooded_fraction <= 1",
            name="ck_flood_ml_predictions_flooded_fraction",
        ),
        CheckConstraint(
            "historical_event_count >= 0 AND historical_event_density >= 0",
            name="ck_flood_ml_predictions_historical_labels",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("flood_ml_models.id", ondelete="CASCADE"),
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
    risk_band: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    predicted_label: Mapped[bool] = mapped_column(Boolean, nullable=False)
    flooded_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    historical_event_count: Mapped[int] = mapped_column(Integer, nullable=False)
    historical_event_density: Mapped[float] = mapped_column(Float, nullable=False)
    features: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class FloodEventMlModel(Base):
    __tablename__ = "flood_event_ml_models"
    __table_args__ = (
        CheckConstraint(
            "dataset_rows > 0 AND train_rows > 0 AND event_count >= 4",
            name="ck_flood_event_ml_models_counts",
        ),
        CheckConstraint(
            "positive_rows >= 0 AND negative_rows >= 0 "
            "AND positive_rows + negative_rows = dataset_rows",
            name="ck_flood_event_ml_models_class_counts",
        ),
        CheckConstraint(
            "target_threshold >= 0 AND target_threshold <= 1 "
            "AND decision_threshold >= 0 AND decision_threshold <= 1",
            name="ck_flood_event_ml_models_thresholds",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_version: Mapped[str] = mapped_column(
        String(120), nullable=False, unique=True
    )
    algorithm: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="experimental", server_default="experimental"
    )
    target_name: Mapped[str] = mapped_column(String(120), nullable=False)
    target_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    decision_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    dataset_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    train_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    positive_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    negative_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False)
    feature_names: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    feature_importance: Mapped[dict[str, float]] = mapped_column(
        JSONB, nullable=False
    )
    split_events: Mapped[dict[str, list[str]]] = mapped_column(JSONB, nullable=False)
    methodology: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    artifact_path: Mapped[str | None] = mapped_column(Text)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class FloodEventMlPrediction(Base):
    __tablename__ = "flood_event_ml_predictions"
    __table_args__ = (
        UniqueConstraint(
            "model_id",
            "event_id",
            "geo_asset_id",
            name="uq_flood_event_ml_predictions_model_event_asset",
        ),
        CheckConstraint(
            "probability >= 0 AND probability <= 1 "
            "AND flooded_fraction >= 0 AND flooded_fraction <= 1",
            name="ck_flood_event_ml_predictions_probabilities",
        ),
        CheckConstraint(
            "split IN ('validation', 'test')",
            name="ck_flood_event_ml_predictions_split",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("flood_event_ml_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    event_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    split: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    geo_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("geo_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_label: Mapped[bool] = mapped_column(Boolean, nullable=False)
    flooded_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
