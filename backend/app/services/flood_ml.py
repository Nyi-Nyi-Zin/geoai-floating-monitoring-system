from collections import Counter
from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.flood_ml import (
    FloodEventMlModel,
    FloodEventMlPrediction,
    FloodMlModel,
    FloodMlPrediction,
)
from app.models.flood_extent import FloodExtent
from app.models.geo_asset import GeoAsset
from app.models.rainfall_history import RainfallHistory
from app.schemas.flood_ml import (
    FloodEventReadiness,
    FloodEventMlEvaluationReport,
    FloodEventMlEventSummary,
    FloodEventMlModelSummary,
    FloodEventMlPredictionIndex,
    FloodEventMlPredictionItem,
    FloodEventMlPredictionSummary,
    FloodMlModelSummary,
    FloodMlPredictionIndex,
    FloodMlPredictionIndexItem,
    FloodMlPredictionSummary,
    HindcastOutcome,
    RiskBand,
)

MINIMUM_EVENT_COUNT = 4
RECOMMENDED_EVENT_COUNT = 8


def surface_water_influence(properties: dict[str, Any] | None) -> float:
    if not properties:
        return 0.0
    percentages = properties.get("land_cover_percentages") or {}
    try:
        water = float(percentages.get("80") or 0.0)
        wetland = float(percentages.get("90") or 0.0)
        mangrove = float(percentages.get("95") or 0.0)
    except (TypeError, ValueError):
        return 0.0
    total = water + wetland + mangrove
    if total > 1.0:
        total /= 100.0
    return min(1.0, max(0.0, total))


def temper_probability(
    probability: float, surface_water: float, beta: float
) -> float:
    tempered = float(probability) * (1.0 - float(beta) * max(0.0, min(1.0, surface_water)))
    return max(0.0, min(1.0, tempered))


def hindcast_outcome(
    *,
    predicted_label: bool,
    observed_positive: bool,
) -> HindcastOutcome:
    if predicted_label and observed_positive:
        return "tp"
    if predicted_label and not observed_positive:
        return "fp"
    if not predicted_label and observed_positive:
        return "fn"
    return "tn"


def evaluation_recommendation(metrics: dict[str, Any]) -> str:
    test = metrics.get("test") if isinstance(metrics.get("test"), dict) else {}
    precision = float(test.get("precision") or 0.0)
    recall = float(test.get("recall") or 0.0)
    rolling = metrics.get("rolling_origin_cross_validation")
    rolling_summary = (
        rolling.get("summary")
        if isinstance(rolling, dict) and isinstance(rolling.get("summary"), dict)
        else {}
    )
    conservative = (
        rolling_summary.get("conservative")
        if isinstance(rolling_summary.get("conservative"), dict)
        else {}
    )
    rolling_precision = float(conservative.get("mean_precision") or 0.0)

    if precision < 0.20:
        return (
            "Keep experimental-only. Held-out precision remains below 20%; do not "
            "use for public alerts. Prefer conservative mode and review FP/FN maps."
        )
    if precision < 0.35 or rolling_precision < 0.25:
        return (
            "Pilot review only. Precision improved but is still too low for automated "
            "warnings; require human review and independent event validation."
        )
    if recall < 0.25:
        return (
            "Precision-oriented settings are reducing false alarms, but recall is low. "
            "Use screening mode for coverage and conservative mode for escalation."
        )
    return (
        "Discrimination is usable for historical analysis. Continue monitoring "
        "rolling-origin stability before any operational escalation path."
    )


def calculate_event_readiness(
    event_dates: list[date], rainfall_dates: set[date]
) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if len(event_dates) < MINIMUM_EVENT_COUNT:
        blockers.append(
            f"At least {MINIMUM_EVENT_COUNT} individual flood events are required "
            "for train/validation/test temporal splits."
        )
    aligned = sum(event_date in rainfall_dates for event_date in event_dates)
    if aligned < MINIMUM_EVENT_COUNT:
        blockers.append(
            f"Rainfall must be available on the start date of at least "
            f"{MINIMUM_EVENT_COUNT} flood events; currently {aligned} are aligned."
        )
    return not blockers, blockers


