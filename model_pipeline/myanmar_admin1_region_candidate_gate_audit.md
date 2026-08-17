# Myanmar Admin 1 Candidate Gate Audit

**Status:** No fit authorized; no nationwide prediction model exists.  
**Protocol:** `myanmar_nationwide_validation_protocol.md`.  
**Joined analysis table:** `/home/ubuntu/deltawatch-model-outputs/myanmar_admin1_event_static_feature_table.csv` (216 event-region rows, 12 historical events, 18 Admin 1 regions).

## Decision

The static terrain, land-cover, and river-network context is now versioned and joined to leakage-safe pre-event rainfall lags and historical GFD Admin 1 labels. However, the frozen protocol requires an upstream-flow proxy with issue-time/latency provenance and prospective validation against verified outcomes. Both requirements remain absent. Therefore, the process **did not fit a model** and did not compute probabilities, thresholds, forecasts, risk scores, predicted labels, or alerts.

## Gate assessment

| Gate | Status | Evidence |
|---|---|---|
| source_integrity | pass | Versioned rainfall, true-polygon historical labels, HydroRIVERS v1, Copernicus DEM GLO-30, and ESA WorldCover 2021 v200 are recorded in the joined manifest. |
| temporal_integrity | pass | Joined rows preserve the pre-registered development, validation, and frozen 2018 holdout partitions. |
| required_issue_time_features | fail_no_fit | The joined manifest explicitly records no upstream-flow proxy, local gauge stage, tide, levee, or drainage-capacity source. The frozen protocol requires a documented upstream-flow proxy and latency for a candidate fit. |
| regional_evidence | insufficient_for_promotion | Historical row counts are reported per region, but only 12 metadata-selected events and two frozen holdout events exist; regional count sufficiency does not establish prospective evaluability. |
| holdout_performance | not_run | No model fit was authorized, so no threshold, score, calibration, or holdout performance was computed. |
| prospective_validation | fail_no_promotion | No timestamped nationwide prospective feature feed matched to verified local outcomes is available. |

## Regional historical counts

> Counts below describe historical source coverage. They do not identify a low-risk region, establish local calibration, or authorize a regional prediction output.

| Admin 1 P-code | Region | Development positives | Validation positives | Holdout positives | Historical count status |
|---|---|---:|---:|---:|---|
| MMR001 | Kachin | 6 | 3 | 2 | historical counts sufficient for declared count reporting |
| MMR002 | Kayah | 2 | 0 | 1 | historical counts sufficient for declared count reporting |
| MMR003 | Kayin | 4 | 2 | 1 | historical counts sufficient for declared count reporting |
| MMR004 | Chin | 5 | 1 | 2 | historical counts sufficient for declared count reporting |
| MMR005 | Sagaing | 6 | 3 | 2 | historical counts sufficient for declared count reporting |
| MMR006 | Tanintharyi | 1 | 0 | 0 | not evaluable |
| MMR007 | Bago (East) | 7 | 2 | 2 | historical counts sufficient for declared count reporting |
| MMR008 | Bago (West) | 7 | 3 | 2 | historical counts sufficient for declared count reporting |
| MMR009 | Magway | 6 | 3 | 2 | historical counts sufficient for declared count reporting |
| MMR010 | Mandalay | 6 | 3 | 2 | historical counts sufficient for declared count reporting |
| MMR011 | Mon | 7 | 2 | 1 | historical counts sufficient for declared count reporting |
| MMR012 | Rakhine | 4 | 3 | 2 | historical counts sufficient for declared count reporting |
| MMR013 | Yangon | 7 | 3 | 2 | historical counts sufficient for declared count reporting |
| MMR014 | Shan (South) | 7 | 2 | 2 | historical counts sufficient for declared count reporting |
| MMR015 | Shan (North) | 6 | 2 | 2 | historical counts sufficient for declared count reporting |
| MMR016 | Shan (East) | 0 | 0 | 0 | not evaluable |
| MMR017 | Ayeyarwady | 7 | 3 | 2 | historical counts sufficient for declared count reporting |
| MMR018 | Nay Pyi Taw | 6 | 2 | 2 | historical counts sufficient for declared count reporting |

## Non-promotion reasons

- Mandatory upstream-flow proxy and latency provenance are absent from the issue-time feature contract.
- No nationwide prospective feature/outcome validation set exists.
- The historical source contains only 12 selected events, with a frozen holdout of two events; this cannot support public nationwide risk output.

## Safety boundary

**Monitoring only.** This is a source and gate audit. It does not create a flood probability, risk score, forecast, predicted label, alert, or life-safety decision.
