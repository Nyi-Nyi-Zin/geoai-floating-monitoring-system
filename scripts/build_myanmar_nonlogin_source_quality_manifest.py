"""Build a non-predictive quality manifest from existing nationwide artefacts.

The manifest reports provenance, coverage, freshness metadata, missingness, and
feature-authorization state only. It never fits a model or emits predictions,
probabilities, risk scores, forecasts, alerts, or predicted labels.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path("/home/ubuntu/deltawatch-model-outputs")
OUT = ROOT / "myanmar_nonlogin_source_quality_manifest.json"
EXPECTED_REGIONS = 18


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def region_count(payload: dict) -> int | None:
    for key in ("region_count", "regions"):
        value = payload.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, list):
            return len(value)
    return None


def region_pcodes(payload: dict) -> set[str]:
    rows = payload.get("regions") or payload.get("records") or []
    return {str(row.get("admin1_pcode")) for row in rows if isinstance(row, dict) and row.get("admin1_pcode")}


def file_record(name: str, source: str, role: str, authorization: str, limit: str) -> dict:
    path = ROOT / name
    payload = load(name) if path.suffix == ".json" else None
    count = region_count(payload) if payload else None
    pcodes = sorted(region_pcodes(payload)) if payload else []
    return {
        "artefact": name,
        "source": source,
        "role": role,
        "file_bytes": path.stat().st_size,
        "region_count": count,
        "region_coverage_complete": count == EXPECTED_REGIONS if count is not None else None,
        "region_pcodes": pcodes,
        "missing_region_count": EXPECTED_REGIONS - count if count is not None else None,
        "model_feature_authorized": authorization == "authorized",
        "authorization": authorization,
        "limits": limit,
    }


def rainfall_lag_record() -> dict:
    path = ROOT / "myanmar_admin1_event_rainfall_lags.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    pcodes = sorted({row.get("admin1_pcode", "") for row in rows if row.get("admin1_pcode")})
    return {
        "artefact": path.name,
        "source": "ERA5-based daily rainfall history and leakage-safe event lag builder",
        "role": "pre-event temporal preparation and observed-label join input",
        "file_bytes": path.stat().st_size,
        "row_count": len(rows),
        "region_count": len(pcodes),
        "region_coverage_complete": len(pcodes) == EXPECTED_REGIONS,
        "region_pcodes": pcodes,
        "missing_region_count": EXPECTED_REGIONS - len(pcodes),
        "model_feature_authorized": False,
        "authorization": "preparation_only_until_candidate_gate",
        "limits": "Temporal table is leakage-safe preparation; no nationwide candidate is fitted.",
    }


def main() -> None:
    ewds_probe = load("myanmar_ewds_glofas_issue_time_probe.json")
    sources = [
        rainfall_lag_record(),
        file_record("myanmar_admin1_glofas_readiness_snapshot.json", "Open-Meteo Flood API / GloFAS-backed bounded source snapshot", "flow source availability context", "not_authorized", "No official issue timestamp or retained forecast-run identifier; not an issue-time model feature."),
        file_record("myanmar_admin1_copernicus_dem_static.json", "Copernicus DEM GLO-30 Public 2021", "static terrain context", "static_context_only", "Digital surface model and coarse overview aggregation; no hydraulic or current-flood information."),
        file_record("myanmar_admin1_worldcover_static.json", "ESA WorldCover 2021 v200", "static land-cover context", "static_context_only", "Dominant categorical class only; not a dynamic land-use update or flood label."),
        file_record("myanmar_admin1_hydrorivers_static.json", "HydroRIVERS Asia v1", "static river-network context", "static_context_only", "No current stage, local drainage, levee condition, or small-channel completeness."),
    ]
    manifest = {
        "schema": "deltawatch-myanmar-nonlogin-source-quality-manifest-v1",
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "expected_admin1_region_count": EXPECTED_REGIONS,
        "sources": sources,
        "ewds_issue_time_probe": {
            "artefact": "myanmar_ewds_glofas_issue_time_probe.json",
            "status": ewds_probe.get("access_status"),
            "blocker": ewds_probe.get("blocker"),
            "issue_time_feature_authorized": False,
            "model_feature_authorized": False,
            "limits": "EWDS login and CEMS-FLOODS licence acceptance are intentionally excluded from this continuation.",
        },
        "candidate_gate": {
            "status": "no_fit_authorized",
            "model_status": "not_fitted",
            "promotion_authorized": False,
            "reason": "No verified nationwide prospective outcomes and no authorized official issue-time flow lineage.",
        },
        "safety": "Monitoring only: quality and provenance audit only; no scores, probabilities, predictions, forecasts, alerts, or life-safety decisions.",
    }
    OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
