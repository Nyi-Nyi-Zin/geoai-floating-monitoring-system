# Myanmar Nationwide Monitoring Validation Protocol

**Status:** Pre-registered planning protocol; no nationwide model has been fitted.  
**Scope:** Historical GFD source coverage across 18 Admin 1 regions.  
**Safety mode:** Monitoring only. This protocol authorizes neither public flood probabilities nor alerts.

## Dataset boundary

The current historical catalog contains 12 GFD metadata-selected Myanmar/Burma events between 2002 and 2018. The true-Admin-1 observed coverage summary is source evidence only. It is not a cell-level training table, it contains no contemporaneous national terrain/rainfall/river feature matrix, and it does not establish prospective accuracy.

| Temporal role | Event dates | Event IDs | Permitted use |
|---|---|---|---|
| Development | 2002-08-17 to 2008-05-03 | 2041, 2276, 2859, 3068, 3125, 3169, 3302 | Feature-engineering and model-family experimentation after issue-time features exist |
| Validation | 2010-06-15 to 2016-06-01 | 3662, 4283, 4365 | Threshold selection and model comparison only |
| Frozen chronological holdout | 2018-06-15 to 2018-07-15 | 4632, 4666 | One-time, final historical assessment only |

> No observation from the frozen 2018 holdout may influence feature transformations, missing-data rules, hyperparameters, probability thresholds, regional pooling strategy, or model selection.

## Required issue-time feature contract

A candidate may be fitted only when each feature is reproducible as it would have been known at the event issue time. The required contract includes terrain/elevation provenance, land-cover version, river-network version, rainfall-lag source and latency, upstream-flow proxy source and latency, and the exact regional masking rule. Future data, post-event labels, event-extent geometry, and global normalization calculated using holdout dates are prohibited.

## Regional reporting rules

Every candidate must report event-level and Admin-1-level sample counts, positive coverage, missingness, precision, recall, F1, ROC-AUC where defined, calibration diagnostics, and confidence intervals or explicit insufficiency notices. A nationwide aggregate cannot substitute for regional reporting. Regions with fewer than two positive development examples or inadequate holdout coverage remain **not evaluable**, not low risk.

## Promotion gates

| Gate | Required outcome | Failure outcome |
|---|---|---|
| Source integrity | Versioned, documented inputs and true-polygon regional masks | Candidate rejected |
| Temporal integrity | Development, validation, and frozen holdout remain disjoint | Candidate rejected |
| Feature availability | Every input is available at issue time and provenance is retained | Candidate remains historical analysis only |
| Regional evidence | Sufficient region-level events and positives for declared metrics | Region remains not evaluable |
| Holdout performance | Pre-registered criteria met without threshold tuning on holdout | No nationwide probability output |
| Prospective validation | Timestamped prospective inputs matched to verified local outcomes | Monitoring-only status continues until evidence is adequate |

## Explicit prohibitions

The workflow must not publish a nationwide flood-risk score, probability, forecast, alert, or life-safety decision from the current 12-event historical source summary. Historical source coverage and the Maubin v7 metrics cannot be transferred as Myanmar-wide accuracy claims.
