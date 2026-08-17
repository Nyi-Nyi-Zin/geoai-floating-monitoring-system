"""Exercise the FastAPI nationwide evidence-readiness route with a controlled seed.

The check validates the public contract only; it does not load model data or produce
scores, probabilities, predictions, or alerts.
"""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spatial_api import main


main.myanmar_admin_evidence_readiness_seed = lambda: {
    "schema": "deltawatch-myanmar-admin1-evidence-readiness-v4",
    "region_count": 1,
    "regions": [{"admin1_pcode": "MMR017", "evidence_readiness": "historical_source_coverage_only_not_validated_for_prediction"}],
    "static_context": {"status": "versioned_admin1_static_context_complete", "interpretation": "Static source context only."},
    "upstream_flow_readiness": {"status": "bounded_source_snapshot_available_not_authorized_as_issue_time_feature", "regions_with_source_snapshot": 18, "official_issue_timestamp_present": False, "model_feature_authorized": False, "reason": "No official forecast issue time is retained."},
    "official_issue_time_flow_access": {"status": "access_blocked_dataset_terms_not_accepted", "dataset": "cems-glofas-forecast", "issue_time_feature_authorized": False, "model_feature_authorized": False, "reason": "Terms acceptance is required."},
    "nonlogin_source_quality": {"status": "complete_static_and_rainfall_coverage_with_closed_candidate_gate", "expected_admin1_region_count": 18, "model_feature_authorized": False, "reason": "Static and rainfall coverage do not authorize a model."},
    "prospective_validation_readiness": {"status": "no_verified_nationwide_prospective_outcomes", "model_evaluation_authorized": False, "reason": "No verified nationwide outcomes."},
    "candidate_gate": {"status": "no_fit_authorized", "model_status": "not_fitted", "fit_authorized": False, "promotion_authorized": False, "reason": "Issue-time flow and prospective validation are absent."},
    "interpretation": "Historical source coverage and static context only; it is not a forecast, risk score, probability, likelihood, or alert. No nationwide candidate model has been fitted.",
    "limits": ["Observed source context only."],
}

response = TestClient(main.app).get("/national-admin/evidence-readiness")
assert response.status_code == 200, response.text
payload = response.json()
assert payload["schema"] == "deltawatch-myanmar-admin1-evidence-readiness-v4"
assert payload["region_count"] == 1
assert payload["regions"][0]["admin1_pcode"] == "MMR017"
assert payload["static_context"]["status"] == "versioned_admin1_static_context_complete"
assert payload["upstream_flow_readiness"]["status"] == "bounded_source_snapshot_available_not_authorized_as_issue_time_feature"
assert payload["upstream_flow_readiness"]["official_issue_timestamp_present"] is False
assert payload["upstream_flow_readiness"]["model_feature_authorized"] is False
assert payload["official_issue_time_flow_access"]["status"] == "access_blocked_dataset_terms_not_accepted"
assert payload["official_issue_time_flow_access"]["dataset"] == "cems-glofas-forecast"
assert payload["official_issue_time_flow_access"]["issue_time_feature_authorized"] is False
assert payload["official_issue_time_flow_access"]["model_feature_authorized"] is False
assert payload["nonlogin_source_quality"]["status"] == "complete_static_and_rainfall_coverage_with_closed_candidate_gate"
assert payload["nonlogin_source_quality"]["expected_admin1_region_count"] == 18
assert payload["nonlogin_source_quality"]["model_feature_authorized"] is False
assert payload["prospective_validation_readiness"]["status"] == "no_verified_nationwide_prospective_outcomes"
assert payload["prospective_validation_readiness"]["model_evaluation_authorized"] is False
assert payload["candidate_gate"]["status"] == "no_fit_authorized"
assert payload["candidate_gate"]["model_status"] == "not_fitted"
assert payload["candidate_gate"]["fit_authorized"] is False
assert payload["candidate_gate"]["promotion_authorized"] is False
assert "not a forecast" in payload["interpretation"]
assert "probability" not in payload and "prediction" not in payload and "alert" not in payload
print("national evidence endpoint contract passed")
