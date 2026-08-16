# Six-hour prospective monitoring validation protocol

## Purpose and operating boundary

DeltaWatch now records timestamped **future-time v7 feature inputs** every six hours. This workflow is a prospective data-quality and model-readiness log; it does **not** compute, display, or deliver flood probabilities, predicted labels, alerts, or life-safety decisions. The existing historical v7 hindcast remains the only model result visible in the dashboard.

Open-Meteo provides hourly forecast precipitation and soil-moisture values, while its Flood API supplies daily GloFAS river-discharge proxy forecasts. The Flood API documentation cautions that the 5 km grid can select a nearby river, which is why the discharge source is retained as a proxy rather than a local gauge. [1] [2]

## Initial monitoring record

The bootstrap run recorded issue key `2026081618Z` at `2026-08-16T18:00:00Z`. It created eight target-date records for 16–23 August 2026. Every target record records the full 5,549-cell static v7 context together with forecast-derived rainfall and discharge lags through a versioned, managed static seed.

| Control | Required state | Initial result |
|---|---|---|
| Schedule cadence | UTC every six hours | Enabled: `0 0 */6 * * *` |
| Input lineage | Issue key, issue time, target date, source coverage | Persisted in `prospective_forecast_snapshots` |
| Per-cell context | 5,549 terrain, land-cover, drainage, levee, and waterway vectors | 5,549 model-ready feature vectors materializable per target |
| Dynamic context | Forecast rainfall and GloFAS discharge lags | Persisted for 1, 3, 7, 14, and 30-day windows |
| Forecast uncertainty context | GloFAS p25/p75 and deep soil moisture when available | Persisted with each target record |
| Safety state | No probability, no predicted label, no alert | Enforced by code and quality flags |

## Quality gates

Each record is accepted only when the static seed matches `maubin-flood-event-hgb-v7`, contains 5,549 cells, and reconstructs the full per-cell feature vector. The record preserves quality flags including `monitoring_only_no_flood_probability`, `no_validated_local_stage_or_tide`, `glofas_discharge_proxy_5km`, and `prospective_validation_pending`.

> A successful refresh proves only that inputs and feature vectors were available at the recorded issue time. It does **not** prove flood-prediction accuracy.

## Prospective validation and promotion rules

For every target date, retain the immutable issue record before the date occurs. After the target interval, compare the input record to independently verified flood outcomes. Valid outcomes must be local field observations, quality-controlled gauge records, or future independently verified flood labels; forecast-derived values cannot serve as their own validation labels.

| Evaluation requirement | Current status | Promotion consequence |
|---|---|---|
| Repeated six-hour snapshot retention | Started | Continue collecting |
| Local river stage spanning prospective events | Missing | Blocks live probability promotion |
| Maubin-calibrated tide/surge evidence | Missing | Blocks coastal influence promotion |
| Independent prospective flood outcomes | Missing | Blocks accuracy claims |
| Prospective precision, recall, PR-AUC, ROC-AUC, calibration evaluation | Not yet possible | Blocks operational alerting |

The dashboard therefore remains **Monitoring only** until a sufficient prospective evaluation window has been collected and independently evaluated. Any later probability output must be a separately reviewed release with a new model card, documented metrics, and explicit governance approval.

## References

[1] [Open-Meteo Weather Forecast API](https://open-meteo.com/en/docs)

[2] [Open-Meteo Global Flood API](https://open-meteo.com/en/docs/flood-api)
