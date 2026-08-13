import numpy as np
from datetime import date

import pytest

from app.services.flood_ml import calculate_event_readiness
from scripts.build_flood_event_dataset import (
    _append_engineered_features,
    as_fraction,
    event_target_label,
    flood_excess_fraction,
    temporal_split_map,
)
from scripts.train_flood_event_model import (
    calibration_report,
    event_metrics,
    ranking_diagnostics,
    rolling_origin_cross_validation,
    select_decision_threshold,
    select_precision_threshold,
    select_screening_threshold,
    select_threshold_profile,
    temper_probabilities,
)

from scripts.train_flood_susceptibility import (
    average_precision,
    evaluate,
    fit_logistic,
    risk_band,
    roc_auc,
    spatial_split,
)


def test_spatial_split_is_deterministic() -> None:
    assert spatial_split(95.65, 16.73) == spatial_split(95.65, 16.73)
    assert spatial_split(95.65, 16.73) in {"train", "validation", "test"}


def test_numpy_logistic_learns_separable_signal() -> None:
    x = np.array([[-2.0], [-1.0], [1.0], [2.0]])
    y = np.array([0.0, 0.0, 1.0, 1.0])
    weights, intercept = fit_logistic(
        x, y, iterations=1500, learning_rate=0.05, l2=0.01
    )

    assert weights[0] > 0
    assert intercept == intercept


def test_metrics_and_risk_bands() -> None:
    truth = np.array([0.0, 0.0, 1.0, 1.0])
    probability = np.array([0.1, 0.2, 0.8, 0.9])

    assert roc_auc(truth, probability) == 1.0
    assert average_precision(truth, probability) == 1.0
    assert evaluate(truth, probability)["f1"] == 1.0
    assert [risk_band(value) for value in (0.1, 0.3, 0.6, 0.9)] == [
        "LOW",
        "MODERATE",
        "HIGH",
        "VERY_HIGH",
    ]


def test_openapi_lists_flood_ml_endpoints(client) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/flood-ml/models/latest" in paths
    assert "/api/v1/flood-ml/predictions/index" in paths
    assert "/api/v1/flood-ml/event-readiness" in paths
    assert "/api/v1/flood-ml/event-models/latest" in paths
    assert "/api/v1/flood-ml/event-models/evaluation" in paths
    assert "/api/v1/flood-ml/event-predictions/index" in paths


def test_temporal_split_holds_out_latest_events() -> None:
    splits = temporal_split_map(
        [
            ("1", date(2010, 1, 1)),
            ("2", date(2011, 1, 1)),
            ("3", date(2012, 1, 1)),
            ("4", date(2013, 1, 1)),
        ]
    )

    assert splits == {"1": "train", "2": "train", "3": "validation", "4": "test"}


def test_temporal_split_uses_multiple_holdout_events_when_available() -> None:
    events = [
        (str(index), date(2000 + index, 1, 1)) for index in range(1, 18)
    ]

    splits = temporal_split_map(events)

    assert list(splits.values()).count("train") == 11
    assert list(splits.values()).count("validation") == 3
    assert list(splits.values()).count("test") == 3
    assert splits["17"] == "test"


def test_temporal_split_requires_four_events() -> None:
    with pytest.raises(ValueError, match="At least 4"):
        temporal_split_map([("1", date(2010, 1, 1))])


def test_engineered_event_features_capture_hydrology_context() -> None:
    row = {
        "distance_to_waterway_m": 125.0,
        "distance_to_river_m": 125.0,
        "distance_to_canal_m": 250.0,
        "hand_mean_m": 3.0,
        "elevation_percentile": 0.2,
        "local_relief_m": 1.0,
        "rainfall_accumulation_3d_mm": 60.0,
        "rainfall_accumulation_7d_mm": 120.0,
        "rainfall_accumulation_30d_mm": 300.0,
        "rainfall_max_1d_mm": 40.0,
        "landcover_water_pct": 0.10,
        "landcover_wetland_pct": 0.20,
        "landcover_mangrove_pct": 0.05,
    }

    _append_engineered_features(row)

    assert row["waterway_proximity_index"] == pytest.approx(2 / 3, rel=1e-6)
    assert row["surface_water_influence_pct"] == pytest.approx(0.35)
    assert row["flatness_index"] == pytest.approx(0.5)
    assert row["rainfall_7d_x_waterway_proximity"] == pytest.approx(80.0)
    assert row["rainfall_30d_x_low_elevation"] == pytest.approx(240.0)
    assert row["rainfall_3d_x_surface_water"] == pytest.approx(21.0)
    assert row["rainfall_7d_x_flatness"] == pytest.approx(60.0)


