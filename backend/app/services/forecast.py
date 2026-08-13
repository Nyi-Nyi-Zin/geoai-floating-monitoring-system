"""Forecast inference service — execute flood forecast runs using the trained
event model and Open-Meteo rainfall forecast combined with ERA5 history."""

from __future__ import annotations

import json
import math
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.flood_ml import FloodEventMlModel
from app.models.forecast import ForecastPrediction, ForecastRun
from app.models.rainfall_history import RainfallHistory
from app.schemas.forecast import (
    ForecastPredictionIndex,
    ForecastPredictionItem,
    ForecastPredictionSummary,
    ForecastRunCreate,
    ForecastRunList,
    ForecastRunListItem,
    ForecastRunSummary,
    RiskBand,
)
from app.services.weather import get_rainfall_forecast

# -------------------------------------------------------------------
# Feature names must match the trained event model exactly
# -------------------------------------------------------------------
STATIC_FEATURE_NAMES = [
    "elevation_mean_m",
    "elevation_min_m",
    "elevation_max_m",
    "elevation_stddev_m",
    "elevation_percentile",
    "distance_to_waterway_m",
    "local_relief_m",
    "landcover_tree_pct",
    "landcover_shrub_pct",
    "landcover_grass_pct",
    "landcover_cropland_pct",
    "landcover_built_pct",
    "landcover_bare_pct",
    "landcover_water_pct",
    "landcover_wetland_pct",
    "landcover_mangrove_pct",
]

RAINFALL_FEATURE_NAMES = [
    "rainfall_mean_1d_mm",
    "rainfall_max_1d_mm",
    "rainfall_p90_1d_mm",
    "rainfall_accumulation_3d_mm",
    "rainfall_accumulation_7d_mm",
    "rainfall_accumulation_30d_mm",
]

ENGINEERED_FEATURE_NAMES = [
    "waterway_proximity_index",
    "surface_water_influence_pct",
    "flatness_index",
    "rainfall_7d_x_waterway_proximity",
    "rainfall_30d_x_low_elevation",
    "rainfall_3d_x_surface_water",
    "rainfall_7d_x_flatness",
    "rainfall_intensity_ratio",
]

ALL_FEATURE_NAMES = [
    *STATIC_FEATURE_NAMES,
    *RAINFALL_FEATURE_NAMES,
    *ENGINEERED_FEATURE_NAMES,
]

# SQL to load terrain cells with static features
TERRAIN_CELLS_SQL = text(
    """
    SELECT
      id AS geo_asset_id,
      name,
      properties,
      ST_X(ST_Centroid(geometry)) AS centroid_lon,
      ST_Y(ST_Centroid(geometry)) AS centroid_lat
    FROM geo_assets
    WHERE asset_type = 'terrain_cell'
    ORDER BY id
    """
)

FORECAST_LIMITATIONS = [
    "This is an experimental scenario forecast, not a validated operational warning.",
    "The underlying model has low precision (~16.6%); false alarms are common.",
    "Rainfall input is a township-level Open-Meteo weather forecast, not a rain-gauge record.",
    "Forecast rainfall accumulations beyond the forecast horizon are padded with ERA5 history.",
    "River stage, discharge, tide, upstream inflow, and drainage capacity are not modelled.",
    "Do not use this output for evacuation or life-safety decisions without field verification.",
]


# -------------------------------------------------------------------
# Pure inference helpers (no database dependency)
# -------------------------------------------------------------------

def sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -35, 35)
    return 1.0 / (1.0 + np.exp(-clipped))


def risk_band(probability: float) -> str:
    if probability < 0.25:
        return "LOW"
    if probability < 0.50:
        return "MODERATE"
    if probability < 0.75:
        return "HIGH"
    return "VERY_HIGH"


