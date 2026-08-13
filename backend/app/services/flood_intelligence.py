"""Flood intelligence: ML vs SAR fusion, exposure, and early-warning classification."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.flood_extent import FloodExtent
from app.models.geo_asset import GeoAsset
from app.schemas.flood_intelligence import (
    EarlyWarningClassification,
    ExposureSummary,
    FloodIntelligenceSummary,
    FloodScenarioAssessment,
    SarValidationEventSummary,
    SarValidationReport,
)
from app.services.flood_ml import FloodMlService

CELL_AREA_KM2 = 0.25
DEFAULT_ARTIFACT = Path("artifacts/maubin_sar_label_validation.json")
HIGH_RISK_PROBABILITY = 0.5


def classify_early_warning(probability: float) -> EarlyWarningClassification:
    value = max(0.0, min(1.0, float(probability)))
    if value < 0.25:
        return EarlyWarningClassification(
            probability=round(value, 4),
            level="LOW",
            recommendation="Routine monitoring. No immediate action required.",
        )
    if value < 0.50:
        return EarlyWarningClassification(
            probability=round(value, 4),
            level="MODERATE",
            recommendation="Monitor rainfall and waterway levels closely.",
        )
    if value < 0.75:
        return EarlyWarningClassification(
            probability=round(value, 4),
            level="HIGH",
            recommendation="Prepare response teams and review evacuation routes.",
        )
    return EarlyWarningClassification(
        probability=round(value, 4),
        level="CRITICAL",
        recommendation="Activate emergency response and issue public alerts.",
    )


def classify_flood_scenario(
    ml_probability: float,
    sar_detected: bool,
    *,
    threshold: float = HIGH_RISK_PROBABILITY,
) -> FloodScenarioAssessment:
    ml_high = float(ml_probability) >= threshold
    if ml_high and not sar_detected:
        return FloodScenarioAssessment(
            ml_probability=round(ml_probability, 4),
            sar_detected=False,
            scenario="high_predicted_risk",
            headline="High predicted risk",
            detail=(
                "ML probability is elevated but no SAR flood extent was detected "
                "for the selected event window."
            ),
        )
    if not ml_high and sar_detected:
        return FloodScenarioAssessment(
            ml_probability=round(ml_probability, 4),
            sar_detected=True,
            scenario="observed_flood_alert",
            headline="Observed flood alert",
            detail=(
                "Sentinel-1 detected inundation while ML probability remained below "
                "the decision threshold."
            ),
        )
    if ml_high and sar_detected:
        return FloodScenarioAssessment(
            ml_probability=round(ml_probability, 4),
            sar_detected=True,
            scenario="confirmed_high_risk",
            headline="Confirmed high-risk flood",
            detail=(
                "ML forecast and SAR observation both indicate significant flood risk."
            ),
        )
    return FloodScenarioAssessment(
        ml_probability=round(ml_probability, 4),
        sar_detected=False,
        scenario="low_risk",
        headline="Low combined risk",
        detail="Neither ML probability nor SAR observation indicates active flooding.",
    )


def built_up_fraction(properties: dict[str, Any] | None) -> float:
    if not properties:
        return 0.0
    percentages = properties.get("land_cover_percentages") or {}
    try:
        built = float(percentages.get("50") or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if built > 1.0:
        built /= 100.0
    return min(1.0, max(0.0, built))


class FloodIntelligenceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def sar_validation_report(self) -> SarValidationReport:
        payload = self._load_sar_validation_payload()
        if payload.get("status") == "awaiting_sar_labels":
            return SarValidationReport(
                status="awaiting_sar_labels",
                model_version=payload.get("model_version"),
                gfd_event_count=int(payload.get("gfd_event_count") or 0),
                sar_event_count=int(payload.get("sar_event_count") or 0),
                message=payload.get("message"),
                generated_at=datetime.now(UTC),
                limitations=[
                    "SAR labels are not imported yet. Export with "
                    "scripts/gee_export_maubin_sar_events.js and import via "
                    "scripts.import_flood_sar_events."
                ],
            )
        paired_events = [
            SarValidationEventSummary(**event)
            for event in payload.get("paired_events", [])
        ]
        return SarValidationReport(
            status="complete",
            model_version=payload.get("model_version"),
            gfd_event_count=int(payload.get("gfd_event_count") or 0),
            sar_event_count=int(payload.get("sar_event_count") or 0),
            paired_event_count=int(payload.get("paired_event_count") or 0),
            overall_model_vs_sar=payload.get("overall_model_vs_sar"),
            paired_events=paired_events,
            interpretation=payload.get("interpretation"),
            generated_at=datetime.now(UTC),
            limitations=[
                "SAR labels are independent validation targets; GFD agreement "
                "reflects label noise between sensors."
            ],
        )

    def exposure_summary(
        self,
        *,
        use_forecast: bool = False,
        probability_threshold: float = 0.5,
    ) -> ExposureSummary:
        flagged_ids: set[Any] = set()
        high_risk_ids: set[Any] = set()
        risk_basis = "terrain_screening"

        if use_forecast:
            from app.services.forecast import ForecastService

            try:
                forecast = ForecastService(self.db).get_run_predictions()
            except HTTPException:
                forecast = None
            if forecast is not None:
                risk_basis = "experimental_forecast"
                for item in forecast.items:
                    if item.predicted_label or item.risk_band in {"HIGH", "VERY_HIGH"}:
                        flagged_ids.add(item.id)
                    if item.probability >= probability_threshold:
                        high_risk_ids.add(item.id)
        else:
            ml_service = FloodMlService(self.db)
            try:
                predictions = ml_service.prediction_index()
            except HTTPException:
                predictions = None
            if predictions is not None:
                risk_basis = "historical_ml_susceptibility"
                for item in predictions.items:
                    if item.predicted_label or item.risk_band in {"HIGH", "VERY_HIGH"}:
                        flagged_ids.add(item.id)
                    if item.probability >= probability_threshold:
                        high_risk_ids.add(item.id)

        if not flagged_ids:
            return ExposureSummary(
                flagged_cells=0,
                affected_area_km2=0.0,
                buildings_at_risk=0,
                built_up_area_km2=0.0,
                high_risk_cells=0,
                risk_basis=risk_basis,
            )

        assets = self.db.scalars(
            select(GeoAsset).where(GeoAsset.id.in_(flagged_ids))
        ).all()
        built_up_km2 = 0.0
        buildings_at_risk = 0
        for asset in assets:
            built_fraction = built_up_fraction(asset.properties)
            if built_fraction <= 0:
                continue
            cell_built_km2 = built_fraction * CELL_AREA_KM2
            built_up_km2 += cell_built_km2
            buildings_at_risk += max(1, round(cell_built_km2 * 450))

        return ExposureSummary(
            flagged_cells=len(flagged_ids),
            affected_area_km2=round(len(flagged_ids) * CELL_AREA_KM2, 2),
            buildings_at_risk=buildings_at_risk,
            built_up_area_km2=round(built_up_km2, 2),
            high_risk_cells=len(high_risk_ids),
            risk_basis=risk_basis,
        )

    def intelligence_summary(
        self,
        *,
        event_id: str | None = None,
        use_forecast: bool = False,
    ) -> FloodIntelligenceSummary:
        readiness = FloodMlService(self.db).event_readiness()
        sar_report = self.sar_validation_report()
        exposure = self.exposure_summary(use_forecast=use_forecast)

        scenario: FloodScenarioAssessment | None = None
        early_warning: EarlyWarningClassification | None = None
        mean_probability = 0.0
        sar_detected = False

        if event_id:
            sar_detected = self._sar_detected_for_event(event_id)
        elif readiness.sar_event_count > 0:
            latest_sar = self.db.scalar(
                select(FloodExtent.event_id)
                .where(FloodExtent.source_key.like("maubin:sar:event:%"))
                .order_by(FloodExtent.observed_start_date.desc())
                .limit(1)
            )
            if latest_sar:
                sar_detected = True
                event_id = str(latest_sar)

        try:
            event_predictions = FloodMlService(self.db).event_prediction_index(
                event_id=event_id,
                threshold_mode="balanced",
            )
            mean_probability = float(event_predictions.summary.mean_probability)
            if event_id is None:
                event_id = event_predictions.event.event_id
            sar_detected = sar_detected or self._sar_detected_for_event(event_id)
            scenario = classify_flood_scenario(mean_probability, sar_detected)
            early_warning = classify_early_warning(mean_probability)
        except HTTPException:
            try:
                susceptibility = FloodMlService(self.db).prediction_index()
                mean_probability = float(susceptibility.summary.mean_probability)
                early_warning = classify_early_warning(mean_probability)
            except HTTPException:
                pass

        limitations = [
            "Susceptibility (static) and forecast (dynamic) are separate products.",
            "Building exposure uses WorldCover built-up fraction, not OSM footprints.",
        ]
        if sar_report.status != "complete":
            limitations.append(
                "SAR validation awaits Sentinel-1 label import from Earth Engine."
            )

        susceptibility_available = False
        forecast_available = False
        try:
            FloodMlService(self.db).prediction_index()
            susceptibility_available = True
        except HTTPException:
            pass
        try:
            from app.services.forecast import ForecastService

            ForecastService(self.db).get_run_predictions()
            forecast_available = True
        except HTTPException:
            pass
        if use_forecast and not forecast_available:
            limitations.append(
                "No completed forecast run is available. Run a forecast before "
                "using forecast-based exposure."
            )

        return FloodIntelligenceSummary(
            susceptibility_available=susceptibility_available,
            forecast_available=forecast_available or use_forecast,
            sar_validation=sar_report,
            exposure=exposure,
            scenario=scenario,
            early_warning=early_warning,
            limitations=limitations,
        )

    def _sar_detected_for_event(self, event_id: str) -> bool:
        sar_event_id = event_id if event_id.startswith("sar-") else f"sar-{event_id}"
        count = self.db.scalar(
            select(func.count())
            .select_from(FloodExtent)
            .where(
                FloodExtent.event_id.in_([event_id, sar_event_id]),
                FloodExtent.source_key.like("maubin:sar:event:%"),
            )
        )
        return int(count or 0) > 0

    def _load_sar_validation_payload(self) -> dict[str, Any]:
        if DEFAULT_ARTIFACT.exists():
            return json.loads(DEFAULT_ARTIFACT.read_text(encoding="utf-8"))
        try:
            from scripts.evaluate_sar_label_validation import run_validation

            class Args:
                artifact = Path("artifacts/maubin_flood_event_logistic_v5.json")
                target_threshold = 0.10
                label_mode = "flood_excess"
                output = DEFAULT_ARTIFACT

            return run_validation(Args())
        except Exception as exc:
            readiness = FloodMlService(self.db).event_readiness()
            if readiness.sar_event_count == 0:
                return {
                    "status": "awaiting_sar_labels",
                    "gfd_event_count": readiness.gfd_event_count,
                    "sar_event_count": 0,
                    "message": (
                        "No SAR labels stored. Export with "
                        "gee_export_maubin_sar_events.js and import."
                    ),
                }
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "sar_validation_unavailable",
                    "message": f"SAR validation could not be computed: {exc}",
                },
            ) from exc
