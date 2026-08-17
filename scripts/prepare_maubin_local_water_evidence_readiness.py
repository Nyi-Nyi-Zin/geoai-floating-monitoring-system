"""Prepare a compact Maubin local-water readiness disclosure seed.

This script preserves verified source evidence and known gaps. It does not
calculate water level thresholds, fit models, create predictions, probabilities,
forecasts, alerts, or life-safety decisions.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


OUTPUTS = Path("/home/ubuntu/deltawatch-model-outputs")
PUBLIC_ASSETS = Path("/home/ubuntu/webdev-static-assets")
HISTORICAL_STAGE = OUTPUTS / "nyaungdon_panhlaing_historical_stage_context.json"
OUTPUT = PUBLIC_ASSETS / "maubin_local_water_evidence_readiness_v1.json"


def main() -> None:
    historical = json.loads(HISTORICAL_STAGE.read_text(encoding="utf-8"))
    readiness = {
        "schema": "deltawatch-maubin-local-water-evidence-readiness-v1",
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "Maubin Township monitoring context; nearby Nyaungdon evidence is not treated as a Maubin gauge equivalent.",
        "river_stage": {
            "status": "historical_context_only",
            "historical_context": {
                "available": True,
                "station": historical["geographic_scope"]["station_label"],
                "administrative_context": historical["geographic_scope"]["administrative_context"],
                "record_count": historical["coverage"]["record_count"],
                "coverage_start": historical["coverage"]["first_observed_date"],
                "coverage_end": historical["coverage"]["last_observed_date"],
                "source": historical["source"]["doi"],
            },
            "live_feed_available": False,
            "datum_verified_for_maubin": False,
            "feature_authorized": False,
            "reason": "The published annual Nyaungdon table is historical Maubin-District context. It has no Maubin-equivalent live telemetry, verified common datum, or issue-time lineage.",
        },
        "tide_and_coastal_water": {
            "status": "known_station_no_current_public_data",
            "station": "Haing Gyi Kyun, Myanmar; IOC station code hain",
            "coordinates": {"latitude": 16.0004, "longitude": 94.3176},
            "sensor": "radar; 1-minute sampling declared in station metadata",
            "public_data_status": "IOC tabular endpoint returned NO DATA during the audit",
            "station_status": "Down; IOC list reported a 1933-day delay on 2026-08-17 UTC",
            "datum_verified_for_maubin": False,
            "feature_authorized": False,
            "reason": "No current public samples, no documented common vertical datum, and coastal station data cannot be treated as a Maubin river-stage gauge.",
        },
        "official_network_context": {
            "dmh_hydrology": "DMH documents 22 hydrological stations and three daily water-level observations, but this audit found no verified Maubin/Nyaungdon public download endpoint with live data and datum metadata.",
            "sources": [
                "https://www.moezala.gov.mm/en/bay-bulletin/96",
                "https://www.ioc-sealevelmonitoring.org/station.php?code=hain",
                "https://www.ioc-sealevelmonitoring.org/bgraph.php?code=hain&output=tab&period=0.5",
                "https://doi.org/10.1371/journal.pone.0224558",
            ],
        },
        "candidate_gate": {
            "status": "no_fit_authorized",
            "reason": "No verified Maubin live river-stage, calibrated tide/coastal-water record, common datum, or prospective outcome linkage is available.",
            "model_status": "not_fitted",
            "prediction_authorized": False,
            "alert_authorized": False,
        },
        "safety": "Monitoring only: readiness disclosure only; no stage threshold, model score, probability, prediction, forecast, alert, or life-safety decision.",
    }
    OUTPUT.write_text(json.dumps(readiness, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(readiness, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
