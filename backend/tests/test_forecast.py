"""Tests for the live flood forecast inference contract."""

from datetime import date, datetime, UTC

import numpy as np
import pytest

from app.services.forecast import (
    ALL_FEATURE_NAMES,
    ENGINEERED_FEATURE_NAMES,
    FORECAST_LIMITATIONS,
    RAINFALL_FEATURE_NAMES,
    STATIC_FEATURE_NAMES,
    append_engineered_features,
    derive_rainfall_features,
    risk_band,
    sigmoid,
)


# -------------------------------------------------------------------
# Feature name consistency
# -------------------------------------------------------------------


def test_feature_names_match_event_model_training() -> None:
    """Live forecast uses the deployed v5 artifact; training adds extended features."""
    from scripts.build_flood_event_dataset import FEATURE_NAMES as TRAINING_FEATURES
    from scripts.train_flood_event_model import MODEL_VERSION

    assert MODEL_VERSION == "maubin-flood-event-logistic-v5"
    assert set(ALL_FEATURE_NAMES).issubset(set(TRAINING_FEATURES))


def test_feature_name_list_is_complete() -> None:
    expected = len(STATIC_FEATURE_NAMES) + len(RAINFALL_FEATURE_NAMES) + len(
        ENGINEERED_FEATURE_NAMES
    )
    assert len(ALL_FEATURE_NAMES) == expected


# -------------------------------------------------------------------
# Sigmoid
# -------------------------------------------------------------------


def test_sigmoid_outputs_zero_to_one() -> None:
    values = np.array([-100, -1, 0, 1, 100], dtype=float)
    result = sigmoid(values)
    assert np.all(result >= 0.0)
    assert np.all(result <= 1.0)
    assert result[2] == pytest.approx(0.5)


def test_sigmoid_is_monotonic() -> None:
    values = np.linspace(-5, 5, 100)
    result = sigmoid(values)
    assert np.all(np.diff(result) >= 0)


# -------------------------------------------------------------------
# Risk band
# -------------------------------------------------------------------


def test_risk_band_boundaries() -> None:
    assert risk_band(0.0) == "LOW"
    assert risk_band(0.24) == "LOW"
    assert risk_band(0.25) == "MODERATE"
    assert risk_band(0.49) == "MODERATE"
    assert risk_band(0.50) == "HIGH"
    assert risk_band(0.74) == "HIGH"
    assert risk_band(0.75) == "VERY_HIGH"
    assert risk_band(1.0) == "VERY_HIGH"


# -------------------------------------------------------------------
# Engineered features
# -------------------------------------------------------------------


