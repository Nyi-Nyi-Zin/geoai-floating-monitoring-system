"""Train and compare leakage-safe chronological Maubin flood-hindcast candidates.

Model selection is based on the 2009–2016 validation interval. The 2018 events remain
fully held out until the final comparison. Labels originate from native GFD flooded pixels
with permanent water excluded.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT = Path("/home/ubuntu/deltawatch-permanent")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs")

STATIC_FEATURES = [
    "elevation_mean_m", "elevation_percentile", "local_relief_m", "distance_to_waterway_m",
    "land_cover_dominant_code",
]
INFRASTRUCTURE_FEATURES = ["osm_drainage_distance_m", "osm_levee_distance_m"]
HYDROLOGIC_FEATURES = [
    "rainfall_lag_1d_mm", "rainfall_lag_3d_mm", "rainfall_lag_7d_mm", "rainfall_lag_14d_mm", "rainfall_lag_30d_mm",
    "discharge_lag_1d_m3s", "discharge_lag_3d_m3s", "discharge_lag_7d_m3s", "discharge_lag_14d_m3s", "discharge_lag_30d_m3s",
]
TRAIN_CUTOFF = "2009-01-01"
TEST_START = "2018-01-01"


def choose_threshold(y_true: pd.Series, probabilities: np.ndarray) -> float:
    candidates = np.linspace(0.02, 0.98, 97)
    scores = [(threshold, f1_score(y_true, probabilities >= threshold, zero_division=0)) for threshold in candidates]
    return float(max(scores, key=lambda item: item[1])[0])


def metrics(y_true: pd.Series, probabilities: np.ndarray, threshold: float) -> dict:
    predicted = probabilities >= threshold
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
    return {
        "rows": int(len(y_true)),
        "positives": int(y_true.sum()),
        "negatives": int((1 - y_true).sum()),
        "threshold": round(threshold, 4),
        "precision": round(float(precision_score(y_true, predicted, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, predicted, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, predicted, zero_division=0)), 4),
        "pr_auc": round(float(average_precision_score(y_true, probabilities)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, probabilities)), 4),
        "brier_score": round(float(brier_score_loss(y_true, probabilities)), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def logistic_pipeline(features: list[str]) -> Pipeline:
    categorical = ["land_cover_dominant_code"] if "land_cover_dominant_code" in features else []
    numeric = [feature for feature in features if feature not in categorical]
    transform = ColumnTransformer([
        ("numeric", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), numeric),
        ("categorical", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical),
    ])
    return Pipeline([("transform", transform), ("model", LogisticRegression(max_iter=2000, class_weight="balanced", C=0.4, solver="lbfgs"))])


def hgb_pipeline(features: list[str]) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", HistGradientBoostingClassifier(max_iter=250, learning_rate=0.06, max_leaf_nodes=24, l2_regularization=1.2, random_state=42)),
    ])


def random_forest_pipeline(features: list[str]) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestClassifier(
            n_estimators=320,
            max_depth=14,
            min_samples_leaf=18,
            max_features=0.75,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=42,
        )),
    ])


def main() -> None:
    predictors = pd.read_csv(OUTPUT / "maubin_training_events_v7.csv")
    labels = pd.read_csv(OUTPUT / "native_gfd_cell_labels.csv")
    frame = predictors.drop(columns=["flooded_label"]).merge(
        labels[["event_id", "cell_id", "flooded_label", "flood_fraction", "valid_pixel_count"]],
        on=["event_id", "cell_id"],
        how="inner",
        validate="one_to_one",
    )
    frame["event_start"] = pd.to_datetime(frame["event_start"])
    train = frame.loc[frame["event_start"] < TRAIN_CUTOFF].copy()
    validation = frame.loc[(frame["event_start"] >= TRAIN_CUTOFF) & (frame["event_start"] < TEST_START)].copy()
    test = frame.loc[frame["event_start"] >= TEST_START].copy()

    experiment_definitions = {
        "v7_terrain_logistic": ("logistic", STATIC_FEATURES),
        "v7_hydrologic_logistic": ("logistic", STATIC_FEATURES + INFRASTRUCTURE_FEATURES + HYDROLOGIC_FEATURES),
        "v7_hydrologic_hgb": ("hgb", STATIC_FEATURES + INFRASTRUCTURE_FEATURES + HYDROLOGIC_FEATURES),
        "v7_hydrologic_rf": ("rf", STATIC_FEATURES + INFRASTRUCTURE_FEATURES + HYDROLOGIC_FEATURES),
    }
    results = {"split": {"train_events_before": TRAIN_CUTOFF, "test_events_from": TEST_START, "train_rows": len(train), "validation_rows": len(validation), "test_rows": len(test)}, "models": {}}
    test_predictions = {}

    for name, (model_type, features) in experiment_definitions.items():
        model = logistic_pipeline(features) if model_type == "logistic" else hgb_pipeline(features) if model_type == "hgb" else random_forest_pipeline(features)
        if model_type == "hgb":
            positives = int(train["flooded_label"].sum())
            negatives = int(len(train) - positives)
            weights = np.where(train["flooded_label"].to_numpy() == 1, negatives / max(positives, 1), 1.0)
            model.fit(train[features], train["flooded_label"], model__sample_weight=weights)
        else:
            model.fit(train[features], train["flooded_label"])
        validation_probabilities = model.predict_proba(validation[features])[:, 1]
        threshold = choose_threshold(validation["flooded_label"], validation_probabilities)

        pretest = frame.loc[frame["event_start"] < TEST_START].copy()
        final_model = logistic_pipeline(features) if model_type == "logistic" else hgb_pipeline(features) if model_type == "hgb" else random_forest_pipeline(features)
        if model_type == "hgb":
            positives = int(pretest["flooded_label"].sum())
            negatives = int(len(pretest) - positives)
            weights = np.where(pretest["flooded_label"].to_numpy() == 1, negatives / max(positives, 1), 1.0)
            final_model.fit(pretest[features], pretest["flooded_label"], model__sample_weight=weights)
        else:
            final_model.fit(pretest[features], pretest["flooded_label"])
        test_probabilities = final_model.predict_proba(test[features])[:, 1]
        results["models"][name] = {
            "algorithm": model_type,
            "feature_count": len(features),
            "features": features,
            "test_refit_training_rows": len(pretest),
            "validation": metrics(validation["flooded_label"], validation_probabilities, threshold),
            "test": metrics(test["flooded_label"], test_probabilities, threshold),
        }
        test_predictions[name] = test_probabilities

    best_name = max(results["models"], key=lambda name: results["models"][name]["validation"]["f1"])
    results["selected_candidate"] = best_name
    results["selection_basis"] = "Highest validation F1 with threshold selected on validation only; 2018 remains held out."
    (OUTPUT / "candidate_metrics_v7.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    prediction_frame = test[["event_id", "event_start", "cell_id", "flooded_label", "flood_fraction"]].copy()
    for name, probabilities in test_predictions.items():
        prediction_frame[f"{name}_probability"] = probabilities
    prediction_frame.to_csv(OUTPUT / "candidate_test_predictions_v7.csv", index=False)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
