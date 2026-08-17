"""Add upstream-flow and prospective-validation readiness to the public evidence seed.

This composes monitoring-status disclosures only. It cannot create a prediction,
probability, forecast, risk score, predicted label, alert, or life-safety decision.
"""

from __future__ import annotations

import json
from pathlib import Path


BASE = Path("/home/ubuntu/deltawatch-model-outputs")
INPUT = Path("/home/ubuntu/webdev-static-assets/myanmar_admin1_evidence_readiness_v2.json")
FLOW_SNAPSHOT = BASE / "myanmar_admin1_glofas_readiness_snapshot.json"
OUTPUT = Path("/home/ubuntu/webdev-static-assets/myanmar_admin1_evidence_readiness_v3.json")


def main() -> None:
    base = json.loads(INPUT.read_text(encoding="utf-8"))
    flow = json.loads(FLOW_SNAPSHOT.read_text(encoding="utf-8"))
    records = flow.get("records", [])
    readiness = flow.get("issue_time_readiness", {})
    if base.get("region_count") != 18 or len(records) != 18:
        raise RuntimeError("Expected full 18-region evidence and upstream-flow snapshots")
    if readiness.get("usable_as_issue_time_model_feature") is not False:
        raise RuntimeError("A public readiness seed cannot promote an upstream-flow feature")
    candidate = base.get("candidate_gate", {})
    if candidate.get("fit_authorized") or candidate.get("promotion_authorized"):
        raise RuntimeError("Candidate gate must remain closed for the v3 disclosure")
    payload = {
        **base,
        "schema": "deltawatch-myanmar-admin1-evidence-readiness-v3",
        "upstream_flow_readiness": {
            "status": "bounded_source_snapshot_available_not_authorized_as_issue_time_feature",
            "source": flow.get("source", {}).get("upstream_dataset"),
            "regions_with_source_snapshot": len(records),
            "official_issue_timestamp_present": False,
            "model_feature_authorized": False,
            "reason": readiness.get("reason"),
        },
        "prospective_validation_readiness": {
            "status": "no_verified_nationwide_prospective_outcomes",
            "model_evaluation_authorized": False,
            "reason": "No timestamped nationwide prospective input/outcome set has been matched to verified local flood evidence. The historical source set is not a substitute for prospective validation.",
        },
        "candidate_gate": {
            **candidate,
            "reason": "Bounded GloFAS-backed source availability has been confirmed for all 18 Admin 1 representative locations, but official issue-time lineage and verified nationwide prospective outcomes remain absent. No nationwide candidate was fitted or evaluated.",
        },
        "interpretation": "Historical source coverage, static context, and bounded upstream-flow source availability only; this is not a forecast, risk score, probability, likelihood, or alert. No nationwide candidate model has been fitted.",
        "limits": [
            *base.get("limits", []),
            "The upstream-flow snapshot is a GloFAS-backed source-availability check, not an official retained forecast-run archive or local river-stage observation.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "schema": payload["schema"], "upstream_flow_readiness": payload["upstream_flow_readiness"], "candidate_gate": payload["candidate_gate"]}, indent=2))


if __name__ == "__main__":
    main()
