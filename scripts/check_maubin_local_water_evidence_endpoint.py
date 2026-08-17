"""Check the public Maubin local-water readiness endpoint contract."""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import spatial_api.main as main


def main_check() -> None:
    main.maubin_local_water_evidence_readiness_seed.cache_clear()
    main.maubin_local_water_evidence_readiness_seed = lambda: {
        "schema": "deltawatch-maubin-local-water-evidence-readiness-v1",
        "scope": "Maubin Township monitoring context",
        "river_stage": {"status": "historical_context_only", "live_feed_available": False, "feature_authorized": False},
        "tide_and_coastal_water": {"status": "known_station_no_current_public_data", "feature_authorized": False},
        "official_network_context": {"dmh_hydrology": "Documented network; no verified public live endpoint."},
        "candidate_gate": {"status": "no_fit_authorized", "prediction_authorized": False, "alert_authorized": False},
        "safety": "Monitoring only: no stage threshold, model score, probability, prediction, forecast, alert, or life-safety decision.",
    }
    response = TestClient(main.app).get("/maubin/local-water-evidence-readiness")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "deltawatch-maubin-local-water-evidence-readiness-v1"
    assert payload["river_stage"]["status"] == "historical_context_only"
    assert payload["tide_and_coastal_water"]["status"] == "known_station_no_current_public_data"
    assert payload["candidate_gate"]["status"] == "no_fit_authorized"
    assert payload["candidate_gate"]["prediction_authorized"] is False
    assert payload["candidate_gate"]["alert_authorized"] is False
    assert all(key not in payload for key in ("score", "probability", "prediction", "forecast", "alert"))
    assert "no stage threshold" in payload["safety"]
    print("maubin-local-water-evidence-endpoint-contract: ok")


if __name__ == "__main__":
    main_check()
