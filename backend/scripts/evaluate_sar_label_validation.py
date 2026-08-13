"""Compare independent Sentinel-1 SAR labels against GFD and the v5 event model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import select, text

from app.db.session import SessionLocal, engine
from app.models.flood_extent import FloodExtent
from scripts.build_flood_event_dataset import (
    FEATURE_NAMES,
    event_target_label,
    load_event_dataset,
)
from scripts.flood_label_sources import LABEL_SOURCE_GFD, LABEL_SOURCE_SAR
from scripts.train_flood_event_model import MODEL_VERSION
from scripts.train_flood_susceptibility import evaluate, sigmoid

DEFAULT_ARTIFACT = Path("artifacts/maubin_flood_event_logistic_v5.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate independent Sentinel-1 SAR flood labels against GFD training "
            "labels and score the existing v5 event model on SAR targets."
        )
    )
    parser.add_argument(
        "--artifact",
        type=Path,
        default=DEFAULT_ARTIFACT,
        help="Trained event-model artifact JSON (default: v5 logistic).",
    )
    parser.add_argument("--target-threshold", type=float, default=0.10)
    parser.add_argument(
        "--label-mode",
        choices=("flood_excess", "flood_extent"),
        default="flood_excess",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/maubin_sar_label_validation.json"),
    )
    return parser.parse_args()


def load_artifact(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("model_version") != MODEL_VERSION:
        raise ValueError(
            f"Expected artifact model_version {MODEL_VERSION!r}, "
            f"got {payload.get('model_version')!r}"
        )
    return payload


def predict_rows(rows: list[dict[str, Any]], artifact: dict[str, Any]) -> np.ndarray:
    feature_names = list(artifact.get("feature_names") or FEATURE_NAMES)
    mean = np.asarray(artifact["mean"], dtype=float)
    scale = np.asarray(artifact["scale"], dtype=float)
    weights = np.asarray(
        artifact.get("weights") or artifact.get("coefficients"),
        dtype=float,
    )
    if weights.size == 0:
        raise KeyError("Artifact is missing 'weights' or 'coefficients'")
    intercept = float(artifact["intercept"])
    matrix = np.asarray(
        [[row[name] for name in feature_names] for row in rows],
        dtype=float,
    )
    normalized = (matrix - mean) / np.where(scale == 0, 1.0, scale)
    logits = normalized @ weights + intercept
    return sigmoid(logits)


def active_threshold(artifact: dict[str, Any], mode: str = "balanced") -> float:
    profiles = artifact.get("metrics", {}).get("threshold_profiles", {})
    profile = profiles.get(mode, {}) if isinstance(profiles, dict) else {}
    threshold = profile.get("threshold")
    if isinstance(threshold, (int, float)):
        return float(threshold)
    return float(artifact.get("decision_threshold") or 0.5)


def index_rows_by_event_cell(
    rows: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(row["event_id"]), str(row["geo_asset_id"])): row for row in rows
    }


def sar_reference_map() -> dict[str, str]:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is required")
    db = SessionLocal()
    try:
        extents = db.scalars(
            select(FloodExtent).where(
                FloodExtent.source_key.like("maubin:sar:event:%")
            )
        ).all()
        mapping: dict[str, str] = {}
        for extent in extents:
            reference = (extent.properties or {}).get("reference_gfd_event_id")
            if reference is not None and extent.event_id is not None:
                mapping[str(reference)] = str(extent.event_id)
        return mapping
    finally:
        db.close()


def label_agreement(
    gfd_row: dict[str, Any],
    sar_row: dict[str, Any],
    *,
    target_threshold: float,
    label_mode: str,
) -> dict[str, float]:
    gfd_fraction = float(gfd_row["flooded_fraction"])
    sar_fraction = float(sar_row["flooded_fraction"])
    gfd_label = event_target_label(
        gfd_row, target_threshold, label_mode=label_mode
    )
    sar_label = event_target_label(
        sar_row, target_threshold, label_mode=label_mode
    )
    return {
        "gfd_fraction": gfd_fraction,
        "sar_fraction": sar_fraction,
        "fraction_delta": abs(gfd_fraction - sar_fraction),
        "gfd_label": float(gfd_label),
        "sar_label": float(sar_label),
        "label_match": float(gfd_label == sar_label),
    }


def summarize_agreement(samples: list[dict[str, float]]) -> dict[str, Any]:
    if not samples:
        return {}
    fraction_delta = np.asarray([item["fraction_delta"] for item in samples])
    label_match = np.asarray([item["label_match"] for item in samples])
    gfd_positive = np.asarray([item["gfd_label"] for item in samples])
    sar_positive = np.asarray([item["sar_label"] for item in samples])
    union = np.clip(gfd_positive + sar_positive, 0, 1)
    intersection = gfd_positive * sar_positive
    iou = float(intersection.sum() / union.sum()) if union.sum() else 0.0
    return {
        "compared_cells": len(samples),
        "mean_fraction_delta": round(float(fraction_delta.mean()), 6),
        "label_agreement_rate": round(float(label_match.mean()), 6),
        "binary_iou": round(iou, 6),
        "gfd_positive_cells": int(gfd_positive.sum()),
        "sar_positive_cells": int(sar_positive.sum()),
    }


def count_label_events(label_source: str) -> int:
    if engine is None:
        raise RuntimeError("DATABASE_URL is required")
    clause = (
        "source_key LIKE 'maubin:gfd:event:%'"
        if label_source == LABEL_SOURCE_GFD
        else "source_key LIKE 'maubin:sar:event:%'"
    )
    query = text(
        f"""
        SELECT COUNT(DISTINCT event_id)
        FROM flood_extents
        WHERE event_id IS NOT NULL
          AND observed_start_date IS NOT NULL
          AND {clause}
        """
    )
    with engine.connect() as connection:
        return int(connection.execute(query).scalar_one())


def run_validation(args: argparse.Namespace) -> dict[str, Any]:
    gfd_count = count_label_events(LABEL_SOURCE_GFD)
    sar_count = count_label_events(LABEL_SOURCE_SAR)
    references = sar_reference_map()
    if sar_count == 0:
        return {
            "status": "awaiting_sar_labels",
            "model_version": MODEL_VERSION,
            "gfd_event_count": gfd_count,
            "sar_event_count": 0,
            "paired_event_count": 0,
            "message": (
                "No SAR labels are stored yet. Export with "
                "scripts/gee_export_maubin_sar_events.js and import with "
                "python -m scripts.import_flood_sar_events."
            ),
        }

    gfd_rows = load_event_dataset(LABEL_SOURCE_GFD)
    sar_rows = load_event_dataset(LABEL_SOURCE_SAR)
    gfd_index = index_rows_by_event_cell(gfd_rows)
    sar_index = index_rows_by_event_cell(sar_rows)
    artifact = load_artifact(args.artifact)
    threshold = active_threshold(artifact, mode="balanced")

    paired_events: list[dict[str, Any]] = []
    for reference_gfd_event_id, sar_event_id in sorted(references.items()):
        gfd_cells = {
            key: row
            for key, row in gfd_index.items()
            if key[0] == reference_gfd_event_id
        }
        sar_cells = {
            key: row for key, row in sar_index.items() if key[0] == sar_event_id
        }
        shared_asset_ids = sorted(
            {asset_id for _, asset_id in gfd_cells} & {asset_id for _, asset_id in sar_cells}
        )
        if not shared_asset_ids:
            continue
        agreement_samples: list[dict[str, float]] = []
        sar_eval_rows: list[dict[str, Any]] = []
        for asset_id in shared_asset_ids:
            gfd_row = gfd_cells[(reference_gfd_event_id, asset_id)]
            sar_row = sar_cells[(sar_event_id, asset_id)]
            agreement_samples.append(
                label_agreement(
                    gfd_row,
                    sar_row,
                    target_threshold=args.target_threshold,
                    label_mode=args.label_mode,
                )
            )
            sar_eval_rows.append(sar_row)

        sar_labels = np.asarray(
            [
                event_target_label(
                    row, args.target_threshold, label_mode=args.label_mode
                )
                for row in sar_eval_rows
            ],
            dtype=float,
        )
        sar_probabilities = predict_rows(sar_eval_rows, artifact)
        sar_metrics = evaluate(sar_labels, sar_probabilities, threshold)
        paired_events.append(
            {
                "reference_gfd_event_id": reference_gfd_event_id,
                "sar_event_id": sar_event_id,
                "event_start_date": str(sar_eval_rows[0]["event_start_date"]),
                "label_agreement": summarize_agreement(agreement_samples),
                "model_vs_sar": {
                    "threshold_mode": "balanced",
                    "decision_threshold": threshold,
                    **sar_metrics,
                },
            }
        )

    aggregate_labels = np.concatenate(
        [
            np.asarray(
                [
                    event_target_label(
                        sar_index[(event["sar_event_id"], asset_id)],
                        args.target_threshold,
                        label_mode=args.label_mode,
                    )
                    for asset_id in sorted(
                        {
                            asset_id
                            for event_id, asset_id in sar_index
                            if event_id == event["sar_event_id"]
                        }
                    )
                ],
                dtype=float,
            )
            for event in paired_events
        ]
    )
    aggregate_probabilities = np.concatenate(
        [
            predict_rows(
                [
                    sar_index[(event["sar_event_id"], asset_id)]
                    for asset_id in sorted(
                        {
                            asset_id
                            for event_id, asset_id in sar_index
                            if event_id == event["sar_event_id"]
                        }
                    )
                ],
                artifact,
            )
            for event in paired_events
        ]
    )
    overall = evaluate(aggregate_labels, aggregate_probabilities, threshold)

    report = {
        "status": "complete",
        "model_version": MODEL_VERSION,
        "label_mode": args.label_mode,
        "target_threshold": args.target_threshold,
        "gfd_event_count": gfd_count,
        "sar_event_count": sar_count,
        "paired_event_count": len(paired_events),
        "overall_model_vs_sar": {
            "threshold_mode": "balanced",
            "decision_threshold": threshold,
            **overall,
        },
        "paired_events": paired_events,
        "interpretation": (
            "SAR labels are independent validation targets. GFD-vs-SAR agreement "
            "shows label noise; model-vs-SAR metrics estimate generalization "
            "without retraining on SAR."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    report = run_validation(parse_args())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