def append_engineered_features(row: dict[str, Any]) -> None:
    """Compute interaction features; mirrors scripts.build_flood_event_dataset."""
    distance_to_waterway = max(float(row["distance_to_waterway_m"]), 0.0)
    elevation_percentile = min(max(float(row["elevation_percentile"]), 0.0), 1.0)
    local_relief = max(float(row["local_relief_m"]), 0.0)
    rainfall_3d = max(float(row["rainfall_accumulation_3d_mm"]), 0.0)
    rainfall_7d = max(float(row["rainfall_accumulation_7d_mm"]), 0.0)
    rainfall_30d = max(float(row["rainfall_accumulation_30d_mm"]), 0.0)
    rainfall_max_1d = max(float(row["rainfall_max_1d_mm"]), 0.0)

    def as_fraction(value: float) -> float:
        number = float(value)
        if number > 1.0:
            number /= 100.0
        return min(1.0, max(0.0, number))

    surface_water_influence = min(
        1.0,
        as_fraction(row["landcover_water_pct"])
        + as_fraction(row["landcover_wetland_pct"])
        + as_fraction(row["landcover_mangrove_pct"]),
    )
    low_elevation_index = 1.0 - elevation_percentile
    waterway_proximity_index = 1.0 / (1.0 + distance_to_waterway / 250.0)
    flatness_index = 1.0 / (1.0 + local_relief)

    row["waterway_proximity_index"] = waterway_proximity_index
    row["surface_water_influence_pct"] = surface_water_influence
    row["flatness_index"] = flatness_index
    row["rainfall_7d_x_waterway_proximity"] = rainfall_7d * waterway_proximity_index
    row["rainfall_30d_x_low_elevation"] = rainfall_30d * low_elevation_index
    row["rainfall_3d_x_surface_water"] = rainfall_3d * surface_water_influence
    row["rainfall_7d_x_flatness"] = rainfall_7d * flatness_index
    row["rainfall_intensity_ratio"] = rainfall_max_1d / max(
        1.0, math.sqrt(rainfall_7d * max(rainfall_30d, 1.0))
    )


def derive_rainfall_features(
    target_date: date,
    forecast_daily: list[dict[str, Any]],
    historical_recent: list[dict[str, Any]],
) -> dict[str, float]:
    """Build ERA5-compatible rainfall features from forecast + history.

    Parameters
    ----------
    target_date:
        The date being forecasted.
    forecast_daily:
        Open-Meteo daily rows with keys ``date`` and ``precipitation_sum_mm``.
    historical_recent:
        Recent ERA5 history rows with ``date`` and ``mean_precipitation_mm``.
        Should cover at least 30 days before the forecast horizon start.

    Returns
    -------
    dict with the six rainfall feature names.
    """
    # Build a merged daily rainfall timeline keyed by date
    daily_rain: dict[date, float] = {}

    # Historical entries (lower priority — overwritten by forecast if overlap)
    for entry in historical_recent:
        entry_date = entry["date"]
        if isinstance(entry_date, str):
            entry_date = date.fromisoformat(entry_date)
        daily_rain[entry_date] = max(0.0, float(entry["mean_precipitation_mm"]))

    # Forecast entries (higher priority)
    for entry in forecast_daily:
        entry_date = entry["date"]
        if isinstance(entry_date, str):
            entry_date = date.fromisoformat(entry_date)
        daily_rain[entry_date] = max(0.0, float(entry["precipitation_sum_mm"]))

    # Target day rainfall
    target_1d = daily_rain.get(target_date, 0.0)

    # Accumulations: sum rainfall over N days ending on (and including) target_date
    def accumulate(days: int) -> float:
        total = 0.0
        for offset in range(days):
            day = target_date - timedelta(days=offset)
            total += daily_rain.get(day, 0.0)
        return total

    acc_3d = accumulate(3)
    acc_7d = accumulate(7)
    acc_30d = accumulate(30)

    return {
        "rainfall_mean_1d_mm": target_1d,
        "rainfall_max_1d_mm": target_1d,
        "rainfall_p90_1d_mm": target_1d,
        "rainfall_accumulation_3d_mm": acc_3d,
        "rainfall_accumulation_7d_mm": acc_7d,
        "rainfall_accumulation_30d_mm": acc_30d,
    }


def load_model_artifact(artifact_path: str) -> dict[str, Any]:
    """Load a trained model JSON artifact from disk."""
    path = Path(artifact_path)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "model_artifact_not_found",
                "message": (
                    f"Trained model artifact not found at {artifact_path}. "
                    "Retrain the event model to generate it."
                ),
            },
        )
    return json.loads(path.read_text(encoding="utf-8"))


# -------------------------------------------------------------------
# Service class
# -------------------------------------------------------------------