def test_as_fraction_accepts_percent_or_unit_scale() -> None:
    assert as_fraction(40) == pytest.approx(0.4)
    assert as_fraction(0.4) == pytest.approx(0.4)


def test_flood_excess_label_ignores_permanent_water_only_cells() -> None:
    row = {
        "flooded_fraction": 0.35,
        "landcover_water_pct": 40.0,
        "landcover_wetland_pct": 0.0,
        "landcover_mangrove_pct": 0.0,
    }

    assert flood_excess_fraction(row) == pytest.approx(0.0)
    assert event_target_label(row, 0.10, label_mode="flood_excess") == 0
    assert event_target_label(row, 0.10, label_mode="flood_extent") == 1

    wet = {
        "flooded_fraction": 0.55,
        "landcover_water_pct": 0.20,
        "landcover_wetland_pct": 0.0,
        "landcover_mangrove_pct": 0.0,
    }
    assert flood_excess_fraction(wet) == pytest.approx(0.35)
    assert event_target_label(wet, 0.10, label_mode="flood_excess") == 1


def test_event_readiness_requires_event_date_rainfall_alignment() -> None:
    event_dates = [date(2010 + index, 1, 1) for index in range(4)]

    ready, blockers = calculate_event_readiness(event_dates, set(event_dates))
    missing_ready, missing_blockers = calculate_event_readiness(
        event_dates, set(event_dates[:3])
    )

    assert ready is True
    assert blockers == []
    assert missing_ready is False
    assert "currently 3" in missing_blockers[0]


def test_event_threshold_is_selected_from_validation_f1() -> None:
    truth = np.array([0.0, 0.0, 1.0, 1.0])
    probability = np.array([0.1, 0.4, 0.45, 0.9])

    threshold, metrics = select_decision_threshold(truth, probability)

    assert 0.4 < threshold <= 0.45
    assert metrics["f1"] == 1.0


def test_precision_threshold_respects_recall_floor() -> None:
    truth = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
    probability = np.array([0.05, 0.55, 0.60, 0.58, 0.70, 0.95])

    balanced_threshold, balanced = select_decision_threshold(truth, probability)
    conservative_threshold, conservative = select_precision_threshold(
        truth, probability, minimum_recall=0.60
    )

    assert conservative_threshold >= balanced_threshold
    assert conservative["precision"] >= balanced["precision"]
    assert conservative["recall"] >= 0.60


def test_screening_threshold_prefers_recall_with_precision_floor() -> None:
    truth = np.array([0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0])
    probability = np.array([0.12, 0.18, 0.24, 0.30, 0.22, 0.40, 0.75, 0.95])

    balanced_threshold, balanced = select_decision_threshold(truth, probability)
    screening_threshold, screening = select_screening_threshold(
        truth, probability, minimum_precision=0.50
    )

    assert screening_threshold <= balanced_threshold
    assert screening["recall"] >= balanced["recall"]
    assert screening["precision"] >= 0.50


def test_precision_threshold_falls_back_when_recall_floor_is_impossible() -> None:
    truth = np.array([0.0, 0.0, 1.0, 1.0])
    probability = np.array([0.1, 0.2, 0.8, 0.9])

    threshold, metrics = select_precision_threshold(
        truth, probability, minimum_recall=1.0
    )

    assert threshold <= 0.8
    assert metrics["recall"] == 1.0


def test_calibration_report_is_zero_for_perfect_probabilities() -> None:
    truth = np.array([0.0, 0.0, 1.0, 1.0])
    probability = np.array([0.0, 0.0, 1.0, 1.0])

    report = calibration_report(truth, probability, bins=4)

    assert report["expected_calibration_error"] == 0.0
    assert report["maximum_calibration_error"] == 0.0


def test_ranking_diagnostics_reports_top_slice_precision() -> None:
    truth = np.array([1.0, 0.0, 1.0, 0.0, 0.0])
    probability = np.array([0.95, 0.80, 0.60, 0.30, 0.10])

    report = ranking_diagnostics(truth, probability, fractions=(0.4,))

    assert report["top_40pct"]["cells"] == 2
    assert report["top_40pct"]["true_positive_cells"] == 1
    assert report["top_40pct"]["precision"] == 0.5


