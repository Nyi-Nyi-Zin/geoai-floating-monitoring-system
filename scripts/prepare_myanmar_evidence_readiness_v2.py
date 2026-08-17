"""Merge historical evidence readiness with the nationwide static-context gate audit.

This emits a disclosure seed only. It does not calculate or expose a prediction,
probability, forecast, risk score, predicted label, alert, or life-safety decision.
"""

from __future__ import annotations

import json
from pathlib import Path


BASE = Path("/home/ubuntu/deltawatch-model-outputs")
INPUT = BASE / "myanmar_admin1_evidence_readiness.json"
GATE_AUDIT = BASE / "myanmar_admin1_candidate_gate_audit.json"
OUTPUT = Path("/home/ubuntu/webdev-static-assets/myanmar_admin1_evidence_readiness_v2.json")


def main() -> None:
    base = json.loads(INPUT.read_text(encoding="utf-8"))
    audit = json.loads(GATE_AUDIT.read_text(encoding="utf-8"))
    if base.get("region_count") != 18 or len(base.get("regions", [])) != 18:
        raise RuntimeError("Expected 18 historical evidence-readiness regions")
    if audit.get("fit_authorized") or audit.get("promotion_authorized"):
        raise RuntimeError("A public disclosure seed must not be built from an authorized candidate")
    payload = {
        **base,
        "schema": "deltawatch-myanmar-admin1-evidence-readiness-v2",
        "static_context": {
            "status": "versioned_admin1_static_context_complete",
            "sources": [
                "HydroRIVERS v1 Asia true-polygon descriptors",
                "Copernicus DEM GLO-30 bounded Admin 1 overview summaries",
                "ESA WorldCover 2021 v200 bounded Admin 1 overview summaries",
            ],
            "interpretation": "Static geographical context has been prepared for historical analysis; it is not an operational flood input or prediction result.",
        },
        "candidate_gate": {
            "status": "no_fit_authorized",
            "model_status": "not_fitted",
            "fit_authorized": False,
            "promotion_authorized": False,
            "reason": "The frozen protocol requires issue-time upstream-flow provenance and prospective validation against verified outcomes. Both are absent, so no nationwide candidate was fitted or evaluated.",
            "required_before_reconsideration": [
                "Documented issue-time upstream-flow proxy with latency and full regional coverage",
                "Timestamped nationwide prospective inputs matched to verified local outcomes",
                "A new protocol-compliant fit that preserves the frozen 2018 holdout and passes every promotion gate",
            ],
        },
        "interpretation": "Historical source coverage and static context only; this is not a forecast, risk score, probability, likelihood, or alert. No nationwide candidate model has been fitted.",
        "limits": [
            *base.get("limits", []),
            "Static terrain, land-cover, and river-network context does not replace upstream-flow, river-stage, tide, drainage, levee, or prospective-outcome evidence.",
            "The candidate gate audit explicitly prohibits a model fit and any nationwide predictive output at this stage.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "schema": payload["schema"], "candidate_gate": payload["candidate_gate"]}, indent=2))


if __name__ == "__main__":
    main()
