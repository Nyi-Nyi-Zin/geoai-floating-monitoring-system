"""Train a rainfall-aligned baseline evaluated on future held-out events."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.flood_ml import FloodEventMlModel, FloodEventMlPrediction
from scripts.build_flood_event_dataset import (
    FEATURE_NAMES,
    event_target_label,
    export_event_dataset,
    load_event_dataset,
    temporal_split_map,
)
from scripts.train_flood_susceptibility import evaluate, fit_logistic, sigmoid

MODEL_VERSION = "maubin-flood-event-logistic-v5"
THRESHOLD_MODES = ("screening", "balanced", "conservative")
WATER_TEMPER_CANDIDATES = tuple(round(value, 2) for value in np.linspace(0.0, 0.80, 9))


def temper_probabilities(
    probability: np.ndarray,
    surface_water: np.ndarray,
    beta: float,
) -> np.ndarray:
    """Down-weight permanent-water cells before applying an alert threshold.

    Permanent water / wetland cells are a common false-alarm source because the
    model learns "water looks flooded". Tempering keeps raw probabilities for
    ranking/calibration while making alert decisions more conservative there.
    """
    tempered = probability * (1.0 - float(beta) * np.clip(surface_water, 0.0, 1.0))
    return np.clip(tempered, 0.0, 1.0)


def _score_threshold_candidates(
    truth: np.ndarray,
    probability: np.ndarray,
) -> list[tuple[float, dict[str, Any]]]:
    candidates = np.linspace(0.05, 0.95, 91)
    return [
        (float(threshold), evaluate(truth, probability, float(threshold)))
        for threshold in candidates
    ]


def select_decision_threshold(
    truth: np.ndarray, probability: np.ndarray
) -> tuple[float, dict[str, Any]]:
    scored = _score_threshold_candidates(truth, probability)
    threshold, metrics = max(
        scored,
        key=lambda item: (
            float(item[1]["f1"]),
            float(item[1]["precision"]),
            -abs(item[0] - 0.5),
        ),
    )
    return round(threshold, 4), metrics


def select_precision_threshold(
    truth: np.ndarray,
    probability: np.ndarray,
    minimum_recall: float = 0.20,
) -> tuple[float, dict[str, Any]]:
    """Select the highest-validation-precision threshold with useful recall.

    The recall floor prevents the degenerate solution where a threshold predicts
    only one easy positive. Both selection and the constraint use validation data
    only; test data remains untouched until final evaluation.
    """
    scored = _score_threshold_candidates(truth, probability)
    eligible = [
        item
        for item in scored
        if float(item[1]["recall"]) >= minimum_recall
        and (
            int(item[1]["confusion_matrix"]["tp"])
            + int(item[1]["confusion_matrix"]["fp"])
            > 0
        )
    ]
    if not eligible:
        return select_decision_threshold(truth, probability)
    threshold, metrics = max(
        eligible,
        key=lambda item: (
            float(item[1]["precision"]),
            float(item[1]["f1"]),
            float(item[0]),
        ),
    )
    return round(threshold, 4), metrics


def select_screening_threshold(
    truth: np.ndarray,
    probability: np.ndarray,
    minimum_precision: float = 0.10,
) -> tuple[float, dict[str, Any]]:
    """Select a higher-recall screening threshold without collapsing to noise."""
    scored = _score_threshold_candidates(truth, probability)
    eligible = [
        item
        for item in scored
        if float(item[1]["precision"]) >= minimum_precision
        and (
            int(item[1]["confusion_matrix"]["tp"])
            + int(item[1]["confusion_matrix"]["fp"])
            > 0
        )
    ]
    if not eligible:
        return select_decision_threshold(truth, probability)
    threshold, metrics = max(
        eligible,
        key=lambda item: (
            float(item[1]["recall"]),
            float(item[1]["f1"]),
            -float(item[0]),
        ),
    )
    return round(threshold, 4), metrics


def select_threshold_profile(
    truth: np.ndarray,
    probability: np.ndarray,
    surface_water: np.ndarray,
    mode: str,
    *,
    minimum_screening_precision: float,
    minimum_conservative_recall: float,
) -> dict[str, Any]:
    """Choose threshold and permanent-water temper jointly on validation data."""
    best: dict[str, Any] | None = None
    for beta in WATER_TEMPER_CANDIDATES:
        tempered = temper_probabilities(probability, surface_water, beta)
        if mode == "screening":
            threshold, metrics = select_screening_threshold(
                truth, tempered, minimum_screening_precision
            )
            rank = (
                float(metrics["recall"]),
                float(metrics["f1"]),
                float(metrics["precision"]),
                -beta,
            )
        elif mode == "conservative":
            threshold, metrics = select_precision_threshold(
                truth, tempered, minimum_conservative_recall
            )
            rank = (
                float(metrics["precision"]),
                float(metrics["f1"]),
                float(metrics["recall"]),
                beta,
            )
        else:
            threshold, metrics = select_decision_threshold(truth, tempered)
            rank = (
                float(metrics["f1"]),
                float(metrics["precision"]),
                float(metrics["recall"]),
                -abs(beta - 0.3),
            )
        candidate = {
            "threshold": threshold,
            "water_temper_beta": float(beta),
            "validation": metrics,
            "rank": rank,
        }
        if best is None or candidate["rank"] > best["rank"]:
            best = candidate
    assert best is not None
    best.pop("rank")
    return best


def calibration_report(
    truth: np.ndarray,
    probability: np.ndarray,
    bins: int = 10,
) -> dict[str, Any]:
    """Summarize how well predicted probabilities match observed event rates."""
    edges = np.linspace(0.0, 1.0, bins + 1)
    reliability_curve: list[dict[str, Any]] = []
    expected_calibration_error = 0.0
    maximum_calibration_error = 0.0
    total = max(1, len(truth))

    for index in range(bins):
        lower = float(edges[index])
        upper = float(edges[index + 1])
        if index == bins - 1:
            mask = (probability >= lower) & (probability <= upper)
        else:
            mask = (probability >= lower) & (probability < upper)
        count = int(np.sum(mask))
        if not count:
            continue
        mean_probability = float(np.mean(probability[mask]))
        observed_rate = float(np.mean(truth[mask]))
        gap = mean_probability - observed_rate
        absolute_gap = abs(gap)
        expected_calibration_error += (count / total) * absolute_gap
        maximum_calibration_error = max(maximum_calibration_error, absolute_gap)
        reliability_curve.append(
            {
                "bin_lower": round(lower, 4),
                "bin_upper": round(upper, 4),
                "count": count,
                "mean_probability": round(mean_probability, 4),
                "observed_rate": round(observed_rate, 4),
                "gap": round(gap, 4),
            }
        )

    return {
        "rows": len(truth),
        "positives": int(np.sum(truth)),
        "base_rate": round(float(np.mean(truth)) if len(truth) else 0.0, 4),
        "expected_calibration_error": round(expected_calibration_error, 4),
        "maximum_calibration_error": round(maximum_calibration_error, 4),
        "reliability_curve": reliability_curve,
    }


def ranking_diagnostics(
    truth: np.ndarray,
    probability: np.ndarray,
    fractions: tuple[float, ...] = (0.01, 0.05, 0.10),
) -> dict[str, dict[str, float | int]]:
    ordered = np.argsort(-probability)
    total_positives = max(1, int(np.sum(truth)))
    diagnostics: dict[str, dict[str, float | int]] = {}
    for fraction in fractions:
        count = max(1, int(np.ceil(len(truth) * fraction)))
        selected = ordered[:count]
        true_positives = int(np.sum(truth[selected]))
        diagnostics[f"top_{int(fraction * 100)}pct"] = {
            "cells": count,
            "true_positive_cells": true_positives,
            "precision": round(true_positives / count, 4),
            "recall": round(true_positives / total_positives, 4),
        }
    return diagnostics


def rolling_origin_cross_validation(
    rows: list[dict[str, Any]],
    x: np.ndarray,
    y: np.ndarray,
    *,
    iterations: int,
    learning_rate: float,
    l2: float,
    positive_weight_scale: float,
    minimum_screening_precision: float,
    minimum_conservative_recall: float,
) -> dict[str, Any]:
    """Retrain across chronological folds to expose event-order sensitivity."""
    ordered_events = sorted(
        {(row["event_id"], row["event_start_date"]) for row in rows},
        key=lambda item: (item[1], item[0]),
    )
    event_ids = np.asarray([row["event_id"] for row in rows])
    surface_water = np.asarray(
        [row["surface_water_influence_pct"] for row in rows], dtype=float
    )
    folds: list[dict[str, Any]] = []

    for validation_index in range(2, len(ordered_events) - 1):
        train_events = [event_id for event_id, _ in ordered_events[:validation_index]]
        validation_event, validation_date = ordered_events[validation_index]
        test_event, test_date = ordered_events[validation_index + 1]
        train = np.isin(event_ids, train_events)
        validation = event_ids == validation_event
        test = event_ids == test_event
        if len(np.unique(y[train])) < 2:
            continue

        mean = np.mean(x[train], axis=0)
        scale = np.std(x[train], axis=0)
        scale[scale < 1e-9] = 1.0
        standardized = (x - mean) / scale
        weights, intercept = fit_logistic(
            standardized[train],
            y[train],
            iterations=iterations,
            learning_rate=learning_rate,
            l2=l2,
            positive_weight_scale=positive_weight_scale,
        )
        probabilities = sigmoid(standardized @ weights + intercept)
        profiles = {
            mode: select_threshold_profile(
                y[validation],
                probabilities[validation],
                surface_water[validation],
                mode,
                minimum_screening_precision=minimum_screening_precision,
                minimum_conservative_recall=minimum_conservative_recall,
            )
            for mode in THRESHOLD_MODES
        }
        folds.append(
            {
                "train_event_count": len(train_events),
                "train_until_event_id": train_events[-1],
                "validation_event_id": validation_event,
                "validation_event_start_date": str(validation_date),
                "test_event_id": test_event,
                "test_event_start_date": str(test_date),
                "test_rows": int(np.sum(test)),
                "test_positive_rows": int(np.sum(y[test])),
                "threshold_profiles": {
                    mode: {
                        "threshold": profile["threshold"],
                        "water_temper_beta": profile["water_temper_beta"],
                        "validation": profile["validation"],
                    }
                    for mode, profile in profiles.items()
                },
                "test": {
                    mode: evaluate(
                        y[test],
                        temper_probabilities(
                            probabilities[test],
                            surface_water[test],
                            float(profile["water_temper_beta"]),
                        ),
                        float(profile["threshold"]),
                    )
                    for mode, profile in profiles.items()
                },
            }
        )

    summary = {
        mode: {
            "folds": len(folds),
            "mean_precision": round(
                float(np.mean([fold["test"][mode]["precision"] for fold in folds])), 4
            )
            if folds
            else 0.0,
            "mean_recall": round(
                float(np.mean([fold["test"][mode]["recall"] for fold in folds])), 4
            )
            if folds
            else 0.0,
            "mean_f1": round(float(np.mean([fold["test"][mode]["f1"] for fold in folds])), 4)
            if folds
            else 0.0,
            "mean_pr_auc": round(
                float(np.mean([fold["test"][mode]["pr_auc"] for fold in folds])), 4
            )
            if folds
            else 0.0,
            "precision_std": round(
                float(np.std([fold["test"][mode]["precision"] for fold in folds])), 4
            )
            if folds
            else 0.0,
            "recall_std": round(
                float(np.std([fold["test"][mode]["recall"] for fold in folds])), 4
            )
            if folds
            else 0.0,
        }
        for mode in THRESHOLD_MODES
    }
    return {"folds": folds, "summary": summary}


def event_metrics(
    rows: list[dict[str, Any]],
    mask: np.ndarray,
    labels: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, dict[str, Any]]:
    """Report performance per held-out event so weak events stay visible."""
    event_ids = np.asarray([row["event_id"] for row in rows])
    result: dict[str, dict[str, Any]] = {}
    for event_id in sorted(set(event_ids[mask])):
        event_mask = mask & (event_ids == event_id)
        metrics = evaluate(labels[event_mask], probabilities[event_mask], threshold)
        result[str(event_id)] = {
            **metrics,
            "event_start_date": str(
                next(row["event_start_date"] for row in rows if row["event_id"] == event_id)
            ),
            "predicted_area_error_cells": (
                int(metrics["confusion_matrix"]["tp"])
                + int(metrics["confusion_matrix"]["fp"])
                - int(metrics["positives"])
            ),
        }
    return result


def false_positive_diagnostics(
    rows: list[dict[str, Any]],
    mask: np.ndarray,
    labels: np.ndarray,
    probabilities: np.ndarray,
    decision_probabilities: np.ndarray,
    threshold: float,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Keep a compact, mappable sample of the strongest false alarms."""
    indexes = np.flatnonzero(
        mask & (labels == 0) & (decision_probabilities >= threshold)
    )
    ordered = sorted(indexes, key=lambda index: -float(decision_probabilities[index]))[
        :limit
    ]
    return [
        {
            "event_id": rows[index]["event_id"],
            "geo_asset_id": str(rows[index]["geo_asset_id"]),
            "probability": round(float(probabilities[index]), 6),
            "decision_probability": round(float(decision_probabilities[index]), 6),
            "flooded_fraction": round(float(rows[index]["flooded_fraction"]), 6),
            "centroid_lon": float(rows[index]["centroid_lon"]),
            "centroid_lat": float(rows[index]["centroid_lat"]),
            "distance_to_waterway_m": round(
                float(rows[index]["distance_to_waterway_m"]), 2
            ),
            "surface_water_influence_pct": round(
                float(rows[index]["surface_water_influence_pct"]), 4
            ),
            "landcover_water_pct": round(float(rows[index]["landcover_water_pct"]), 4),
            "landcover_wetland_pct": round(
                float(rows[index]["landcover_wetland_pct"]), 4
            ),
            "landcover_mangrove_pct": round(
                float(rows[index]["landcover_mangrove_pct"]), 4
            ),
        }
        for index in ordered
    ]