def test_temper_probabilities_downweights_permanent_water() -> None:
    probability = np.array([0.80, 0.80])
    surface_water = np.array([0.0, 1.0])

    tempered = temper_probabilities(probability, surface_water, beta=0.5)

    assert tempered[0] == pytest.approx(0.80)
    assert tempered[1] == pytest.approx(0.40)


def test_threshold_profile_can_select_water_temper() -> None:
    truth = np.array([1.0, 1.0, 0.0, 0.0, 0.0, 0.0])
    probability = np.array([0.90, 0.70, 0.85, 0.65, 0.20, 0.10])
    surface_water = np.array([0.0, 0.1, 1.0, 0.9, 0.0, 0.0])

    profile = select_threshold_profile(
        truth,
        probability,
        surface_water,
        "conservative",
        minimum_screening_precision=0.10,
        minimum_conservative_recall=0.40,
    )

    assert 0.0 <= profile["water_temper_beta"] <= 0.8
    assert profile["validation"]["precision"] >= 0.4
    assert profile["validation"]["recall"] >= 0.4


def test_positive_weight_scale_is_accepted_by_logistic() -> None:
    x = np.array([[-2.0], [-1.0], [1.0], [2.0]])
    y = np.array([0.0, 0.0, 1.0, 1.0])
    weights, intercept = fit_logistic(
        x,
        y,
        iterations=500,
        learning_rate=0.05,
        l2=0.01,
        positive_weight_scale=0.5,
    )

    assert weights[0] > 0
    assert intercept == intercept


def test_event_metrics_report_per_event_confusion() -> None:
    rows = [
        {
            "event_id": "a",
            "event_start_date": date(2020, 1, 1),
            "surface_water_influence_pct": 0.0,
        },
        {
            "event_id": "a",
            "event_start_date": date(2020, 1, 1),
            "surface_water_influence_pct": 0.0,
        },
        {
            "event_id": "b",
            "event_start_date": date(2021, 1, 1),
            "surface_water_influence_pct": 0.0,
        },
        {
            "event_id": "b",
            "event_start_date": date(2021, 1, 1),
            "surface_water_influence_pct": 0.0,
        },
    ]
    labels = np.array([1.0, 0.0, 1.0, 0.0])
    probabilities = np.array([0.9, 0.8, 0.2, 0.1])
    mask = np.array([True, True, True, True])

    report = event_metrics(rows, mask, labels, probabilities, threshold=0.5)

    assert report["a"]["confusion_matrix"] == {"tn": 0, "fp": 1, "fn": 0, "tp": 1}
    assert report["b"]["confusion_matrix"] == {"tn": 1, "fp": 0, "fn": 1, "tp": 0}
    assert report["a"]["precision"] == 0.5


def test_rolling_origin_cross_validation_returns_fold_summary() -> None:
    feature_count = 3
    rows: list[dict] = []
    x_rows: list[list[float]] = []
    y_rows: list[float] = []
    for event_index in range(5):
        event_id = str(event_index + 1)
        event_date = date(2010 + event_index, 1, 1)
        for cell_index in range(8):
            positive = cell_index < (2 + event_index % 2)
            rainfall = 20.0 + 15.0 * event_index + (8.0 if positive else 0.0)
            elevation = 0.2 if positive else 0.8
            water = 0.1 if positive else 0.6
            rows.append(
                {
                    "event_id": event_id,
                    "event_start_date": event_date,
                    "surface_water_influence_pct": water,
                }
            )
            x_rows.append([rainfall, elevation, water])
            y_rows.append(1.0 if positive else 0.0)

    report = rolling_origin_cross_validation(
        rows,
        np.asarray(x_rows, dtype=float),
        np.asarray(y_rows, dtype=float),
        iterations=200,
        learning_rate=0.05,
        l2=0.01,
        positive_weight_scale=0.75,
        minimum_screening_precision=0.10,
        minimum_conservative_recall=0.20,
    )

    assert len(report["folds"]) >= 1
    assert set(report["summary"]) == {"screening", "balanced", "conservative"}
    for mode in ("screening", "balanced", "conservative"):
        assert report["summary"][mode]["folds"] == len(report["folds"])
        assert 0.0 <= report["summary"][mode]["mean_precision"] <= 1.0
        assert "water_temper_beta" in report["folds"][0]["threshold_profiles"][mode]
