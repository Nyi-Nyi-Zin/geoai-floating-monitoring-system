"""Audit whether a nationwide regional candidate is authorized to be fitted.

This script intentionally produces a promotion-gate record, not a model. It never
fits, scores, forecasts, classifies, or alerts. Its default outcome is no-fit when
any mandatory issue-time source or prospective-validation prerequisite is absent.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


BASE = Path("/home/ubuntu/deltawatch-model-outputs")
TABLE = BASE / "myanmar_admin1_event_static_feature_table.csv"
MANIFEST = BASE / "myanmar_admin1_event_static_feature_table_manifest.json"
OUTPUT = BASE / "myanmar_admin1_candidate_gate_audit.json"
REPORT = Path("/home/ubuntu/deltawatch-permanent/model_pipeline/myanmar_admin1_region_candidate_gate_audit.md")


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with TABLE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 216:
        raise RuntimeError(f"Expected 216 joined rows, received {len(rows)}")

    by_region: dict[str, dict[str, int | str]] = defaultdict(lambda: {
        "name": "", "development_rows": 0, "development_positives": 0,
        "validation_rows": 0, "validation_positives": 0,
        "holdout_rows": 0, "holdout_positives": 0,
    })
    for row in rows:
        region = by_region[row["admin1_pcode"]]
        region["name"] = row["admin1_name"]
        split = row["temporal_split"]
        region[f"{split}_rows"] = int(region[f"{split}_rows"]) + 1
        if row["observed_flood_presence"] == "1":
            region[f"{split}_positives"] = int(region[f"{split}_positives"]) + 1
    regional_records = []
    for pcode in sorted(by_region):
        region = by_region[pcode]
        evaluable = int(region["development_positives"]) >= 2 and int(region["holdout_rows"]) > 0
        regional_records.append({
            "admin1_pcode": pcode,
            **region,
            "regional_evidence_status": "historical counts sufficient for declared count reporting" if evaluable else "not evaluable",
        })

    source_contract = manifest["input_contract"]
    upstream_flow_present = False
    gauge_or_tide_present = False
    prospective_verified_outcomes_present = False
    gates = [
        {
            "gate": "source_integrity",
            "status": "pass",
            "evidence": "Versioned rainfall, true-polygon historical labels, HydroRIVERS v1, Copernicus DEM GLO-30, and ESA WorldCover 2021 v200 are recorded in the joined manifest.",
        },
        {
            "gate": "temporal_integrity",
            "status": "pass",
            "evidence": "Joined rows preserve the pre-registered development, validation, and frozen 2018 holdout partitions.",
        },
        {
            "gate": "required_issue_time_features",
            "status": "fail_no_fit",
            "evidence": "The joined manifest explicitly records no upstream-flow proxy, local gauge stage, tide, levee, or drainage-capacity source. The frozen protocol requires a documented upstream-flow proxy and latency for a candidate fit.",
        },
        {
            "gate": "regional_evidence",
            "status": "insufficient_for_promotion",
            "evidence": "Historical row counts are reported per region, but only 12 metadata-selected events and two frozen holdout events exist; regional count sufficiency does not establish prospective evaluability.",
        },
        {
            "gate": "holdout_performance",
            "status": "not_run",
            "evidence": "No model fit was authorized, so no threshold, score, calibration, or holdout performance was computed.",
        },
        {
            "gate": "prospective_validation",
            "status": "fail_no_promotion",
            "evidence": "No timestamped nationwide prospective feature feed matched to verified local outcomes is available.",
        },
    ]
    no_fit_reasons = [
        "Mandatory upstream-flow proxy and latency provenance are absent from the issue-time feature contract.",
        "No nationwide prospective feature/outcome validation set exists.",
        "The historical source contains only 12 selected events, with a frozen holdout of two events; this cannot support public nationwide risk output.",
    ]
    payload = {
        "schema": "deltawatch-myanmar-admin1-candidate-gate-audit-v1",
        "fit_authorized": False,
        "promotion_authorized": False,
        "model_artifact_created": False,
        "predictive_output_created": False,
        "joined_table": manifest["schema"],
        "global_inputs": {
            "upstream_flow_present": upstream_flow_present,
            "gauge_or_tide_present": gauge_or_tide_present,
            "prospective_verified_outcomes_present": prospective_verified_outcomes_present,
        },
        "gates": gates,
        "regional_evidence": regional_records,
        "no_fit_reasons": no_fit_reasons,
        "safety": "Monitoring only: this audit produces neither a flood probability nor a risk score, forecast, predicted label, alert, or life-safety decision.",
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    table_rows = "\n".join(
        f"| {item['admin1_pcode']} | {item['name']} | {item['development_positives']} | {item['validation_positives']} | {item['holdout_positives']} | {item['regional_evidence_status']} |"
        for item in regional_records
    )
    gate_rows = "\n".join(f"| {gate['gate']} | {gate['status']} | {gate['evidence']} |" for gate in gates)
    report = f"""# Myanmar Admin 1 Candidate Gate Audit\n\n**Status:** No fit authorized; no nationwide prediction model exists.  \n**Protocol:** `myanmar_nationwide_validation_protocol.md`.  \n**Joined analysis table:** `{TABLE}` (216 event-region rows, 12 historical events, 18 Admin 1 regions).\n\n## Decision\n\nThe static terrain, land-cover, and river-network context is now versioned and joined to leakage-safe pre-event rainfall lags and historical GFD Admin 1 labels. However, the frozen protocol requires an upstream-flow proxy with issue-time/latency provenance and prospective validation against verified outcomes. Both requirements remain absent. Therefore, the process **did not fit a model** and did not compute probabilities, thresholds, forecasts, risk scores, predicted labels, or alerts.\n\n## Gate assessment\n\n| Gate | Status | Evidence |\n|---|---|---|\n{gate_rows}\n\n## Regional historical counts\n\n> Counts below describe historical source coverage. They do not identify a low-risk region, establish local calibration, or authorize a regional prediction output.\n\n| Admin 1 P-code | Region | Development positives | Validation positives | Holdout positives | Historical count status |\n|---|---|---:|---:|---:|---|\n{table_rows}\n\n## Non-promotion reasons\n\n""" + "\n".join(f"- {reason}" for reason in no_fit_reasons) + "\n\n## Safety boundary\n\n**Monitoring only.** This is a source and gate audit. It does not create a flood probability, risk score, forecast, predicted label, alert, or life-safety decision.\n"
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps({"audit": str(OUTPUT), "report": str(REPORT), "fit_authorized": False, "regions": len(regional_records)}, indent=2))


if __name__ == "__main__":
    main()