def persist_event_model(
    *,
    rows: list[dict[str, Any]],
    splits: np.ndarray,
    probabilities: np.ndarray,
    labels: np.ndarray,
    model_version: str,
    target_threshold: float,
    decision_threshold: float,
    metrics: dict[str, Any],
    feature_importance: dict[str, float],
    split_events: dict[str, list[str]],
    methodology: dict[str, Any],
    artifact_path: Path,
    decision_probabilities: np.ndarray | None = None,
) -> str:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is required")
    alert_scores = (
        decision_probabilities if decision_probabilities is not None else probabilities
    )
    db = SessionLocal()
    try:
        model = db.scalar(
            select(FloodEventMlModel).where(
                FloodEventMlModel.model_version == model_version
            )
        )
        if model is None:
            model = FloodEventMlModel(model_version=model_version)
            db.add(model)
        model.algorithm = "NumPy regularized logistic regression"
        model.status = "experimental"
        model.target_name = "event_cell_flooded_fraction"
        model.target_threshold = target_threshold
        model.decision_threshold = decision_threshold
        model.dataset_rows = len(rows)
        model.train_rows = int(np.sum(splits == "train"))
        model.positive_rows = int(np.sum(labels))
        model.negative_rows = int(len(labels) - np.sum(labels))
        model.event_count = len({row["event_id"] for row in rows})
        model.feature_names = FEATURE_NAMES
        model.metrics = metrics
        model.feature_importance = feature_importance
        model.split_events = split_events
        model.methodology = methodology
        model.artifact_path = artifact_path.as_posix()
        model.trained_at = datetime.now(UTC)
        db.flush()
        db.execute(
            delete(FloodEventMlPrediction).where(
                FloodEventMlPrediction.model_id == model.id
            )
        )
        batch: list[FloodEventMlPrediction] = []
        for index, row in enumerate(rows):
            split = str(splits[index])
            if split == "train":
                continue
            probability = float(probabilities[index])
            batch.append(
                FloodEventMlPrediction(
                    model_id=model.id,
                    event_id=row["event_id"],
                    event_start_date=row["event_start_date"],
                    split=split,
                    geo_asset_id=row["geo_asset_id"],
                    probability=probability,
                    predicted_label=float(alert_scores[index]) >= decision_threshold,
                    flooded_fraction=row["flooded_fraction"],
                )
            )
            if len(batch) >= 5_000:
                db.add_all(batch)
                db.flush()
                batch.clear()
        if batch:
            db.add_all(batch)
        db.commit()
        return str(model.id)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset-output",
        type=Path,
        default=Path("data/derived/maubin_flood_event_dataset_v1.csv"),
    )
    parser.add_argument(
        "--artifact-output",
        type=Path,
        default=Path("artifacts/maubin_flood_event_logistic_v5.json"),
    )
    parser.add_argument("--model-version", default=MODEL_VERSION)
    parser.add_argument("--target-threshold", type=float, default=0.10)
    parser.add_argument("--iterations", type=int, default=3000)
    parser.add_argument("--learning-rate", type=float, default=0.03)
    parser.add_argument("--l2", type=float, default=0.01)
    parser.add_argument(
        "--positive-weight-scale",
        type=float,
        default=1.0,
        help=(
            "Multiplier on positive-class sample weight during training. "
            "Values below 1.0 usually reduce false alarms."
        ),
    )
    parser.add_argument(
        "--label-mode",
        choices=("flood_excess", "flood_extent"),
        default="flood_excess",
        help=(
            "flood_excess labels new inundation beyond permanent water cover; "
            "flood_extent uses raw flooded fraction."
        ),
    )
    parser.add_argument(
        "--threshold-mode",
        choices=THRESHOLD_MODES,
        default="conservative",
        help="Operating threshold persisted as the model default.",
    )
    parser.add_argument(
        "--minimum-screening-precision",
        type=float,
        default=0.10,
        help="Validation precision floor for high-recall screening threshold selection.",
    )
    parser.add_argument(
        "--minimum-conservative-recall",
        type=float,
        default=0.20,
        help="Validation recall floor for precision-first threshold selection.",
    )
    args = parser.parse_args()
    if not 0 < args.minimum_screening_precision <= 1:
        raise ValueError("minimum-screening-precision must be in (0, 1]")
    if not 0 < args.minimum_conservative_recall <= 1:
        raise ValueError("minimum-conservative-recall must be in (0, 1]")
    if args.positive_weight_scale <= 0:
        raise ValueError("positive-weight-scale must be > 0")

    rows = load_event_dataset()
    split_map = temporal_split_map(
        [(row["event_id"], row["event_start_date"]) for row in rows]
    )
    export_event_dataset(
        rows,
        args.dataset_output,
        args.target_threshold,
        label_mode=args.label_mode,
    )
    x = np.asarray([[row[name] for name in FEATURE_NAMES] for row in rows], dtype=float)
    y = np.asarray(
        [
            event_target_label(
                row, args.target_threshold, label_mode=args.label_mode
            )
            for row in rows
        ],
        dtype=float,
    )
    surface_water = np.asarray(
        [row["surface_water_influence_pct"] for row in rows], dtype=float
    )
    splits = np.asarray([split_map[row["event_id"]] for row in rows])
    train = splits == "train"
    validation = splits == "validation"
    test = splits == "test"
    mean = np.mean(x[train], axis=0)
    scale = np.std(x[train], axis=0)
    scale[scale < 1e-9] = 1.0
    standardized = (x - mean) / scale
    weights, intercept = fit_logistic(
        standardized[train],
        y[train],
        iterations=args.iterations,
        learning_rate=args.learning_rate,
        l2=args.l2,
        positive_weight_scale=args.positive_weight_scale,
    )
    probabilities = sigmoid(standardized @ weights + intercept)
    selection_objectives = {
        "screening": (
            "maximum validation recall subject to precision >= "
            f"{args.minimum_screening_precision:.2f}; "
            "joint permanent-water temper selection"
        ),
        "balanced": (
            "maximum validation F1 with joint permanent-water temper selection"
        ),
        "conservative": (
            "maximum validation precision subject to recall >= "
            f"{args.minimum_conservative_recall:.2f}; "
            "joint permanent-water temper selection"
        ),
    }
    threshold_profiles = {
        mode: {
            **select_threshold_profile(
                y[validation],
                probabilities[validation],
                surface_water[validation],
                mode,
                minimum_screening_precision=args.minimum_screening_precision,
                minimum_conservative_recall=args.minimum_conservative_recall,
            ),
            "selection_objective": selection_objectives[mode],
        }
        for mode in THRESHOLD_MODES
    }
    active_profile = threshold_profiles[args.threshold_mode]
    decision_threshold = float(active_profile["threshold"])
    water_temper_beta = float(active_profile["water_temper_beta"])
    decision_probabilities = temper_probabilities(
        probabilities, surface_water, water_temper_beta
    )
    rolling_origin = rolling_origin_cross_validation(
        rows,
        x,
        y,
        iterations=args.iterations,
        learning_rate=args.learning_rate,
        l2=args.l2,
        positive_weight_scale=args.positive_weight_scale,
        minimum_screening_precision=args.minimum_screening_precision,
        minimum_conservative_recall=args.minimum_conservative_recall,
    )
    split_events = {
        name: sorted(event_id for event_id, split in split_map.items() if split == name)
        for name in ("train", "validation", "test")
    }

    def tempered_for(mode: str) -> np.ndarray:
        profile = threshold_profiles[mode]
        return temper_probabilities(
            probabilities, surface_water, float(profile["water_temper_beta"])
        )

    metrics = {
        "active_threshold_mode": args.threshold_mode,
        "label_mode": args.label_mode,
        "positive_weight_scale": args.positive_weight_scale,
        "threshold_profiles": threshold_profiles,
        "validation": active_profile["validation"],
        "validation_at_default_threshold": evaluate(
            y[validation], probabilities[validation]
        ),
        "test": evaluate(y[test], decision_probabilities[test], decision_threshold),
        "test_by_threshold_mode": {
            mode: evaluate(
                y[test],
                tempered_for(mode)[test],
                float(profile["threshold"]),
            )
            for mode, profile in threshold_profiles.items()
        },
        "test_calibration": calibration_report(y[test], probabilities[test]),
        "validation_calibration": calibration_report(
            y[validation], probabilities[validation]
        ),
        "test_ranking_quality": ranking_diagnostics(y[test], probabilities[test]),
        "test_by_event": {
            mode: event_metrics(
                rows,
                test,
                y,
                tempered_for(mode),
                float(profile["threshold"]),
            )
            for mode, profile in threshold_profiles.items()
        },
        "false_positive_diagnostics": false_positive_diagnostics(
            rows,
            test,
            y,
            probabilities,
            decision_probabilities,
            decision_threshold,
        ),
        "rolling_origin_cross_validation": rolling_origin,
        "split_events": split_events,
    }
    absolute = np.abs(weights)
    importance = absolute / float(np.sum(absolute)) if np.sum(absolute) else absolute
    feature_importance = {
        name: round(float(value), 6)
        for name, value in sorted(
            zip(FEATURE_NAMES, importance, strict=True),
            key=lambda item: -item[1],
        )
    }
    methodology = {
        "label": (
            "flood-excess event-cell label "
            f"({args.label_mode}; threshold={args.target_threshold})"
        ),
        "rainfall_alignment": "ERA5 township rainfall on each event start date",
        "feature_engineering": (
            "Static terrain/land-cover inputs plus rainfall interaction features "
            "to partially recover non-linear hydrologic signal; land-cover shares "
            "normalized to 0-1 fractions"
        ),
        "false_alarm_reduction": (
            "Flood-excess labeling removes permanent-water pseudo-positives; "
            "positive-class sample weight scale "
            f"{args.positive_weight_scale:.2f}; permanent-water probability temper "
            "selected jointly with each operating threshold on validation only"
        ),
        "evaluation": (
            "chronological event holdout; latest 20% of events are test "
            "and the preceding 20% are validation; rolling-origin CV reported"
        ),
        "threshold_selection": (
            "Screening, balanced, and precision-first conservative thresholds "
            "are selected only on validation data; test data is never used "
            "for selection"
        ),
        "active_threshold_mode": args.threshold_mode,
        "label_mode": args.label_mode,
        "display_mode": "historical_hindcast",
        "limitations": [
            "This is a historical hindcast, not an operational or future forecast.",
            "Rainfall is township-level and does not represent river stage.",
            "GFD MODIS labels can miss cloud-obscured or vegetation-covered water.",
            "Permanent-water tempering reduces some false alarms but can miss "
            "flood expansion into wetland and open-water margins.",
            "The selected threshold requires validation on additional independent events.",
        ],
    }
    artifact = {
        "model_version": args.model_version,
        "algorithm": "NumPy regularized logistic regression",
        "operational_forecast": False,
        "feature_names": FEATURE_NAMES,
        "mean": mean.tolist(),
        "scale": scale.tolist(),
        "coefficients": weights.tolist(),
        "intercept": intercept,
        "target_threshold": args.target_threshold,
        "label_mode": args.label_mode,
        "decision_threshold": decision_threshold,
        "water_temper_beta": water_temper_beta,
        "positive_weight_scale": args.positive_weight_scale,
        "threshold_profiles": threshold_profiles,
        "feature_importance": feature_importance,
        "metrics": metrics,
        "false_positive_diagnostics": metrics["false_positive_diagnostics"],
        "methodology": methodology,
        "trained_at": datetime.now(UTC).isoformat(),
    }
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    model_id = persist_event_model(
        rows=rows,
        splits=splits,
        probabilities=probabilities,
        labels=y,
        model_version=args.model_version,
        target_threshold=args.target_threshold,
        decision_threshold=decision_threshold,
        metrics=metrics,
        feature_importance=feature_importance,
        split_events=split_events,
        methodology=methodology,
        artifact_path=args.artifact_output,
        decision_probabilities=decision_probabilities,
    )
    print(
        json.dumps(
            {
                "model_id": model_id,
                "rows": len(rows),
                "decision_threshold": decision_threshold,
                "water_temper_beta": water_temper_beta,
                "metrics": {
                    "test": metrics["test"],
                    "test_by_threshold_mode": metrics["test_by_threshold_mode"],
                    "rolling_origin_summary": rolling_origin["summary"],
                },
                "top_features": list(feature_importance.items())[:8],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
