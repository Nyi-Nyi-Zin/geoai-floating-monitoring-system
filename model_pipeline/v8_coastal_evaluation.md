# v8 coastal-proxy evaluation

## Scope and evidence

This experiment evaluates whether an authorised coastal forcing proxy improves the experimental Maubin flood hindcast. It supplements the unchanged v7 terrain, rainfall-lag, GloFAS discharge-proxy, and OpenStreetMap infrastructure features with GTSM-ERA5-E daily maxima. The GTSM data were requested through the Copernicus Climate Data Store using the reanalysis experiment, version v3, and the `storm_surge_residual` and `total_water_level` outputs. [1] [2]

The nearest valid GTSM node to Maubin is **16.1870° N, 95.8450° E**, 0.57695° from the model reference point. It is a modelled coastal node, not a local river-stage gauge. All 17 historical event windows have complete one-to-three-day pre-event coverage. The experiment deliberately does **not** present the total-water-level series as a local observed tide measurement, and it does not derive a separate tide maximum from the returned daily-maximum files.

| Feature family | Definition | Leakage control |
|---|---|---|
| Coastal total water | One-day value and three-day maximum from GTSM daily maximum total water level. | Values end on the calendar day before event start. |
| Coastal surge | One-day value and three-day maximum from GTSM storm-surge residual. | Values end on the calendar day before event start. |
| Training label | Native GFD flood pixels with permanent water excluded. | Labels are never exposed as predictors. |

## Chronological result

Candidate architecture and threshold were selected using the 2009–2016 validation interval. The 2018 events remain a common held-out test. The v8 coastal HGB improves held-out F1 and recall but **does not** beat the unchanged v7 HGB on the validation-selection criterion, PR-AUC, or ROC-AUC. The coastal proxy is also materially distant from Maubin. It is therefore **not promoted** to the production dashboard.

| Model | Validation F1 | 2018 F1 | 2018 precision | 2018 recall | 2018 PR-AUC | 2018 ROC-AUC | 2018 Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| Production v7 hydrologic HGB | 0.4933 | 0.1884 | 0.1574 | 0.2346 | 0.1320 | 0.7088 | 0.1411 |
| v8 coastal logistic | 0.3398 | 0.0297 | 0.0174 | 0.1012 | 0.0499 | 0.3237 | 0.5429 |
| v8 coastal HGB | 0.4414 | 0.2169 | 0.1436 | 0.4432 | 0.1257 | 0.6893 | 0.1376 |
| v8 coastal random forest | 0.4021 | 0.1929 | 0.1197 | 0.4963 | 0.1185 | 0.6199 | 0.1497 |

> **Decision:** retain the current v7 experimental model in production. The retrieved GTSM series is a valuable validated research input, but the present evidence does not justify presenting it as a superior deployed Maubin model or as a life-safety alert signal.

## Next evidence requirement

A future candidate should be considered only after obtaining a Maubin- or Nyaungdon-near gauge or a locally calibrated hydrodynamic relationship, then repeating the same chronological comparison. The v8 scripts and the external authorised source archives remain reproducible research artefacts; they are not included in the deployed web image.

## References

[1] [Copernicus Climate Data Store — Global sea level change time series from 1950 to 2050](https://doi.org/10.24381/cds.a6d42d60)

[2] [Copernicus Climate Data Store — CDS API setup](https://cds.climate.copernicus.eu/how-to-api)