def to_model_summary(model: FloodMlModel) -> FloodMlModelSummary:
    return FloodMlModelSummary(
        id=model.id,
        model_version=model.model_version,
        algorithm=model.algorithm,
        status=model.status,
        target_name=model.target_name,
        target_threshold=model.target_threshold,
        training_rows=model.training_rows,
        positive_rows=model.positive_rows,
        negative_rows=model.negative_rows,
        feature_names=model.feature_names,
        metrics=model.metrics,
        feature_importance=model.feature_importance,
        methodology=model.methodology,
        trained_at=model.trained_at,
    )


def to_event_model_summary(model: FloodEventMlModel) -> FloodEventMlModelSummary:
    return FloodEventMlModelSummary(
        id=model.id,
        model_version=model.model_version,
        algorithm=model.algorithm,
        status=model.status,
        target_name=model.target_name,
        target_threshold=model.target_threshold,
        decision_threshold=model.decision_threshold,
        dataset_rows=model.dataset_rows,
        train_rows=model.train_rows,
        positive_rows=model.positive_rows,
        negative_rows=model.negative_rows,
        event_count=model.event_count,
        feature_names=model.feature_names,
        metrics=model.metrics,
        feature_importance=model.feature_importance,
        split_events=model.split_events,
        methodology=model.methodology,
        trained_at=model.trained_at,
    )


