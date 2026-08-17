# Myanmar Rainfall-Only Temporal Baseline Evaluation

**Status:** Rejected diagnostic baseline; not a nationwide prediction model.  
**Protocol:** `myanmar_nationwide_validation_protocol.md`.

| Split | Rows | Events | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| Validation | 52 | 3 | 0.712 | 1.000 | 0.831 | 0.434234 | 0.721246 |
| Frozen 2018 holdout | 35 | 2 | 0.829 | 1.000 | 0.906 | 0.545977 | 0.83261 |

The threshold of **0.20** was selected on the validation period only. The frozen 2018 holdout was not used for threshold selection. Nonetheless, this candidate is **rejected**: it uses centroid rainfall lags only, has too few historical events, omits required hydrologic and static context, and has no prospective local validation. No model artefact, probability, forecast, risk score, or alert has been exported.
