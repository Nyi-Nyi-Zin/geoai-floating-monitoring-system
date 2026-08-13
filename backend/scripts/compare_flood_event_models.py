"""Compare logistic vs Random Forest vs gradient boosting on the event CSV.

Designed for local OR Google Colab:
  1. Upload `maubin_flood_event_dataset_v1.csv`
  2. Run this module (or the Colab notebook)
  3. Download `artifacts/maubin_flood_event_model_comparison.json`

Does not require PostGIS. Uses the CSV temporal_split and target_label columns.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np

from scripts.build_flood_event_dataset import FEATURE_NAMES
from scripts.train_flood_event_model import (
    THRESHOLD_MODES,
    select_threshold_profile,
    temper_probabilities,
)
from scripts.train_flood_susceptibility import evaluate

try:
    from sklearn.ensemble import (
        HistGradientBoostingClassifier,
        RandomForestClassifier,
    )
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
except ImportError as exc:  # pragma: no cover - exercised in Colab setup
    raise SystemExit(
        "scikit-learn is required. Install with:\n"
        "  pip install scikit-learn\n"
        f"Original error: {exc}"
    ) from exc


ModelFactory = Callable[[np.ndarray, np.ndarray], Any]


def load_comparison_csv(path: Path) -> dict[str, np.ndarray | list[str]]:
    import csv

    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    if not rows:
        raise ValueError(f"No rows in {path}")
    missing = [name for name in FEATURE_NAMES if name not in rows[0]]
    if missing:
        raise ValueError(f"CSV missing features: {missing}")
    for required in ("target_label", "temporal_split", "event_id"):
        if required not in rows[0]:
            raise ValueError(f"CSV missing column: {required}")

    x = np.asarray(
        [[float(row[name]) for name in FEATURE_NAMES] for row in rows],
        dtype=float,
    )
    y = np.asarray([float(row["target_label"]) for row in rows], dtype=float)
    splits = np.asarray([row["temporal_split"] for row in rows])
    surface_water = np.asarray(
        [float(row.get("surface_water_influence_pct") or 0.0) for row in rows],
        dtype=float,
    )
    event_ids = [str(row["event_id"]) for row in rows]
    return {
        "x": x,
        "y": y,
        "splits": splits,
        "surface_water": surface_water,
        "event_ids": event_ids,
        "rows": len(rows),
    }


def fit_logistic_sklearn(x_train: np.ndarray, y_train: np.ndarray) -> Pipeline:
    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    solver="lbfgs",
                ),
            ),
        ]
    )
    model.fit(x_train, y_train)
    return model


def fit_random_forest(x_train: np.ndarray, y_train: np.ndarray) -> RandomForestClassifier:
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=20,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=42,
    )
    model.fit(x_train, y_train)
    return model


def fit_hist_gradient_boosting(
    x_train: np.ndarray, y_train: np.ndarray
) -> HistGradientBoostingClassifier:
    # sklearn HGB is the default "boosting" baseline (XGBoost-like, no extra dep).
    common = {
        "max_depth": 6,
        "learning_rate": 0.05,
        "max_iter": 300,
        "l2_regularization": 0.1,
        "random_state": 42,
    }
    try:
        model = HistGradientBoostingClassifier(class_weight="balanced", **common)
        model.fit(x_train, y_train)
        return model
    except TypeError:
        model = HistGradientBoostingClassifier(**common)
        positives = max(1, int(np.sum(y_train == 1)))
        negatives = max(1, int(np.sum(y_train == 0)))
        sample_weight = np.where(
            y_train == 1,
            negatives / (2 * positives),
            positives / (2 * negatives),
        )
        model.fit(x_train, y_train, sample_weight=sample_weight)
        return model


def fit_xgboost(x_train: np.ndarray, y_train: np.ndarray) -> Any:
    try:
        from xgboost import XGBClassifier
    except ImportError as exc:
        raise RuntimeError(
            "xgboost is not installed. Optional: pip install xgboost"
        ) from exc

    positives = max(1, int(np.sum(y_train == 1)))
    negatives = max(1, int(np.sum(y_train == 0)))
    scale_pos_weight = negatives / positives
    model = XGBClassifier(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        objective="binary:logistic",
        eval_metric="aucpr",
        scale_pos_weight=scale_pos_weight,
        n_jobs=-1,
        random_state=42,
    )
    model.fit(x_train, y_train)
    return model


def predict_proba_positive(model: Any, x: np.ndarray) -> np.ndarray:
    probabilities = model.predict_proba(x)
    if probabilities.ndim != 2 or probabilities.shape[1] < 2:
        raise ValueError("Model did not return binary predict_proba output")
    return np.asarray(probabilities[:, 1], dtype=float)


def feature_importance_for(model: Any) -> dict[str, float]:
    raw: np.ndarray | None = None
    if isinstance(model, Pipeline):
        clf = model.named_steps.get("clf")
        if hasattr(clf, "coef_"):
            raw = np.abs(np.asarray(clf.coef_).reshape(-1))
    elif hasattr(model, "feature_importances_"):
        raw = np.asarray(model.feature_importances_, dtype=float)
    if raw is None or len(raw) != len(FEATURE_NAMES):
        return {}
    total = float(np.sum(raw)) or 1.0
    ranked = sorted(
        (
            (name, round(float(value) / total, 6))
            for name, value in zip(FEATURE_NAMES, raw, strict=True)
        ),
        key=lambda item: -item[1],
    )
    return dict(ranked)


def evaluate_model_family(
    *,
    name: str,
    factory: ModelFactory,
    x: np.ndarray,
    y: np.ndarray,
    splits: np.ndarray,
    surface_water: np.ndarray,
    minimum_screening_precision: float,
    minimum_conservative_recall: float,
) -> dict[str, Any]:
    train = splits == "train"
    validation = splits == "validation"
    test = splits == "test"
    if len(np.unique(y[train])) < 2:
        raise ValueError(f"{name}: training split must contain both classes")

    model = factory(x[train], y[train])
    probabilities = predict_proba_positive(model, x)

    profiles = {
        mode: {
            **select_threshold_profile(
                y[validation],
                probabilities[validation],
                surface_water[validation],
                mode,
                minimum_screening_precision=minimum_screening_precision,
                minimum_conservative_recall=minimum_conservative_recall,
            ),
            "selection_objective": mode,
        }
        for mode in THRESHOLD_MODES
    }

    def tempered(mode: str) -> np.ndarray:
        return temper_probabilities(
            probabilities,
            surface_water,
            float(profiles[mode]["water_temper_beta"]),
        )

    test_by_mode = {
        mode: evaluate(
            y[test],
            tempered(mode)[test],
            float(profile["threshold"]),
        )
        for mode, profile in profiles.items()
    }
    best_mode = max(
        THRESHOLD_MODES,
        key=lambda mode: (
            float(test_by_mode[mode]["precision"]),
            float(test_by_mode[mode]["f1"]),
            float(test_by_mode[mode]["recall"]),
        ),
    )
    return {
        "algorithm": name,
        "train_rows": int(np.sum(train)),
        "validation_rows": int(np.sum(validation)),
        "test_rows": int(np.sum(test)),
        "test_positives": int(np.sum(y[test])),
        "threshold_profiles": {
            mode: {
                "threshold": profile["threshold"],
                "water_temper_beta": profile["water_temper_beta"],
                "validation": profile["validation"],
            }
            for mode, profile in profiles.items()
        },
        "test_by_threshold_mode": test_by_mode,
        "best_test_mode": best_mode,
        "best_test": test_by_mode[best_mode],
        "feature_importance_top8": list(feature_importance_for(model).items())[:8],
    }


def pick_winner(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ranked = sorted(
        results.items(),
        key=lambda item: (
            float(item[1]["best_test"]["precision"]),
            float(item[1]["best_test"]["f1"]),
            float(item[1]["best_test"]["pr_auc"]),
        ),
        reverse=True,
    )
    winner_name, winner = ranked[0]
    baseline = results.get("logistic_sklearn") or next(iter(results.values()))
    baseline_precision = float(baseline["best_test"]["precision"])
    winner_precision = float(winner["best_test"]["precision"])
    improved = winner_precision > baseline_precision + 0.01
    return {
        "algorithm": winner_name,
        "best_test_mode": winner["best_test_mode"],
        "precision": winner_precision,
        "recall": float(winner["best_test"]["recall"]),
        "f1": float(winner["best_test"]["f1"]),
        "beats_logistic_by_precision": improved,
        "recommendation": (
            f"Promote {winner_name} as the experimental event model candidate."
            if improved
            else (
                "No meaningful precision gain over logistic. Keep logistic as the "
                "explainable baseline; invest in better labels/features next."
            )
        ),
    }


def available_model_factories(*, include_xgboost: bool) -> dict[str, ModelFactory]:
    factories: dict[str, ModelFactory] = {
        "logistic_sklearn": fit_logistic_sklearn,
        "random_forest": fit_random_forest,
        "hist_gradient_boosting": fit_hist_gradient_boosting,
    }
    if include_xgboost:
        factories["xgboost"] = fit_xgboost
    return factories


def run_comparison(
    *,
    dataset: Path,
    output: Path,
    include_xgboost: bool,
    minimum_screening_precision: float,
    minimum_conservative_recall: float,
) -> dict[str, Any]:
    loaded = load_comparison_csv(dataset)
    x = np.asarray(loaded["x"], dtype=float)
    y = np.asarray(loaded["y"], dtype=float)
    splits = np.asarray(loaded["splits"])
    surface_water = np.asarray(loaded["surface_water"], dtype=float)

    results: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for name, factory in available_model_factories(
        include_xgboost=include_xgboost
    ).items():
        try:
            results[name] = evaluate_model_family(
                name=name,
                factory=factory,
                x=x,
                y=y,
                splits=splits,
                surface_water=surface_water,
                minimum_screening_precision=minimum_screening_precision,
                minimum_conservative_recall=minimum_conservative_recall,
            )
        except Exception as exc:  # noqa: BLE001 - report per-model failures
            errors[name] = str(exc)

    if not results:
        raise RuntimeError(f"All model fits failed: {errors}")

    report = {
        "report_version": "maubin-flood-event-model-comparison-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": str(dataset),
        "rows": int(loaded["rows"]),
        "feature_names": FEATURE_NAMES,
        "split_counts": {
            "train": int(np.sum(splits == "train")),
            "validation": int(np.sum(splits == "validation")),
            "test": int(np.sum(splits == "test")),
        },
        "models": results,
        "errors": errors,
        "winner": pick_winner(results),
        "baseline_reference": {
            "numpy_logistic_v2_flood_extent_balanced_precision": 0.1664,
            "numpy_logistic_v5_flood_excess_balanced_precision": 0.1294,
            "note": (
                "CSV target_label follows the export label_mode "
                "(flood_excess if exported with that flag)."
            ),
        },
        "limitations": [
            "Comparison uses the same chronological CSV splits as the event model.",
            "Rolling-origin CV is omitted here for runtime; use train_flood_event_model for that.",
            "This report does not auto-replace the production/experimental DB model.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare logistic / Random Forest / boosting on the event CSV"
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/derived/maubin_flood_event_dataset_v1.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/maubin_flood_event_model_comparison.json"),
    )
    parser.add_argument(
        "--include-xgboost",
        action="store_true",
        help="Also train XGBoost if the xgboost package is installed.",
    )
    parser.add_argument("--minimum-screening-precision", type=float, default=0.10)
    parser.add_argument("--minimum-conservative-recall", type=float, default=0.20)
    args = parser.parse_args()

    report = run_comparison(
        dataset=args.dataset,
        output=args.output,
        include_xgboost=args.include_xgboost,
        minimum_screening_precision=args.minimum_screening_precision,
        minimum_conservative_recall=args.minimum_conservative_recall,
    )
    summary = {
        "output": str(args.output),
        "winner": report["winner"],
        "models": {
            name: {
                "best_mode": result["best_test_mode"],
                "precision": result["best_test"]["precision"],
                "recall": result["best_test"]["recall"],
                "f1": result["best_test"]["f1"],
            }
            for name, result in report["models"].items()
        },
        "errors": report["errors"],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