class ForecastService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------ model helpers ------------------------------------------

    def _latest_event_model(self) -> FloodEventMlModel:
        model = self.db.scalar(
            select(FloodEventMlModel)
            .order_by(FloodEventMlModel.trained_at.desc())
            .limit(1)
        )
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "event_model_not_found",
                    "message": (
                        "No trained flood event model is available. "
                        "Train one first with scripts.train_flood_event_model."
                    ),
                },
            )
        return model

    # ------ rainfall helpers ---------------------------------------

    def _fetch_recent_rainfall_history(
        self, before_date: date, days: int = 30
    ) -> list[dict[str, Any]]:
        """Fetch up to ``days`` of ERA5 history ending before ``before_date``."""
        start = before_date - timedelta(days=days)
        rows = self.db.scalars(
            select(RainfallHistory)
            .where(
                RainfallHistory.observed_date >= start,
                RainfallHistory.observed_date < before_date,
            )
            .order_by(RainfallHistory.observed_date)
        ).all()
        return [
            {
                "date": row.observed_date,
                "mean_precipitation_mm": row.mean_precipitation_mm,
            }
            for row in rows
        ]

    # ------ terrain cell helpers -----------------------------------

    def _load_terrain_cells(self) -> list[dict[str, Any]]:
        """Load all terrain cells with static features from PostGIS."""
        from sqlalchemy.engine import Row

        result = self.db.execute(TERRAIN_CELLS_SQL)
        cells: list[dict[str, Any]] = []
        for row in result.mappings():
            props = row["properties"] or {}
            cell: dict[str, Any] = {
                "geo_asset_id": row["geo_asset_id"],
                "name": row["name"],
                "centroid_lon": float(row["centroid_lon"]),
                "centroid_lat": float(row["centroid_lat"]),
            }
            # Extract static features from JSONB properties
            for feat in STATIC_FEATURE_NAMES:
                raw = props.get(feat)
                # land cover uses numeric code keys
                if raw is None and feat.startswith("landcover_"):
                    lc_map = {
                        "landcover_tree_pct": "10",
                        "landcover_shrub_pct": "20",
                        "landcover_grass_pct": "30",
                        "landcover_cropland_pct": "40",
                        "landcover_built_pct": "50",
                        "landcover_bare_pct": "60",
                        "landcover_water_pct": "80",
                        "landcover_wetland_pct": "90",
                        "landcover_mangrove_pct": "95",
                    }
                    code = lc_map.get(feat)
                    lc_pcts = props.get("land_cover_percentages", {})
                    raw = lc_pcts.get(code, 0) if code else 0
                value = float(raw) if raw is not None else 0.0
                if feat.startswith("landcover_") and value > 1.0:
                    value /= 100.0
                cell[feat] = value
            cells.append(cell)
        return cells

    # ------ core forecast execution --------------------------------

    def execute_forecast_run(
        self, request: ForecastRunCreate
    ) -> ForecastRunSummary:
        """Execute a complete flood forecast run and persist results."""
        now = datetime.now(UTC)

        # 1. Resolve target date (default: tomorrow)
        target = request.target_date or (now.date() + timedelta(days=1))

        # 2. Load event model and its artifact
        event_model = self._latest_event_model()
        if not event_model.artifact_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "model_artifact_path_missing",
                    "message": "The event model has no artifact_path recorded.",
                },
            )
        artifact = load_model_artifact(event_model.artifact_path)

        # 3. Resolve threshold from model threshold_profiles
        threshold_profiles = artifact.get("threshold_profiles", {})
        profile = threshold_profiles.get(request.threshold_mode, {})
        decision_threshold = (
            float(profile["threshold"])
            if isinstance(profile.get("threshold"), (int, float))
            else event_model.decision_threshold
        )
        water_temper_beta = float(profile.get("water_temper_beta") or 0.0)

        # 4. Fetch Open-Meteo forecast rainfall
        forecast_response = get_rainfall_forecast(request.forecast_days)
        forecast_daily_raw = [
            {
                "date": day.date,
                "precipitation_sum_mm": day.precipitation_sum_mm,
            }
            for day in forecast_response.daily
        ]

        # 5. Fetch recent ERA5 history for 30-day padding
        # Determine the earliest forecast day to know where history ends
        forecast_start = min(
            (d["date"] for d in forecast_daily_raw),
            default=now.date(),
        )
        historical = self._fetch_recent_rainfall_history(forecast_start, days=30)

        # 6. Derive rainfall features for the target date
        rainfall_features = derive_rainfall_features(
            target, forecast_daily_raw, historical
        )

        # 7. Load terrain cells
        cells = self._load_terrain_cells()
        if not cells:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "terrain_cells_not_found",
                    "message": "No terrain cells found in the database.",
                },
            )

        # 8. Build feature matrix and run inference
        model_mean = np.asarray(artifact["mean"], dtype=float)
        model_scale = np.asarray(artifact["scale"], dtype=float)
        model_weights = np.asarray(artifact["coefficients"], dtype=float)
        model_intercept = float(artifact["intercept"])
        feature_names = artifact["feature_names"]

        # Inject rainfall features into each cell and compute engineered features
        for cell in cells:
            cell.update(rainfall_features)
            append_engineered_features(cell)

        # Build the feature matrix in the exact feature order
        x = np.asarray(
            [[cell[feat] for feat in feature_names] for cell in cells],
            dtype=float,
        )

        # Standardize using training statistics
        standardized = (x - model_mean) / model_scale

        # Predict
        probabilities = sigmoid(standardized @ model_weights + model_intercept)
        surface_water = np.asarray(
            [float(cell.get("surface_water_influence_pct") or 0.0) for cell in cells],
            dtype=float,
        )
        decision_probabilities = np.clip(
            probabilities * (1.0 - water_temper_beta * np.clip(surface_water, 0.0, 1.0)),
            0.0,
            1.0,
        )

        # 9. Persist forecast run
        run_version = f"forecast-{now.strftime('%Y%m%dT%H%M%SZ')}"
        flagged_count = int(np.sum(decision_probabilities >= decision_threshold))
        mean_prob = float(np.mean(probabilities))

        band_counts: Counter[str] = Counter()
        for prob in probabilities:
            band_counts[risk_band(float(prob))] += 1

        summary_metrics = {
            "mean_probability": round(mean_prob, 6),
            "flagged_cell_percentage": round(
                100.0 * flagged_count / len(cells), 2
            ),
            "water_temper_beta": water_temper_beta,
            "band_counts": {
                band: band_counts.get(band, 0)
                for band in ("LOW", "MODERATE", "HIGH", "VERY_HIGH")
            },
            "rainfall_features_used": rainfall_features,
        }

        run = ForecastRun(
            run_version=run_version,
            model_id=event_model.id,
            status="completed",
            forecast_type="scenario_forecast",
            rainfall_source=f"open-meteo-{request.forecast_days}day",
            rainfall_fetched_at=forecast_response.fetched_at,
            rainfall_snapshot={
                "forecast_daily": [
                    {"date": str(d["date"]), "precipitation_sum_mm": d["precipitation_sum_mm"]}
                    for d in forecast_daily_raw
                ],
                "historical_daily_count": len(historical),
                "derived_features": {
                    key: round(val, 4) for key, val in rainfall_features.items()
                },
            },
            forecast_horizon_days=request.forecast_days,
            target_date=target,
            decision_threshold=decision_threshold,
            threshold_mode=request.threshold_mode,
            cell_count=len(cells),
            flagged_cell_count=flagged_count,
            summary_metrics=summary_metrics,
            limitations=FORECAST_LIMITATIONS,
        )
        self.db.add(run)
        self.db.flush()

        # 10. Persist per-cell predictions in batches
        batch: list[ForecastPrediction] = []
        for index, cell in enumerate(cells):
            prob = float(probabilities[index])
            decision_prob = float(decision_probabilities[index])
            prediction = ForecastPrediction(
                run_id=run.id,
                geo_asset_id=cell["geo_asset_id"],
                probability=prob,
                predicted_label=decision_prob >= decision_threshold,
                risk_band=risk_band(prob),
                features={feat: round(cell[feat], 6) for feat in feature_names},
            )
            batch.append(prediction)
            if len(batch) >= 5_000:
                self.db.add_all(batch)
                self.db.flush()
                batch.clear()
        if batch:
            self.db.add_all(batch)
        self.db.commit()

        return self._to_run_summary(run, event_model.model_version)

    # ------ query methods ------------------------------------------

    def list_runs(self, limit: int = 20) -> ForecastRunList:
        runs = self.db.scalars(
            select(ForecastRun)
            .order_by(ForecastRun.created_at.desc())
            .limit(limit)
        ).all()
        total = self.db.scalar(
            select(func.count()).select_from(ForecastRun)
        ) or 0
        return ForecastRunList(
            items=[
                ForecastRunListItem(
                    id=run.id,
                    run_version=run.run_version,
                    status=run.status,
                    target_date=run.target_date,
                    threshold_mode=run.threshold_mode,
                    cell_count=run.cell_count,
                    flagged_cell_count=run.flagged_cell_count,
                    created_at=run.created_at,
                )
                for run in runs
            ],
            total=total,
        )

    def latest_run_summary(self) -> ForecastRunSummary:
        run = self.db.scalar(
            select(ForecastRun)
            .where(ForecastRun.status == "completed")
            .order_by(ForecastRun.created_at.desc())
            .limit(1)
        )
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "forecast_run_not_found",
                    "message": "No completed forecast run is available yet.",
                },
            )
        model = self.db.scalar(
            select(FloodEventMlModel).where(FloodEventMlModel.id == run.model_id)
        )
        return self._to_run_summary(
            run, model.model_version if model else "unknown"
        )

    def get_run_predictions(
        self, run_id: str | None = None
    ) -> ForecastPredictionIndex:
        """Get predictions for a specific run or the latest completed run."""
        if run_id:
            import uuid as uuid_mod

            try:
                parsed_id = uuid_mod.UUID(run_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "invalid_run_id",
                        "message": f"'{run_id}' is not a valid UUID.",
                    },
                )
            run = self.db.scalar(
                select(ForecastRun).where(ForecastRun.id == parsed_id)
            )
        else:
            run = self.db.scalar(
                select(ForecastRun)
                .where(ForecastRun.status == "completed")
                .order_by(ForecastRun.created_at.desc())
                .limit(1)
            )
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "forecast_run_not_found",
                    "message": "No forecast run found.",
                },
            )

        model = self.db.scalar(
            select(FloodEventMlModel).where(FloodEventMlModel.id == run.model_id)
        )
        predictions = self.db.scalars(
            select(ForecastPrediction)
            .where(ForecastPrediction.run_id == run.id)
            .order_by(ForecastPrediction.probability.desc())
        ).all()

        band_counts: Counter[str] = Counter(p.risk_band for p in predictions)
        mean_prob = (
            float(
                self.db.scalar(
                    select(func.avg(ForecastPrediction.probability)).where(
                        ForecastPrediction.run_id == run.id
                    )
                )
                or 0
            )
            if predictions
            else 0.0
        )

        return ForecastPredictionIndex(
            run=self._to_run_summary(
                run, model.model_version if model else "unknown"
            ),
            items=[
                ForecastPredictionItem(
                    id=p.geo_asset_id,
                    probability=round(p.probability, 6),
                    predicted_label=p.predicted_label,
                    risk_band=p.risk_band,
                )
                for p in predictions
            ],
            summary=ForecastPredictionSummary(
                total_cells=len(predictions),
                mean_probability=round(mean_prob, 6),
                flagged_cells=sum(p.predicted_label for p in predictions),
                band_counts={
                    band: band_counts.get(band, 0)
                    for band in ("LOW", "MODERATE", "HIGH", "VERY_HIGH")
                },
            ),
            limitations=run.limitations or FORECAST_LIMITATIONS,
        )

    # ------ internal helpers ---------------------------------------

    @staticmethod
    def _to_run_summary(
        run: ForecastRun, model_version: str
    ) -> ForecastRunSummary:
        return ForecastRunSummary(
            id=run.id,
            run_version=run.run_version,
            model_id=run.model_id,
            model_version=model_version,
            status=run.status,
            forecast_type=run.forecast_type,
            rainfall_source=run.rainfall_source,
            rainfall_fetched_at=run.rainfall_fetched_at,
            forecast_horizon_days=run.forecast_horizon_days,
            target_date=run.target_date,
            decision_threshold=run.decision_threshold,
            threshold_mode=run.threshold_mode,
            cell_count=run.cell_count,
            flagged_cell_count=run.flagged_cell_count,
            summary_metrics=run.summary_metrics,
            limitations=run.limitations or FORECAST_LIMITATIONS,
            created_at=run.created_at,
        )
