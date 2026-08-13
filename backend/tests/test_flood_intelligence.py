import pytest

from app.services.flood_intelligence import (
    classify_early_warning,
    classify_flood_scenario,
)


def test_classify_flood_scenario_matrix() -> None:
    assert classify_flood_scenario(0.82, False).scenario == "high_predicted_risk"
    assert classify_flood_scenario(0.40, True).scenario == "observed_flood_alert"
    assert classify_flood_scenario(0.90, True).scenario == "confirmed_high_risk"
    assert classify_flood_scenario(0.10, False).scenario == "low_risk"


def test_early_warning_levels() -> None:
    assert classify_early_warning(0.10).level == "LOW"
    assert classify_early_warning(0.30).level == "MODERATE"
    assert classify_early_warning(0.60).level == "HIGH"
    assert classify_early_warning(0.85).level == "CRITICAL"


def test_openapi_lists_flood_intelligence_endpoints(client) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/flood-intelligence/summary" in paths
    assert "/api/v1/flood-intelligence/sar-validation" in paths
    assert "/api/v1/flood-intelligence/exposure" in paths
