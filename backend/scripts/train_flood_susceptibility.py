"""Build, evaluate, persist, and export the Maubin spatial ML baseline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import delete, select, text

from app.db.session import SessionLocal, engine
from app.models.flood_ml import FloodMlModel, FloodMlPrediction

MODEL_VERSION = "maubin-flood-susceptibility-logistic-v1"
TARGET_THRESHOLD = 0.10
FEATURE_NAMES = [
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

DATASET_SQL = text(
    """
    WITH cells AS (
      SELECT
        id,
        name,
        geometry,
        properties,
        ST_Area(geometry::geography) AS cell_area_m2,
        ST_X(ST_Centroid(geometry)) AS centroid_lon,
        ST_Y(ST_Centroid(geometry)) AS centroid_lat
      FROM geo_assets
      WHERE asset_type = 'terrain_cell'
    ),
    flood_overlap AS (
      SELECT
        c.id,
        SUM(
          ST_Area(ST_Intersection(c.geometry, f.geometry)::geography)
        ) AS flooded_area_m2,
        MAX((f.properties->>'event_count')::integer) AS event_count_max,
        SUM(
          ST_Area(ST_Intersection(c.geometry, f.geometry)::geography)
          * (f.properties->>'event_count')::double precision
        ) AS weighted_area_events
      FROM cells AS c
      JOIN flood_extents AS f ON ST_Intersects(c.geometry, f.geometry)
      GROUP BY c.id
    )
    SELECT
      c.id AS geo_asset_id,
      c.name,
      c.centroid_lon,
      c.centroid_lat,
      LEAST(1.0, GREATEST(0.0,
        COALESCE(o.flooded_area_m2 / NULLIF(c.cell_area_m2, 0), 0)
      )) AS flooded_fraction,
      COALESCE(o.event_count_max, 0) AS historical_event_count,
      GREATEST(0.0,
        COALESCE(o.weighted_area_events / NULLIF(c.cell_area_m2, 0), 0)
      ) AS historical_event_density,
      (c.properties->>'elevation_mean_m')::double precision AS elevation_mean_m,
      (c.properties->>'elevation_min_m')::double precision AS elevation_min_m,
      (c.properties->>'elevation_max_m')::double precision AS elevation_max_m,
      COALESCE((c.properties->>'elevation_stddev_m')::double precision, 0) AS elevation_stddev_m,
      (c.properties->>'elevation_percentile')::double precision AS elevation_percentile,
      (c.properties->>'distance_to_waterway_m')::double precision AS distance_to_waterway_m,
      (c.properties->>'local_relief_m')::double precision AS local_relief_m,
      COALESCE((c.properties->'land_cover_percentages'->>'10')::double precision, 0) AS landcover_tree_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'20')::double precision, 0) AS landcover_shrub_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'30')::double precision, 0) AS landcover_grass_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'40')::double precision, 0) AS landcover_cropland_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'50')::double precision, 0) AS landcover_built_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'60')::double precision, 0) AS landcover_bare_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'80')::double precision, 0) AS landcover_water_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'90')::double precision, 0) AS landcover_wetland_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'95')::double precision, 0) AS landcover_mangrove_pct
    FROM cells AS c
    LEFT JOIN flood_overlap AS o ON o.id = c.id
    ORDER BY c.id
    """
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train the sensor-independent Maubin flood susceptibility baseline."
    )
    parser.add_argument("--model-version", default=MODEL_VERSION)
    parser.add_argument("--target-threshold", type=float, default=TARGET_THRESHOLD)
    parser.add_argument(
        "--dataset-output",
        type=Path,
        default=Path("data/derived/maubin_flood_ml_dataset_v1.csv"),
    )
    parser.add_argument(
        "--artifact-output",
        type=Path,
        default=Path("artifacts/maubin_flood_susceptibility_logistic_v1.json"),
    )
    parser.add_argument("--iterations", type=int, default=3000)
    parser.add_argument("--learning-rate", type=float, default=0.03)
    parser.add_argument("--l2", type=float, default=0.01)
    return parser.parse_args()


def load_dataset() -> list[dict[str, Any]]:
    if engine is None:
        raise RuntimeError("DATABASE_URL is required")
    with engine.connect() as connection:
        rows = [dict(row) for row in connection.execute(DATASET_SQL).mappings()]
    if not rows:
        raise RuntimeError("No terrain cells are available")
    for row in rows:
        for feature in FEATURE_NAMES:
            value = row.get(feature)
            if value is None or not math.isfinite(float(value)):
                raise ValueError(
                    f"Terrain cell {row['geo_asset_id']} has invalid feature {feature}"
                )
            row[feature] = float(value)
        row["flooded_fraction"] = float(row["flooded_fraction"])
        row["historical_event_count"] = int(row["historical_event_count"])
        row["historical_event_density"] = float(row["historical_event_density"])
    return rows


def spatial_split(longitude: float, latitude: float) -> str:
    block = f"{math.floor(longitude / 0.04)}:{math.floor(latitude / 0.04)}"
    bucket = int(hashlib.sha256(block.encode()).hexdigest()[:8], 16) % 10
    if bucket <= 1:
        return "test"
    if bucket == 2:
        return "validation"
    return "train"


def sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -35, 35)
    return 1.0 / (1.0 + np.exp(-clipped))


def fit_logistic(
    x: np.ndarray,
    y: np.ndarray,
    *,
    iterations: int,
    learning_rate: float,
    l2: float,
    positive_weight_scale: float = 1.0,
) -> tuple[np.ndarray, float]:
    if set(np.unique(y)) != {0.0, 1.0}:
        raise ValueError("Training split must contain both target classes")
    if positive_weight_scale <= 0:
        raise ValueError("positive_weight_scale must be > 0")
    weights = np.zeros(x.shape[1], dtype=float)
    intercept = 0.0
    # Scale < 1 down-weights flooded cells and usually reduces false alarms.
    positive_weight = (len(y) / (2 * float(np.sum(y)))) * positive_weight_scale
    negative_weight = len(y) / (2 * float(np.sum(1 - y)))
    sample_weights = np.where(y == 1, positive_weight, negative_weight)
    normalizer = float(np.sum(sample_weights))

    for iteration in range(iterations):
        probabilities = sigmoid(x @ weights + intercept)
        error = (probabilities - y) * sample_weights
        gradient = (x.T @ error) / normalizer + l2 * weights
        intercept_gradient = float(np.sum(error) / normalizer)
        step = learning_rate / math.sqrt(1 + iteration / 500)
        weights -= step * gradient
        intercept -= step * intercept_gradient
    return weights, intercept


def roc_auc(y: np.ndarray, probability: np.ndarray) -> float:
    positives = int(np.sum(y == 1))
    negatives = int(np.sum(y == 0))
    if not positives or not negatives:
        return 0.0
    order = np.argsort(probability)
    ranks = np.empty(len(probability), dtype=float)
    position = 0
    while position < len(order):
        end = position + 1
        while end < len(order) and probability[order[end]] == probability[order[position]]:
            end += 1
        ranks[order[position:end]] = (position + 1 + end) / 2
        position = end
    positive_rank_sum = float(np.sum(ranks[y == 1]))
    return (positive_rank_sum - positives * (positives + 1) / 2) / (
        positives * negatives
    )


def average_precision(y: np.ndarray, probability: np.ndarray) -> float:
    positives = int(np.sum(y == 1))
    if not positives:
        return 0.0
    ordered_y = y[np.argsort(-probability)]
    cumulative = np.cumsum(ordered_y)
    precision = cumulative / np.arange(1, len(y) + 1)
    return float(np.sum(precision * ordered_y) / positives)


def evaluate(
    y: np.ndarray, probability: np.ndarray, threshold: float = 0.5
) -> dict[str, Any]:
    predicted = probability >= threshold
    truth = y == 1
    tp = int(np.sum(predicted & truth))
    tn = int(np.sum(~predicted & ~truth))
    fp = int(np.sum(predicted & ~truth))
    fn = int(np.sum(~predicted & truth))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "rows": len(y),
        "positives": int(np.sum(truth)),
        "negatives": int(np.sum(~truth)),
        "accuracy": round((tp + tn) / len(y), 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(2 * precision * recall / (precision + recall), 4)
        if precision + recall
        else 0.0,
        "roc_auc": round(roc_auc(y, probability), 4),
        "pr_auc": round(average_precision(y, probability), 4),
        "brier_score": round(float(np.mean((probability - y) ** 2)), 4),
        "decision_threshold": round(threshold, 4),
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    }


def risk_band(probability: float) -> str:
    if probability < 0.25:
        return "LOW"
    if probability < 0.50:
        return "MODERATE"
    if probability < 0.75:
        return "HIGH"
    return "VERY_HIGH"


def export_dataset(
    rows: list[dict[str, Any]],
    path: Path,
    target_threshold: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "geo_asset_id",
        "name",
        "centroid_lon",
        "centroid_lat",
        *FEATURE_NAMES,
        "flooded_fraction",
        "historical_event_count",
        "historical_event_density",
        "target_label",
        "spatial_split",
    ]
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **{field: row[field] for field in fields if field in row},
                    "target_label": int(row["flooded_fraction"] >= target_threshold),
                    "spatial_split": spatial_split(
                        float(row["centroid_lon"]), float(row["centroid_lat"])
                    ),
                }
            )


def persist(
    *,
    rows: list[dict[str, Any]],
    probabilities: np.ndarray,
    feature_matrix_standardized: np.ndarray,
    coefficients: np.ndarray,
    model_version: str,
    target_threshold: float,
    metrics: dict[str, Any],
    feature_importance: dict[str, float],
    artifact_path: Path,
    hyperparameters: dict[str, float | int],
) -> uuid.UUID:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is required")
    labels = np.array(
        [row["flooded_fraction"] >= target_threshold for row in rows], dtype=bool
    )
    db = SessionLocal()
    try:
        model = db.scalar(
            select(FloodMlModel).where(FloodMlModel.model_version == model_version)
        )
        if model is None:
            model = FloodMlModel(model_version=model_version)
            db.add(model)
        model.algorithm = "NumPy regularized logistic regression"
        model.status = "trained"
        model.target_name = (
            f"historical_flooded_fraction_gte_{target_threshold:.2f}"
            .replace(".", "_")
        )
        model.target_threshold = target_threshold
        model.training_rows = len(rows)
        model.positive_rows = int(np.sum(labels))
        model.negative_rows = int(np.sum(~labels))
        model.feature_names = FEATURE_NAMES
        model.metrics = metrics
        model.feature_importance = feature_importance
        model.methodology = {
            "dataset": "Maubin 500 m terrain cells",
            "label_source": "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1 frequency composite 2000-2018",
            "label_definition": f"flooded_fraction >= {target_threshold}",
            "split": "deterministic 0.04-degree spatial blocks",
            "features": "30 m DEM aggregates, OSM waterway proximity, ESA WorldCover 2021 shares",
            "rainfall_excluded": "Township rainfall is spatially constant and is not aligned to individual GFD events.",
            "operational_forecast": False,
            "hyperparameters": hyperparameters,
            "limitations": [
                "Historical susceptibility is not a live flood forecast.",
                "The label source is a MODIS-derived frequency composite and is not field validated.",
                "WorldCover 2021 post-dates some historical flood observations.",
                "Spatial autocorrelation may still inflate holdout metrics.",
            ],
        }
        model.artifact_path = artifact_path.as_posix()
        model.trained_at = datetime.now(UTC)
        db.flush()
        db.execute(delete(FloodMlPrediction).where(FloodMlPrediction.model_id == model.id))

        predictions = []
        for index, row in enumerate(rows):
            cell_contributions = feature_matrix_standardized[index] * coefficients
            importance_order = np.argsort(-np.abs(cell_contributions))[:3]
            contributions = [
                {
                    "feature": FEATURE_NAMES[position],
                    "standardized_value": round(
                        float(feature_matrix_standardized[index, position]), 4
                    ),
                    "contribution": round(
                        float(
                            feature_matrix_standardized[index, position]
                            * coefficients[position]
                        ),
                        4,
                    ),
                }
                for position in importance_order
            ]
            probability = float(probabilities[index])
            predictions.append(
                FloodMlPrediction(
                    model_id=model.id,
                    geo_asset_id=row["geo_asset_id"],
                    probability=probability,
                    risk_band=risk_band(probability),
                    predicted_label=probability >= 0.5,
                    flooded_fraction=row["flooded_fraction"],
                    historical_event_count=row["historical_event_count"],
                    historical_event_density=row["historical_event_density"],
                    features={name: row[name] for name in FEATURE_NAMES},
                    explanation={"top_linear_contributions": contributions},
                )
            )
        db.add_all(predictions)
        db.commit()
        return model.id
    finally:
        db.close()


def main() -> None:
    args = parse_args()
    if not 0 < args.target_threshold < 1:
        raise ValueError("target-threshold must be between 0 and 1")
    rows = load_dataset()
    export_dataset(rows, args.dataset_output, args.target_threshold)

    x = np.asarray([[row[name] for name in FEATURE_NAMES] for row in rows], dtype=float)
    y = np.asarray(
        [row["flooded_fraction"] >= args.target_threshold for row in rows],
        dtype=float,
    )
    splits = np.asarray(
        [
            spatial_split(float(row["centroid_lon"]), float(row["centroid_lat"]))
            for row in rows
        ]
    )
    train_mask = splits == "train"
    validation_mask = splits == "validation"
    test_mask = splits == "test"
    mean = np.mean(x[train_mask], axis=0)
    scale = np.std(x[train_mask], axis=0)
    scale[scale < 1e-9] = 1.0
    standardized = (x - mean) / scale

    evaluation_coefficients, evaluation_intercept = fit_logistic(
        standardized[train_mask],
        y[train_mask],
        iterations=args.iterations,
        learning_rate=args.learning_rate,
        l2=args.l2,
    )
    validation_probability = sigmoid(
        standardized[validation_mask] @ evaluation_coefficients
        + evaluation_intercept
    )
    test_probability = sigmoid(
        standardized[test_mask] @ evaluation_coefficients + evaluation_intercept
    )
    metrics = {
        "validation": evaluate(y[validation_mask], validation_probability),
        "test": evaluate(y[test_mask], test_probability),
        "split_counts": {
            "train": int(np.sum(train_mask)),
            "validation": int(np.sum(validation_mask)),
            "test": int(np.sum(test_mask)),
        },
    }

    full_mean = np.mean(x, axis=0)
    full_scale = np.std(x, axis=0)
    full_scale[full_scale < 1e-9] = 1.0
    full_standardized = (x - full_mean) / full_scale
    final_coefficients, final_intercept = fit_logistic(
        full_standardized,
        y,
        iterations=args.iterations,
        learning_rate=args.learning_rate,
        l2=args.l2,
    )
    probabilities = sigmoid(full_standardized @ final_coefficients + final_intercept)
    absolute = np.abs(final_coefficients)
    importance = absolute / float(np.sum(absolute)) if np.sum(absolute) else absolute
    feature_importance = {
        name: round(float(value), 6)
        for name, value in sorted(
            zip(FEATURE_NAMES, importance, strict=True),
            key=lambda item: -item[1],
        )
    }

    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "model_version": args.model_version,
        "algorithm": "NumPy regularized logistic regression",
        "feature_names": FEATURE_NAMES,
        "mean": full_mean.tolist(),
        "scale": full_scale.tolist(),
        "coefficients": final_coefficients.tolist(),
        "intercept": final_intercept,
        "target_threshold": args.target_threshold,
        "risk_thresholds": {"LOW": 0.25, "MODERATE": 0.5, "HIGH": 0.75},
        "hyperparameters": {
            "iterations": args.iterations,
            "learning_rate": args.learning_rate,
            "l2": args.l2,
        },
        "metrics": metrics,
        "trained_at": datetime.now(UTC).isoformat(),
    }
    args.artifact_output.write_text(
        json.dumps(artifact, indent=2), encoding="utf-8"
    )
    model_id = persist(
        rows=rows,
        probabilities=probabilities,
        feature_matrix_standardized=full_standardized,
        coefficients=final_coefficients,
        model_version=args.model_version,
        target_threshold=args.target_threshold,
        metrics=metrics,
        feature_importance=feature_importance,
        artifact_path=args.artifact_output,
        hyperparameters={
            "iterations": args.iterations,
            "learning_rate": args.learning_rate,
            "l2": args.l2,
        },
    )
    print(
        json.dumps(
            {
                "model_id": str(model_id),
                "model_version": args.model_version,
                "rows": len(rows),
                "positive_rows": int(np.sum(y)),
                "negative_rows": int(np.sum(1 - y)),
                "metrics": metrics,
                "top_features": list(feature_importance.items())[:8],
                "dataset": str(args.dataset_output),
                "artifact": str(args.artifact_output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