def test_append_engineered_features_matches_training_script() -> None:
    """Ensure engineered features produce identical values to the training
    script's _append_engineered_features."""
    from scripts.build_flood_event_dataset import (
        _append_engineered_features as training_fn,
    )

    base = {
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

    row_forecast = dict(base)
    row_training = dict(base)

    append_engineered_features(row_forecast)
    training_fn(row_training)

    shared_features = set(ENGINEERED_FEATURE_NAMES) & set(row_training)
    for feat in shared_features:
        assert row_forecast[feat] == pytest.approx(
            row_training[feat], rel=1e-9
        ), f"Mismatch on {feat}"


# -------------------------------------------------------------------
# Rainfall feature derivation
# -------------------------------------------------------------------


def test_derive_rainfall_features_forecast_only() -> None:
    target = date(2026, 8, 12)
    forecast_daily = [
        {"date": date(2026, 8, 10), "precipitation_sum_mm": 5.0},
        {"date": date(2026, 8, 11), "precipitation_sum_mm": 10.0},
        {"date": date(2026, 8, 12), "precipitation_sum_mm": 20.0},
        {"date": date(2026, 8, 13), "precipitation_sum_mm": 8.0},
    ]

    result = derive_rainfall_features(target, forecast_daily, [])

    assert result["rainfall_mean_1d_mm"] == 20.0
    assert result["rainfall_max_1d_mm"] == 20.0
    assert result["rainfall_p90_1d_mm"] == 20.0
    # 3d: Aug 12 + Aug 11 + Aug 10 = 20 + 10 + 5
    assert result["rainfall_accumulation_3d_mm"] == 35.0
    # 7d: only Aug 10-12 available = 35
    assert result["rainfall_accumulation_7d_mm"] == 35.0
    # 30d: only what's available
    assert result["rainfall_accumulation_30d_mm"] == 35.0


def test_derive_rainfall_features_hybrid_with_history() -> None:
    target = date(2026, 8, 12)
    forecast_daily = [
        {"date": date(2026, 8, 12), "precipitation_sum_mm": 15.0},
    ]
    historical = [
        {"date": date(2026, 8, 11), "mean_precipitation_mm": 8.0},
        {"date": date(2026, 8, 10), "mean_precipitation_mm": 3.0},
        {"date": date(2026, 8, 5), "mean_precipitation_mm": 12.0},
        {"date": date(2026, 7, 20), "mean_precipitation_mm": 25.0},
    ]

    result = derive_rainfall_features(target, forecast_daily, historical)

    assert result["rainfall_mean_1d_mm"] == 15.0
    # 3d: Aug 12 (15) + Aug 11 (8) + Aug 10 (3)
    assert result["rainfall_accumulation_3d_mm"] == 26.0
    # 7d: Aug 12 (15) + Aug 11 (8) + Aug 10 (3) + Aug 5 is outside 7-day window
    # Aug 6-9 = 0, so 7d = 15 + 8 + 3 + 0 + 0 + 0 + 0 = 26
    assert result["rainfall_accumulation_7d_mm"] == 26.0
    # 30d: includes Jul 20 (25) and Aug 5 (12)
    assert result["rainfall_accumulation_30d_mm"] == pytest.approx(
        15.0 + 8.0 + 3.0 + 12.0 + 25.0
    )


def test_derive_rainfall_features_string_dates() -> None:
    """Ensure string dates are parsed correctly."""
    target = date(2026, 8, 12)
    forecast_daily = [
        {"date": "2026-08-12", "precipitation_sum_mm": 10.0},
    ]
    historical = [
        {"date": "2026-08-11", "mean_precipitation_mm": 5.0},
    ]

    result = derive_rainfall_features(target, forecast_daily, historical)

    assert result["rainfall_mean_1d_mm"] == 10.0
    assert result["rainfall_accumulation_3d_mm"] == 15.0


def test_derive_rainfall_features_forecast_overrides_history() -> None:
    """When forecast and history overlap, forecast should take priority."""
    target = date(2026, 8, 12)
    forecast_daily = [
        {"date": date(2026, 8, 12), "precipitation_sum_mm": 20.0},
    ]
    historical = [
        # History also has Aug 12 — should be overridden
        {"date": date(2026, 8, 12), "mean_precipitation_mm": 5.0},
    ]

    result = derive_rainfall_features(target, forecast_daily, historical)

    assert result["rainfall_mean_1d_mm"] == 20.0


def test_derive_rainfall_features_zero_rainfall() -> None:
    target = date(2026, 8, 12)
    result = derive_rainfall_features(target, [], [])

    assert result["rainfall_mean_1d_mm"] == 0.0
    assert result["rainfall_accumulation_3d_mm"] == 0.0
    assert result["rainfall_accumulation_7d_mm"] == 0.0
    assert result["rainfall_accumulation_30d_mm"] == 0.0


# -------------------------------------------------------------------
# API endpoints registration
# -------------------------------------------------------------------


def test_openapi_lists_forecast_endpoints(client) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/flood-forecast/runs" in paths
    assert "/api/v1/flood-forecast/runs/latest" in paths
    assert "/api/v1/flood-forecast/predictions/index" in paths

    # POST method exists on /runs
    runs_methods = paths["/api/v1/flood-forecast/runs"]
    assert "post" in runs_methods
    assert "get" in runs_methods


def test_forecast_limitations_are_not_empty() -> None:
    assert len(FORECAST_LIMITATIONS) >= 3
    assert any("experimental" in lim.lower() for lim in FORECAST_LIMITATIONS)
    assert any("precision" in lim.lower() for lim in FORECAST_LIMITATIONS)
