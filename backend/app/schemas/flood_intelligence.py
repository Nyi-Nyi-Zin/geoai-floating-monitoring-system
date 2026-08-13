from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel

FloodScenario = Literal[
    "low_risk",
    "high_predicted_risk",
    "observed_flood_alert",
    "confirmed_high_risk",
]
EarlyWarningLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]


class EarlyWarningClassification(BaseModel):
    probability: float
    level: EarlyWarningLevel
    recommendation: str


class FloodScenarioAssessment(BaseModel):
    ml_probability: float
    sar_detected: bool
    scenario: FloodScenario
    headline: str
    detail: str


class ExposureSummary(BaseModel):
    flagged_cells: int
    affected_area_km2: float
    buildings_at_risk: int
    built_up_area_km2: float
    high_risk_cells: int
    risk_basis: str


class SarValidationEventSummary(BaseModel):
    reference_gfd_event_id: str
    sar_event_id: str
    event_start_date: str
    label_agreement: dict[str, Any]
    model_vs_sar: dict[str, Any]


class SarValidationReport(BaseModel):
    status: Literal["awaiting_sar_labels", "complete"]
    model_version: str | None = None
    gfd_event_count: int = 0
    sar_event_count: int = 0
    paired_event_count: int = 0
    overall_model_vs_sar: dict[str, Any] | None = None
    paired_events: list[SarValidationEventSummary] = []
    interpretation: str | None = None
    message: str | None = None
    generated_at: datetime


class FloodIntelligenceSummary(BaseModel):
    susceptibility_available: bool
    forecast_available: bool
    sar_validation: SarValidationReport
    exposure: ExposureSummary | None = None
    scenario: FloodScenarioAssessment | None = None
    early_warning: EarlyWarningClassification | None = None
    limitations: list[str]
