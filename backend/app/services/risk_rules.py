from dataclasses import dataclass
from typing import Literal

RiskClassification = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL", "UNAVAILABLE"]


@dataclass(frozen=True)
class ThresholdAssessment:
    risk_level: RiskClassification
    crossed_threshold_cm: float | None
    explanation: str


def classify_water_level(
    water_level_cm: float | None,
    *,
    warning_level_cm: float | None,
    danger_level_cm: float | None,
    critical_level_cm: float | None,
) -> ThresholdAssessment:
    thresholds = (
        warning_level_cm,
        danger_level_cm,
        critical_level_cm,
    )
    if water_level_cm is None:
        return ThresholdAssessment(
            risk_level="UNAVAILABLE",
            crossed_threshold_cm=None,
            explanation="No observed water level was supplied.",
        )
    if any(value is None for value in thresholds):
        return ThresholdAssessment(
            risk_level="UNAVAILABLE",
            crossed_threshold_cm=None,
            explanation="The station does not have a complete threshold set.",
        )

    warning = float(warning_level_cm)
    danger = float(danger_level_cm)
    critical = float(critical_level_cm)
    if water_level_cm >= critical:
        return ThresholdAssessment(
            risk_level="CRITICAL",
            crossed_threshold_cm=critical,
            explanation="Observed water level crossed the configured critical threshold.",
        )
    if water_level_cm >= danger:
        return ThresholdAssessment(
            risk_level="HIGH",
            crossed_threshold_cm=danger,
            explanation="Observed water level crossed the configured danger threshold.",
        )
    if water_level_cm >= warning:
        return ThresholdAssessment(
            risk_level="MEDIUM",
            crossed_threshold_cm=warning,
            explanation="Observed water level crossed the configured warning threshold.",
        )
    return ThresholdAssessment(
        risk_level="LOW",
        crossed_threshold_cm=None,
        explanation="Observed water level is below the configured warning threshold.",
    )
