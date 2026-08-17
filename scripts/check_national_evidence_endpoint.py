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
    "schema": "deltawatch-myanmar-admin1-evidence-readiness-v1",
    "region_count": 1,
    "regions": [{"admin1_pcode": "MMR017", "evidence_readiness": "historical_source_coverage_only_not_validated_for_prediction"}],
    "interpretation": "Historical source-coverage descriptor only; it is not a forecast, risk score, probability, likelihood, or alert.",
    "limits": ["Observed source context only."],
}

response = TestClient(main.app).get("/national-admin/evidence-readiness")
assert response.status_code == 200, response.text
payload = response.json()
assert payload["schema"] == "deltawatch-myanmar-admin1-evidence-readiness-v1"
assert payload["region_count"] == 1
assert payload["regions"][0]["admin1_pcode"] == "MMR017"
assert "not a forecast" in payload["interpretation"]
assert "probability" not in payload and "prediction" not in payload and "alert" not in payload
print("national evidence endpoint contract passed")
