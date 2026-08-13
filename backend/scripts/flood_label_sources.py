"""Shared constants and SQL filters for flood-event label provenance."""

from __future__ import annotations

from typing import Literal

LabelSource = Literal["gfd", "sar", "all"]

LABEL_SOURCE_GFD: LabelSource = "gfd"
LABEL_SOURCE_SAR: LabelSource = "sar"
LABEL_SOURCE_ALL: LabelSource = "all"

SOURCE_KEY_PREFIX: dict[LabelSource, str | None] = {
    LABEL_SOURCE_GFD: "maubin:gfd:event:",
    LABEL_SOURCE_SAR: "maubin:sar:event:",
    LABEL_SOURCE_ALL: None,
}

SENSOR_BY_SOURCE: dict[LabelSource, str | None] = {
    LABEL_SOURCE_GFD: "Terra/Aqua MODIS",
    LABEL_SOURCE_SAR: "Sentinel-1",
    LABEL_SOURCE_ALL: None,
}


def normalize_label_source(label_source: str) -> LabelSource:
    normalized = label_source.strip().lower()
    if normalized not in SOURCE_KEY_PREFIX:
        supported = ", ".join(key for key in SOURCE_KEY_PREFIX if key != LABEL_SOURCE_ALL)
        raise ValueError(
            f"Unsupported label_source {label_source!r}; expected one of: {supported}, all"
        )
    return normalized  # type: ignore[return-value]


def label_source_sql_clause(label_source: LabelSource) -> str:
    """Return an AND clause restricting flood_extents rows by label provenance."""
    prefix = SOURCE_KEY_PREFIX[label_source]
    if prefix is None:
        return ""
    return f"AND source_key LIKE '{prefix}%'"
