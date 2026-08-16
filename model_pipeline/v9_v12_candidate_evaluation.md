# v9–v12 candidate evaluation

## Decision

The production **v7 hydrologic HGB** remains unchanged. Four pre-specified, leakage-safe candidate families were evaluated using the same native GFD labels, chronological split, and 2018 held-out interval. None improved both the 2009–2016 selection interval and the independent 2018 holdout. A candidate that improves only one split is not promoted.

| Candidate family | Best representative | Validation F1 | 2018 F1 | 2018 PR-AUC | 2018 ROC-AUC | Decision |
|---|---|---:|---:|---:|---:|---|
| Production baseline | v7 hydrologic HGB | 0.4933 | 0.1884 | 0.1320 | 0.7088 | Retain |
| Capacity and class-weight regularization | v9 regularized HGB with square-root positive weight | 0.4916 | 0.1998 | 0.1233 | 0.6724 | Do not promote: lower validation F1, PR-AUC, and ROC-AUC |
| Prior-event GFD susceptibility | v10 prior flood rate | 0.5362 | 0.1587 | 0.1102 | 0.6329 | Do not promote: held-out discrimination and F1 worsen |
| Terrain-cell location context | v11 centroid coordinates | 0.4925 | 0.1991 | 0.1308 | 0.7059 | Do not promote: validation F1 and holdout discrimination do not improve |
| Land-cover representation | v12 one-hot land cover | 0.5088 | 0.1836 | 0.1285 | 0.7034 | Do not promote: 2018 F1, PR-AUC, and ROC-AUC worsen |

## Controls and interpretation

All dynamic rainfall and discharge features continue to end before each GFD event begins. The v10 historical-susceptibility experiment excludes every 2018 label from held-out feature construction. The v11 location experiment uses only static centroids from the existing terrain seed. The v12 experiment uses existing ESA WorldCover code representation and arithmetic ratios of already lagged, pre-event values.

> **Promotion gate:** a candidate must improve validation F1 and must not degrade the independent 2018 F1, PR-AUC, or ROC-AUC versus v7. This prevents selecting a model that only fits the validation years more closely.

The CEMS GloFAS historical catalogue confirms that daily root-zone soil-wetness index and runoff water equivalent are available at 0.05° across the required period, but the minimal authorised retrieval probe returned HTTP 403. The candidate remains deferred until the account holder completes the separate EWDS CEMS-FLOODS licence authorization. [1]

## Reproducibility artefacts

| Experiment | Script | Metrics output |
|---|---|---|
| v9 | `train_v9_regularized_candidates.py` | `/home/ubuntu/deltawatch-model-outputs/candidate_metrics_v9_regularization.json` |
| v10 | `train_v10_historical_susceptibility.py` | `/home/ubuntu/deltawatch-model-outputs/candidate_metrics_v10_historical_susceptibility.json` |
| v11 | `train_v11_spatial_location_candidates.py` | `/home/ubuntu/deltawatch-model-outputs/candidate_metrics_v11_spatial_location.json` |
| v12 | `train_v12_feature_representation_candidates.py` | `/home/ubuntu/deltawatch-model-outputs/candidate_metrics_v12_feature_representation.json` |

## References

[1] [CEMS Early Warning Data Store — GloFAS historical hydrological variables](https://ewds.climate.copernicus.eu/datasets/cems-glofas-historical)
