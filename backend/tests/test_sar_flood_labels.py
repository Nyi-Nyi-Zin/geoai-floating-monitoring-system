"""Tests for Sentinel-1 SAR flood label import and provenance filtering."""

from __future__ import annotations

from datetime import date

import pytest

from scripts.flood_label_sources import (
    LABEL_SOURCE_GFD,
    LABEL_SOURCE_SAR,
    label_source_sql_clause,
    normalize_label_source,
)
from scripts.import_flood_sar_events import consistent_sar_event_properties


def test_label_source_sql_clause_filters_by_prefix() -> None:
    assert "maubin:gfd:event:" in label_source_sql_clause(LABEL_SOURCE_GFD)
    assert "maubin:sar:event:" in label_source_sql_clause(LABEL_SOURCE_SAR)
    assert label_source_sql_clause("all") == ""


def test_normalize_label_source_rejects_unknown_values() -> None:
    with pytest.raises(ValueError, match="Unsupported label_source"):
        normalize_label_source("modis")


def test_sar_event_metadata_accepts_alias_property_names() -> None:
    collection = {
        "features": [
            {
                "properties": {
                    "event_start_date": "2015-08-09",
                    "event_end_date": "2015-08-14",
                    "polarization": "VH",
                    "vh_threshold_db": -3.0,
                    "resolution_m": 30,
                }
            }
        ]
    }

    metadata = consistent_sar_event_properties("sar-4666", collection)

    assert metadata["sar_polarization"] == "VH"
    assert metadata["sar_vh_threshold_db"] == -3.0
    assert metadata["processing_scale_m"] == 30
    assert metadata["reference_gfd_event_id"] == "4666"


def test_sar_event_metadata_is_consistent() -> None:
    collection = {
        "features": [
            {
                "properties": {
                    "event_start_date": "2015-08-09",
                    "event_end_date": "2015-08-14",
                    "reference_gfd_event_id": "4666",
                    "label_method": "vh_change_detection",
                }
            },
            {
                "properties": {
                    "event_start_date": "2015-08-09",
                    "event_end_date": "2015-08-14",
                    "reference_gfd_event_id": "4666",
                    "label_method": "vh_change_detection",
                }
            },
        ]
    }

    metadata = consistent_sar_event_properties("sar-4666", collection)

    assert metadata["event_id"] == "sar-4666"
    assert metadata["reference_gfd_event_id"] == "4666"
    assert metadata["label_source"] == LABEL_SOURCE_SAR


def test_sar_event_metadata_rejects_mixed_dates() -> None:
    with pytest.raises(ValueError, match="inconsistent"):
        consistent_sar_event_properties(
            "sar-4666",
            {
                "features": [
                    {
                        "properties": {
                            "event_start_date": "2015-08-09",
                            "event_end_date": "2015-08-14",
                        }
                    },
                    {
                        "properties": {
                            "event_start_date": "2015-08-10",
                            "event_end_date": "2015-08-14",
                        }
                    },
                ]
            },
        )


def test_summarize_agreement_handles_empty_samples() -> None:
    from scripts.evaluate_sar_label_validation import summarize_agreement

    assert summarize_agreement([]) == {}


def test_summarize_agreement_computes_binary_iou() -> None:
    from scripts.evaluate_sar_label_validation import summarize_agreement

    summary = summarize_agreement(
        [
            {"fraction_delta": 0.1, "label_match": 1.0, "gfd_label": 1.0, "sar_label": 1.0},
            {"fraction_delta": 0.2, "label_match": 0.0, "gfd_label": 1.0, "sar_label": 0.0},
            {"fraction_delta": 0.0, "label_match": 1.0, "gfd_label": 0.0, "sar_label": 0.0},
        ]
    )

    assert summary["compared_cells"] == 3
    assert summary["gfd_positive_cells"] == 2
    assert summary["sar_positive_cells"] == 1
    assert 0.0 <= summary["binary_iou"] <= 1.0
