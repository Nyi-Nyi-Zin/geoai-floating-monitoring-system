# Model Card — Maubin Rainfall-Aligned Flood Event Model

**Status:** Experimental historical hindcast (not an operational warning system)  
**Last updated:** 2026-08-12  
**Active version:** `maubin-flood-event-logistic-v5` (unchanged after Priority 4 comparison)

## Intended use

- Historical event hindcast and model evaluation for Maubin Township
- Scenario forecast experimentation using Open-Meteo + ERA5 rainfall features
- **Not** for public emergency alerts, evacuation orders, or life-safety decisions

## Training recipe (v5)

| Setting | Value |
|---|---|
| Algorithm | NumPy L2-regularized logistic regression |
| Label mode | `flood_excess` (inundation beyond permanent water/wetland/mangrove) |
| Target threshold | 0.10 flood-excess fraction |
| Rows | 94,333 event×cell (train 61,039 / val 16,647 / test 16,647) |
| Test positives (excess) | 502 |
| Default mode | conservative |
| Decision threshold | 0.32 |
| Water temper β | 0.50 |
| Positive weight scale | 1.0 |

## Held-out test metrics (v5)

| Mode | Precision | Recall | F1 | FP | TP |
|---|---:|---:|---:|---:|---:|
| screening | 0.0909 | 0.0020 | 0.0039 | 10 | 1 |
| **balanced** | **0.1294** | 0.1673 | 0.1460 | 565 | 84 |
| conservative (default) | 0.0545 | 0.6833 | 0.1010 | 5950 | 343 |

ROC-AUC (conservative): 0.7126 · PR-AUC: 0.0829

### Rolling-origin CV (14 folds, mean)

| Mode | Mean precision | Mean recall |
|---|---:|---:|
| screening | 0.0435 | 0.4494 |
| balanced | 0.0466 | 0.4269 |
| conservative | 0.0400 | 0.5225 |

## Comparison to v2/v3 baseline

| | Baseline (flood_extent, balanced @0.55) | v5 best (flood_excess, balanced) |
|---|---:|---:|
| Precision | **0.1664** | 0.1294 |
| Recall | 0.3941 | 0.1673 |

**Verdict:** False-alarm tooling landed, but **precision did not improve** above 16.6%. Flood-excess labels changed the positive definition (fewer positives), and threshold selection on validation did not generalize to higher test precision. Keep experimental-only.

## Evaluation surfaces

- `GET /api/v1/flood-ml/event-models/evaluation`
- Dashboard Event hindcast → Error map (TP/FP/FN)
- Artifact: `backend/artifacts/maubin_flood_event_logistic_v5.json`

## Priority 4 model comparison (Colab, flood_excess CSV)

Same chronological splits / 502 test positives as v5. Best mode per algorithm:

| Algorithm | Best mode | Precision | Recall | F1 | PR-AUC |
|---|---|---:|---:|---:|---:|
| logistic_sklearn | balanced | 0.0930 | 0.6235 | 0.1619 | 0.1303 |
| **random_forest** | screening | **0.1083** | 0.2968 | 0.1587 | 0.0718 |
| hist_gradient_boosting | conservative | 0.0677 | 0.4482 | 0.1176 | 0.0592 |
| xgboost | balanced | 0.0718 | 0.4283 | 0.1229 | 0.0614 |

Artifact: `backend/artifacts/maubin_flood_event_model_comparison.json`

### vs published baselines

| Reference | Precision |
|---|---:|
| v2/v3 flood_extent balanced | **0.1664** |
| v5 numpy logistic flood_excess balanced | **0.1294** |
| Colab RF best (screening) | 0.1083 |

**Verdict:** Colab did **not** make the product “worse” by training poorly — it
**rejected the hypothesis** that RF/XGBoost alone would raise precision. Under
flood_excess labels + ~500 test positives / limited events, tree models stay in
a similar low-precision band. Likely bottleneck: **data signal / sample size**,
not missing booster architecture.

**Winner selected for integration:** `maubin-flood-event-logistic-v5`

| Reason |
|---|
| Highest practical precision among integrated candidates (12.9% balanced) |
| Explainable, already in API/artifact/DB path |
| RF/XGB/HistGB evaluated and not promoted |

## Deployment recommendation

**Do not escalate to operational alerts. Stop endless model swapping for the MVP.**

Next priorities (in order):

1. **More independent flood labels** (Sentinel-1 SAR / additional events)
2. **Feature expansion** only after labels improve (rain anomaly, wetness, flow accumulation, …)
3. Demo/story polish (map + provenance + limitations) for hackathon judging
4. Auth / sensors / production hardening for pilot readiness