class FloodMlService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def latest_model_row(self) -> FloodMlModel:
        model = self.db.scalar(
            select(FloodMlModel)
            .where(FloodMlModel.status == "trained")
            .order_by(FloodMlModel.trained_at.desc())
            .limit(1)
        )
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "flood_ml_model_not_found",
                    "message": "No trained flood susceptibility model is available.",
                },
            )
        return model

    def latest_model(self) -> FloodMlModelSummary:
        return to_model_summary(self.latest_model_row())

    def prediction_index(self) -> FloodMlPredictionIndex:
        model = self.latest_model_row()
        predictions = self.db.scalars(
            select(FloodMlPrediction)
            .where(FloodMlPrediction.model_id == model.id)
            .order_by(FloodMlPrediction.probability.desc())
        ).all()
        counts: Counter[RiskBand] = Counter(
            prediction.risk_band for prediction in predictions
        )
        mean_probability = (
            float(
                self.db.scalar(
                    select(func.avg(FloodMlPrediction.probability)).where(
                        FloodMlPrediction.model_id == model.id
                    )
                )
                or 0
            )
            if predictions
            else 0.0
        )
        return FloodMlPredictionIndex(
            model=to_model_summary(model),
            items=[
                FloodMlPredictionIndexItem(
                    id=prediction.geo_asset_id,
                    probability=round(prediction.probability, 6),
                    risk_band=prediction.risk_band,
                    predicted_label=prediction.predicted_label,
                    flooded_fraction=round(prediction.flooded_fraction, 6),
                    historical_event_count=prediction.historical_event_count,
                    historical_event_density=round(
                        prediction.historical_event_density, 6
                    ),
                    explanation=prediction.explanation,
                )
                for prediction in predictions
            ],
            summary=FloodMlPredictionSummary(
                total_cells=len(predictions),
                mean_probability=round(mean_probability, 6),
                predicted_positive_cells=sum(
                    prediction.predicted_label for prediction in predictions
                ),
                band_counts={
                    band: counts[band]
                    for band in ("LOW", "MODERATE", "HIGH", "VERY_HIGH")
                },
            ),
            limitations=list(model.methodology.get("limitations", [])),
        )

    def event_readiness(self) -> FloodEventReadiness:
        event_rows = self.db.execute(
            select(FloodExtent.event_id, FloodExtent.observed_start_date)
            .where(
                FloodExtent.event_id.is_not(None),
                FloodExtent.observed_start_date.is_not(None),
            )
            .distinct()
            .order_by(FloodExtent.observed_start_date, FloodExtent.event_id)
        ).all()
        gfd_rows = self.db.execute(
            select(FloodExtent.event_id, FloodExtent.observed_start_date)
            .where(
                FloodExtent.event_id.is_not(None),
                FloodExtent.observed_start_date.is_not(None),
                FloodExtent.source_key.like("maubin:gfd:event:%"),
            )
            .distinct()
            .order_by(FloodExtent.observed_start_date, FloodExtent.event_id)
        ).all()
        sar_rows = self.db.execute(
            select(FloodExtent.event_id, FloodExtent.observed_start_date)
            .where(
                FloodExtent.event_id.is_not(None),
                FloodExtent.observed_start_date.is_not(None),
                FloodExtent.source_key.like("maubin:sar:event:%"),
            )
            .distinct()
            .order_by(FloodExtent.observed_start_date, FloodExtent.event_id)
        ).all()
        event_dates = [row[1] for row in event_rows]
        gfd_dates = [row[1] for row in gfd_rows]
        rainfall_dates = set(
            self.db.scalars(select(RainfallHistory.observed_date)).all()
        )
        ready, blockers = calculate_event_readiness(gfd_dates, rainfall_dates)
        aligned = sum(event_date in rainfall_dates for event_date in gfd_dates)
        sar_aligned = sum(row[1] in rainfall_dates for row in sar_rows)
        next_steps: list[str] = []
        if len(gfd_rows) < MINIMUM_EVENT_COUNT:
            next_steps.append(
                "Export and import individual GFD events with event IDs and dates."
            )
        if sar_rows and sar_aligned < len(sar_rows):
            next_steps.append(
                "Backfill ERA5 rainfall for SAR event dates that are not covered."
            )
        elif not sar_rows:
            next_steps.append(
                "Export Sentinel-1 SAR labels with scripts/gee_export_maubin_sar_events.js "
                "and import via scripts.import_flood_sar_events for independent validation."
            )
        elif sar_rows:
            next_steps.append(
                "Run scripts.evaluate_sar_label_validation to compare SAR labels "
                "against GFD and score the existing v5 model."
            )
        if gfd_rows and aligned < len(gfd_rows):
            next_steps.append(
                "Backfill ERA5 rainfall for GFD event dates that are not covered."
            )
        if ready:
            next_steps.append(
                "Build the event-cell dataset and train the temporal baseline."
            )
        return FloodEventReadiness(
            ready=ready,
            event_count=len(gfd_rows),
            rainfall_aligned_event_count=aligned,
            missing_rainfall_event_count=len(gfd_rows) - aligned,
            gfd_event_count=len(gfd_rows),
            sar_event_count=len(sar_rows),
            sar_validation_ready=len(sar_rows) > 0 and sar_aligned == len(sar_rows),
            event_observed_from=min(event_dates) if event_dates else None,
            event_observed_to=max(event_dates) if event_dates else None,
            rainfall_available_from=min(rainfall_dates) if rainfall_dates else None,
            rainfall_available_to=max(rainfall_dates) if rainfall_dates else None,
            minimum_event_count=MINIMUM_EVENT_COUNT,
            recommended_event_count=RECOMMENDED_EVENT_COUNT,
            blockers=blockers,
            next_steps=next_steps,
        )

    def latest_event_model_row(self) -> FloodEventMlModel:
        model = self.db.scalar(
            select(FloodEventMlModel)
            .where(FloodEventMlModel.status == "experimental")
            .order_by(FloodEventMlModel.trained_at.desc())
            .limit(1)
        )
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "flood_event_ml_model_not_found",
                    "message": "No trained flood event model is available.",
                },
            )
        return model

    def latest_event_model(self) -> FloodEventMlModelSummary:
        return to_event_model_summary(self.latest_event_model_row())

    def event_model_evaluation(self) -> FloodEventMlEvaluationReport:
        model = self.latest_event_model_row()
        metrics = model.metrics if isinstance(model.metrics, dict) else {}
        profiles = metrics.get("threshold_profiles", {})
        active_mode = str(metrics.get("active_threshold_mode") or "conservative")
        active_profile = (
            profiles.get(active_mode, {}) if isinstance(profiles, dict) else {}
        )
        decision_threshold = float(
            active_profile.get("threshold")
            if isinstance(active_profile.get("threshold"), (int, float))
            else model.decision_threshold
        )
        water_temper_beta = float(active_profile.get("water_temper_beta") or 0.0)
        rolling = metrics.get("rolling_origin_cross_validation")
        rolling_summary = (
            rolling.get("summary")
            if isinstance(rolling, dict) and isinstance(rolling.get("summary"), dict)
            else {}
        )
        return FloodEventMlEvaluationReport(
            model_version=model.model_version,
            algorithm=model.algorithm,
            trained_at=model.trained_at,
            active_threshold_mode=active_mode,
            decision_threshold=decision_threshold,
            water_temper_beta=water_temper_beta,
            test=metrics.get("test") if isinstance(metrics.get("test"), dict) else {},
            test_by_threshold_mode=(
                metrics.get("test_by_threshold_mode")
                if isinstance(metrics.get("test_by_threshold_mode"), dict)
                else {}
            ),
            test_by_event=(
                metrics.get("test_by_event")
                if isinstance(metrics.get("test_by_event"), dict)
                else {}
            ),
            rolling_origin_summary=rolling_summary,
            ranking_quality=(
                metrics.get("test_ranking_quality")
                if isinstance(metrics.get("test_ranking_quality"), dict)
                else {}
            ),
            test_calibration=(
                metrics.get("test_calibration")
                if isinstance(metrics.get("test_calibration"), dict)
                else {}
            ),
            false_positive_diagnostics=(
                metrics.get("false_positive_diagnostics")
                if isinstance(metrics.get("false_positive_diagnostics"), list)
                else []
            ),
            recommendation=evaluation_recommendation(metrics),
            limitations=list(model.methodology.get("limitations", [])),
        )

    def event_prediction_index(
        self,
        event_id: str | None,
        threshold_mode: str = "conservative",
    ) -> FloodEventMlPredictionIndex:
        model = self.latest_event_model_row()
        profiles = model.metrics.get("threshold_profiles", {})
        requested_profile = profiles.get(threshold_mode, {})
        profile_threshold = requested_profile.get("threshold")
        water_temper_beta = float(requested_profile.get("water_temper_beta") or 0.0)
        if isinstance(profile_threshold, (int, float)):
            decision_threshold = float(profile_threshold)
            operating_mode = threshold_mode
        else:
            decision_threshold = model.decision_threshold
            operating_mode = "model_default"
        event_rows = self.db.execute(
            select(
                FloodEventMlPrediction.event_id,
                FloodEventMlPrediction.event_start_date,
                FloodEventMlPrediction.split,
                func.count(),
                func.count().filter(
                    FloodEventMlPrediction.flooded_fraction
                    >= model.target_threshold
                ),
            )
            .where(FloodEventMlPrediction.model_id == model.id)
            .group_by(
                FloodEventMlPrediction.event_id,
                FloodEventMlPrediction.event_start_date,
                FloodEventMlPrediction.split,
            )
            .order_by(FloodEventMlPrediction.event_start_date.desc())
        ).all()
        available = [
            FloodEventMlEventSummary(
                event_id=row[0],
                event_start_date=row[1],
                split=row[2],
                total_cells=row[3],
                observed_positive_cells=row[4],
            )
            for row in event_rows
        ]
        if not available:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "flood_event_ml_predictions_not_found",
                    "message": "The event model has no historical hindcast predictions.",
                },
            )
        selected_event = (
            next((item for item in available if item.event_id == event_id), None)
            if event_id
            else next(
                (item for item in available if item.split == "test"),
                available[0],
            )
        )
        if selected_event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "flood_event_ml_event_not_found",
                    "message": f"No hindcast predictions exist for event '{event_id}'.",
                },
            )
        predictions = self.db.scalars(
            select(FloodEventMlPrediction)
            .where(
                FloodEventMlPrediction.model_id == model.id,
                FloodEventMlPrediction.event_id == selected_event.event_id,
            )
            .order_by(FloodEventMlPrediction.probability.desc())
        ).all()
        asset_ids = [item.geo_asset_id for item in predictions]
        assets = self.db.scalars(
            select(GeoAsset).where(GeoAsset.id.in_(asset_ids))
        ).all() if asset_ids else []
        surface_water_by_id = {
            asset.id: surface_water_influence(asset.properties) for asset in assets
        }
        mean_probability = float(
            self.db.scalar(
                select(func.avg(FloodEventMlPrediction.probability)).where(
                    FloodEventMlPrediction.model_id == model.id,
                    FloodEventMlPrediction.event_id == selected_event.event_id,
                )
            )
            or 0
        )
        items: list[FloodEventMlPredictionItem] = []
        true_positive_cells = 0
        false_positive_cells = 0
        false_negative_cells = 0
        for item in predictions:
            decision_probability = temper_probability(
                item.probability,
                surface_water_by_id.get(item.geo_asset_id, 0.0),
                water_temper_beta,
            )
            predicted_label = decision_probability >= decision_threshold
            label_mode = str(model.metrics.get("label_mode") or "flood_extent")
            if label_mode == "flood_excess":
                surface = surface_water_by_id.get(item.geo_asset_id, 0.0)
                observed_positive = (
                    max(0.0, item.flooded_fraction - surface)
                    >= model.target_threshold
                )
            else:
                observed_positive = item.flooded_fraction >= model.target_threshold
            outcome = hindcast_outcome(
                predicted_label=predicted_label,
                observed_positive=observed_positive,
            )
            if outcome == "tp":
                true_positive_cells += 1
            elif outcome == "fp":
                false_positive_cells += 1
            elif outcome == "fn":
                false_negative_cells += 1
            items.append(
                FloodEventMlPredictionItem(
                    id=item.geo_asset_id,
                    probability=round(item.probability, 6),
                    predicted_label=predicted_label,
                    flooded_fraction=round(item.flooded_fraction, 6),
                    outcome=outcome,
                    decision_probability=round(decision_probability, 6),
                )
            )
        precision = (
            true_positive_cells / (true_positive_cells + false_positive_cells)
            if true_positive_cells + false_positive_cells
            else 0.0
        )
        recall = (
            true_positive_cells / (true_positive_cells + false_negative_cells)
            if true_positive_cells + false_negative_cells
            else 0.0
        )
        model_summary = to_event_model_summary(model).model_copy(
            update={
                "decision_threshold": decision_threshold,
                "operating_mode": operating_mode,
            }
        )
        return FloodEventMlPredictionIndex(
            model=model_summary,
            event=selected_event,
            available_events=available,
            items=items,
            summary=FloodEventMlPredictionSummary(
                total_cells=len(predictions),
                mean_probability=round(mean_probability, 6),
                predicted_positive_cells=true_positive_cells + false_positive_cells,
                observed_positive_cells=selected_event.observed_positive_cells,
                true_positive_cells=true_positive_cells,
                false_positive_cells=false_positive_cells,
                false_negative_cells=false_negative_cells,
                precision=round(precision, 6),
                recall=round(recall, 6),
            ),
            limitations=list(model.methodology.get("limitations", [])),
        )
