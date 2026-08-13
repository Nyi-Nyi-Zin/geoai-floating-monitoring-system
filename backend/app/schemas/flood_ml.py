from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

RiskBand = Literal["LOW", "MODERATE", "HIGH", "VERY_HIGH"]


class FloodMlModelSummary(BaseModel):
    id: UUID
    model_version: str
    algorithm: str
    status: str
    target_name: str
    target_threshold: float
    training_rows: int
    positive_rows: int
    negative_rows: int
    feature_names: list[str]
    metrics: dict[str, Any]
    feature_importance: dict[str, float]
    methodology: dict[str, Any]
    trained_at: datetime
    operational_forecast: Literal[False] = False


class FloodMlPredictionIndexItem(BaseModel):
    id: UUID
    probability: float
    risk_band: RiskBand
    predicted_label: bool
    flooded_fraction: float
    historical_event_count: int
    historical_event_density: float
    explanation: dict[str, Any]


class FloodMlPredictionSummary(BaseModel):
    total_cells: int
    mean_probability: float
    predicted_positive_cells: int
    band_counts: dict[RiskBand, int]


class FloodMlPredictionIndex(BaseModel):
    model: FloodMlModelSummary
    items: list[FloodMlPredictionIndexItem]
    summary: FloodMlPredictionSummary
    limitations: list[str]


class FloodEventReadiness(BaseModel):
    ready: bool
    event_count: int
    rainfall_aligned_event_count: int
    missing_rainfall_event_count: int
    gfd_event_count: int = 0
    sar_event_count: int = 0
    sar_validation_ready: bool = False
    event_observed_from: date | None
    event_observed_to: date | None
    rainfall_available_from: date | None
    rainfall_available_to: date | None
    minimum_event_count: int
    recommended_event_count: int
    blockers: list[str]
    next_steps: list[str]


class FloodEventMlEventSummary(BaseModel):
    event_id: str
    event_start_date: date
    split: Literal["validation", "test"]
    total_cells: int
    observed_positive_cells: int


class FloodEventMlModelSummary(BaseModel):
    id: UUID
    model_version: str
    algorithm: str
    status: Literal["experimental"]
    target_name: str
    target_threshold: float
    decision_threshold: float
    dataset_rows: int
    train_rows: int
    positive_rows: int
    negative_rows: int
    event_count: int
    feature_names: list[str]
    metrics: dict[str, Any]
    feature_importance: dict[str, float]
    split_events: dict[str, list[str]]
    methodology: dict[str, Any]
    trained_at: datetime
    operational_forecast: Literal[False] = False
    display_mode: Literal["historical_hindcast"] = "historical_hindcast"
    operating_mode: Literal["screening", "balanced", "conservative", "model_default"] = (
        "model_default"
    )


HindcastOutcome = Literal["tp", "fp", "fn", "tn"]


class FloodEventMlPredictionItem(BaseModel):
    id: UUID
    probability: float
    predicted_label: bool
    flooded_fraction: float
    outcome: HindcastOutcome
    decision_probability: float


class FloodEventMlPredictionSummary(BaseModel):
    total_cells: int
    mean_probability: float
    predicted_positive_cells: int
    observed_positive_cells: int
    true_positive_cells: int
    false_positive_cells: int
    false_negative_cells: int
    precision: float
    recall: float


class FloodEventMlPredictionIndex(BaseModel):
    model: FloodEventMlModelSummary
    event: FloodEventMlEventSummary
    available_events: list[FloodEventMlEventSummary]
    items: list[FloodEventMlPredictionItem]
    summary: FloodEventMlPredictionSummary
    limitations: list[str]


class FloodEventMlEvaluationReport(BaseModel):
    model_version: str
    algorithm: str
    trained_at: datetime
    active_threshold_mode: str
    decision_threshold: float
    water_temper_beta: float
    test: dict[str, Any]
    test_by_threshold_mode: dict[str, Any]
    test_by_event: dict[str, Any]
    rolling_origin_summary: dict[str, Any]
    ranking_quality: dict[str, Any]
    test_calibration: dict[str, Any]
    false_positive_diagnostics: list[dict[str, Any]]
    recommendation: str
    limitations: list[str]
