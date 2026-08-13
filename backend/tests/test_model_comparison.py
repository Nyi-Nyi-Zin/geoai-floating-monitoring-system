"""Tests for Priority 4 model comparison helpers."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import numpy as np

from scripts.build_flood_event_dataset import FEATURE_NAMES
from scripts.compare_flood_event_models import (
    evaluate_model_family,
    fit_logistic_sklearn,
    fit_random_forest,
    load_comparison_csv,
    pick_winner,
    run_comparison,
)


def _write_tiny_csv(path: Path) -> None:
    rng = np.random.default_rng(0)
    fieldnames = [
        "event_id",
        "temporal_split",
        "target_label",
        "surface_water_influence_pct",
        *FEATURE_NAMES,
    ]
    rows: list[dict[str, object]] = []
    for index in range(120):
        split = "train" if index < 70 else "validation" if index < 95 else "test"
        label = 1 if (index % 5 == 0) else 0
        features = {
            name: float(rng.normal(label * 0.8, 1.0)) for name in FEATURE_NAMES
        }
        rows.append(
            {
                "event_id": str((index // 20) + 1),
                "temporal_split": split,
                "target_label": label,
                "surface_water_influence_pct": 0.1 if label else 0.4,
                **features,
            }
        )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_load_comparison_csv_reads_features() -> None:
    with tempfile.TemporaryDirectory() as raw:
        csv_path = Path(raw) / "tiny.csv"
        _write_tiny_csv(csv_path)
        loaded = load_comparison_csv(csv_path)
        assert loaded["rows"] == 120
        assert np.asarray(loaded["x"]).shape[1] == len(FEATURE_NAMES)


def test_evaluate_model_family_returns_threshold_modes() -> None:
    with tempfile.TemporaryDirectory() as raw:
        csv_path = Path(raw) / "tiny.csv"
        _write_tiny_csv(csv_path)
        loaded = load_comparison_csv(csv_path)
        result = evaluate_model_family(
            name="logistic_sklearn",
            factory=fit_logistic_sklearn,
            x=np.asarray(loaded["x"], dtype=float),
            y=np.asarray(loaded["y"], dtype=float),
            splits=np.asarray(loaded["splits"]),
            surface_water=np.asarray(loaded["surface_water"], dtype=float),
            minimum_screening_precision=0.05,
            minimum_conservative_recall=0.10,
        )
        assert set(result["test_by_threshold_mode"]) == {
            "screening",
            "balanced",
            "conservative",
        }
        assert 0.0 <= result["best_test"]["precision"] <= 1.0


def test_run_comparison_writes_report() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        csv_path = base / "tiny.csv"
        output = base / "comparison.json"
        _write_tiny_csv(csv_path)
        report = run_comparison(
            dataset=csv_path,
            output=output,
            include_xgboost=False,
            minimum_screening_precision=0.05,
            minimum_conservative_recall=0.10,
        )
        assert output.exists()
        assert "logistic_sklearn" in report["models"]
        assert "random_forest" in report["models"]
        assert "hist_gradient_boosting" in report["models"]
        assert "algorithm" in report["winner"]


def test_pick_winner_prefers_higher_precision() -> None:
    results = {
        "a": {
            "best_test_mode": "balanced",
            "best_test": {
                "precision": 0.10,
                "recall": 0.5,
                "f1": 0.16,
                "pr_auc": 0.1,
            },
        },
        "b": {
            "best_test_mode": "conservative",
            "best_test": {
                "precision": 0.25,
                "recall": 0.2,
                "f1": 0.22,
                "pr_auc": 0.2,
            },
        },
    }
    winner = pick_winner(results)
    assert winner["algorithm"] == "b"
    assert winner["beats_logistic_by_precision"] is True


def test_random_forest_factory_fits() -> None:
    with tempfile.TemporaryDirectory() as raw:
        csv_path = Path(raw) / "tiny.csv"
        _write_tiny_csv(csv_path)
        loaded = load_comparison_csv(csv_path)
        x = np.asarray(loaded["x"], dtype=float)
        y = np.asarray(loaded["y"], dtype=float)
        train = np.asarray(loaded["splits"]) == "train"
        model = fit_random_forest(x[train], y[train])
        assert hasattr(model, "predict_proba")
