from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

RiskBand = Literal["LOW", "MODERATE", "HIGH", "VERY_HIGH"]
ThresholdMode = Literal["screening", "balanced", "conservative"]


class ForecastRunCreate(BaseModel):
    """Request body for triggering a new forecast run."""

    forecast_days: int = Field(
        default=7, ge=1, le=7,
        description="Open-Meteo forecast horizon in days",
    )
    target_date: date | None = Field(
        default=None,
        description="Date to forecast; defaults to tomorrow if not set",
    )
    threshold_mode: ThresholdMode = Field(
        default="balanced",
        description="Operating threshold mode for flagging cells",
    )


class ForecastRunSummary(BaseModel):
    """Compact forecast run metadata."""

    id: UUID
    run_version: str
    model_id: UUID
    model_version: str
    status: str
    forecast_type: str
    rainfall_source: str
    rainfall_fetched_at: datetime
    forecast_horizon_days: int
    target_date: date
    decision_threshold: float
    threshold_mode: str
    cell_count: int
    flagged_cell_count: int
    summary_metrics: dict[str, Any]
    limitations: list[str]
    created_at: datetime
    experimental: Literal[True] = True


class ForecastRunListItem(BaseModel):
    """Item for listing past forecast runs."""

    id: UUID
    run_version: str
    status: str
    target_date: date
    threshold_mode: str
    cell_count: int
    flagged_cell_count: int
    created_at: datetime


class ForecastPredictionItem(BaseModel):
    """Per-cell flood probability from a forecast run."""

    id: UUID  # geo_asset_id
    probability: float
    predicted_label: bool
    risk_band: RiskBand


class ForecastPredictionSummary(BaseModel):
    """Aggregate statistics for a forecast run's predictions."""

    total_cells: int
    mean_probability: float
    flagged_cells: int
    band_counts: dict[RiskBand, int]


class ForecastPredictionIndex(BaseModel):
    """Full forecast run result with model info and all predictions."""

    run: ForecastRunSummary
    items: list[ForecastPredictionItem]
    summary: ForecastPredictionSummary
    limitations: list[str]
    display_mode: Literal["scenario_forecast"] = "scenario_forecast"


class ForecastRunList(BaseModel):
    """Paginated list of past forecast runs."""

    items: list[ForecastRunListItem]
    total: int
