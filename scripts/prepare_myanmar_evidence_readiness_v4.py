"""Compose nationwide monitoring-readiness disclosures from verified non-login artefacts.

This generator never fits a model or emits a probability, score, prediction,
forecast, alert, or life-safety decision.
"""

from __future__ import annotations

import json
from pathlib import Path


BASE = Path("/home/ubuntu/deltawatch-model-outputs")
INPUT = Path("/home/ubuntu/webdev-static-assets/myanmar_admin1_evidence_readiness_v3.json")
MANIFEST = BASE / "myanmar_nonlogin_source_quality_manifest.json"
OUTPUT = Path("/home/ubuntu/webdev-static-assets/myanmar_admin1_evidence_readiness_v4.json")


def main() -> None:
    base = json.loads(INPUT.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    probe = manifest.get("ewds_issue_time_probe", {})
    gate = manifest.get("candidate_gate", {})
    complete_sources = [item for item in manifest.get("sources", []) if item.get("region_coverage_complete")]
    if manifest.get("expected_admin1_region_count") != 18 or len(complete_sources) < 4:
        raise RuntimeError("Expected complete non-login coverage evidence for four nationwide source families")
    if probe.get("status") != "access_blocked" or probe.get("blocker") != "dataset_terms_not_accepted":
        raise RuntimeError("Expected the sanitized EWDS terms-acceptance blocker")
    if probe.get("issue_time_feature_authorized") or gate.get("promotion_authorized"):
        raise RuntimeError("Non-login readiness may not authorize a model feature or candidate promotion")
    payload = {
        **base,
        "schema": "deltawatch-myanmar-admin1-evidence-readiness-v4",
        "official_issue_time_flow_access": {
            "status": "access_blocked_dataset_terms_not_accepted",
            "dataset": "cems-glofas-forecast",
            "issue_time_feature_authorized": False,
            "model_feature_authorized": False,
            "reason": "The bounded official EWDS GloFAS forecast probe returned a dataset-terms-not-accepted blocker. Login and CEMS-FLOODS licence acceptance are intentionally excluded from this continuation.",
        },
        "nonlogin_source_quality": {
            "status": "complete_static_and_rainfall_coverage_with_closed_candidate_gate",
            "expected_admin1_region_count": manifest["expected_admin1_region_count"],
            "complete_source_families": [item["artefact"] for item in complete_sources],
            "model_feature_authorized": False,
            "reason": "Rainfall lags and static context cover all 18 Admin 1 regions, but source coverage is not sufficient to fit or promote a nationwide candidate without authorized official issue-time flow lineage and verified prospective outcomes.",
        },
        "candidate_gate": {
            **base.get("candidate_gate", {}),
            "status": "no_fit_authorized",
            "model_status": "not_fitted",
            "fit_authorized": False,
            "promotion_authorized": False,
            "reason": "The verified official EWDS issue-time flow probe is blocked pending manual dataset-terms acceptance, and no verified nationwide prospective outcomes are matched. No nationwide candidate was fitted or evaluated.",
        },
        "interpretation": "Historical source coverage, static context, non-login source-quality audit, and a sanitized official-access blocker only; this is not a forecast, risk score, probability, likelihood, or alert. No nationwide candidate model has been fitted.",
        "limits": [
            *base.get("limits", []),
            "Official EWDS GloFAS issue-time forecast access remains blocked until an authorized user accepts the CEMS-FLOODS dataset terms; no login bypass was attempted.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "schema": payload["schema"], "official_issue_time_flow_access": payload["official_issue_time_flow_access"], "nonlogin_source_quality": payload["nonlogin_source_quality"], "candidate_gate": payload["candidate_gate"]}, indent=2))


if __name__ == "__main__":
    main()
