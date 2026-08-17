"""Summarize observed historical GFD coverage by Myanmar Admin 1.

Readiness is a data-coverage descriptor only. It is not a risk score, flood forecast,
probability, likelihood, or alert, and it must not be used as one.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


SOURCE = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_gfd_admin1_historical_coverage.csv")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_admin1_evidence_readiness.json")


def readiness(observed_events: int, positive_events: int) -> str:
    if observed_events < 4:
        return "insufficient_historical_source_coverage"
    if positive_events < 2:
        return "limited_observed_flood_examples"
    return "historical_source_coverage_only_not_validated_for_prediction"


def main() -> None:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    with SOURCE.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            groups[(row["admin1_pcode"], row["admin1_name"])].append(row)
    regions = []
    for (pcode, name), rows in sorted(groups.items(), key=lambda item: item[0][1]):
        observed = [row for row in rows if row["coverage_status"] == "observed"]
        positive = [row for row in observed if row["observed_flood_presence"] == "1"]
        total_valid = sum(int(row["valid_pixel_count"]) for row in observed)
        total_flooded = sum(int(row["flooded_pixel_count"]) for row in observed)
        regions.append({
            "admin1_pcode": pcode,
            "admin1_name": name,
            "historical_events_considered": len(rows),
            "events_with_valid_source_pixels": len(observed),
            "events_with_observed_flood_pixels": len(positive),
            "aggregate_observed_flood_fraction": round(total_flooded / total_valid, 8) if total_valid else None,
            "evidence_readiness": readiness(len(observed), len(positive)),
        })
    payload = {
        "schema": "deltawatch-myanmar-admin1-evidence-readiness-v1",
        "region_count": len(regions),
        "regions": regions,
        "interpretation": "Historical source-coverage descriptor only; it is not a forecast, risk score, probability, likelihood, or alert.",
        "limits": [
            "Observed event frequency is influenced by source event selection and coverage; it is not a measure of future flood likelihood.",
            "No local gauge, tide, river-stage, or prospective field-evidence validation is included.",
            "A region may have historical coverage but still be unsuitable for a predictive model without leakage-safe features and temporal validation.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    counts: dict[str, int] = defaultdict(int)
    for region in regions:
        counts[str(region["evidence_readiness"])] += 1
    print(json.dumps({"output": str(OUTPUT), "region_count": len(regions), "readiness_counts": dict(counts)}, indent=2))


if __name__ == "__main__":
    main()
