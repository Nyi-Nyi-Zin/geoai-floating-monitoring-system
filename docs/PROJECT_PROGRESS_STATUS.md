# FloodGuard Myanmar Project Progress Status

**Date:** 2026-08-11  
**Scope:** Maubin Township floating monitoring / flood GeoAI MVP

This document is a short operational summary of what is already done, what is
usable right now, and what still remains.

## 1. Overall Status

- **Project stage:** Hackathon MVP
- **Current maturity:** Historical intelligence and dashboard are usable
- **Newly operational:** Live flood scenario forecast (experimental)
- **Not yet operational:** Real sensor deployment and production hardening

## 2. What Is Done

| Area | Status | Notes |
|---|---|---|
| FastAPI backend | Done | Health, Swagger, versioned API, request IDs, validation, structured errors |
| PostgreSQL + PostGIS | Done | Spatial assets, observations, extents, model records, migrations |
| Maubin boundary | Done | Township boundary loaded and used for clipping / map extent |
| OSM waterways | Done | River and canal network loaded for analysis and map display |
| Terrain pipeline | Done | Copernicus DEM processed into 500 m terrain cells |
| Land cover | Done | ESA WorldCover summary available per terrain cell |
| Historical rainfall | Done | ERA5 daily history API and dashboard windows |
| Flood extent labels | Done | Historical flood polygons stored in PostGIS |
| Susceptibility screening | Done | Rule-based relative terrain score works |
| ML susceptibility baseline | Done | Historical probability layer and model metrics are available |
| Rainfall-aligned event ML | Done / experimental | Historical event hindcast layer is available |
| Dashboard UI | Done | 2D, 3D, and Cesium views, plus overlays and inspectors |
| Sensor API foundation | Done | Stations, readings, MQTT bridge, WebSocket live channel |
| Sensor simulator | Done | Demo-only local simulator can publish sample readings |
| Data provenance layer | Done | Sources, limitations, and licences are surfaced |

## 3. What Can Be Used Now

- Interactive dashboard for Maubin terrain, waterways, land cover, and flood history
- Terrain-based susceptibility screening for relative prioritization
- Historical ML probability layer for analysis
- Experimental historical event hindcast for past-event evaluation
- Rainfall forecast and rainfall history views
- Sensor ingestion and live update plumbing for future stations
- Demo sensor simulator for local testing

## 4. What Is Not Done Yet

| Area | Status | Notes |
|---|---|---|
| Live flood forecast | Done | Experimental scenario forecast with Open-Meteo + ERA5 hybrid rainfall |
| Flood depth / arrival time | Not done | Hydraulic model or data still needed |
| Real physical sensors | Not done | No deployed station data in production use |
| Sensor QA workflow | Not done | Calibration, maintenance, drift, battery checks still needed |
| Authentication / authorization | Not done | MVP endpoints are still unauthenticated |
| Alert escalation workflow | Not done | No full production messaging / override pipeline |
| Production deployment | Not done | Hosting, secrets, CI/CD, backup, monitoring still needed |
| Model monitoring | Not done | Drift monitoring and retraining approval not yet in place |
| Public launch readiness | Not done | Licence and operational requirements still need review |

## 5. Priority Next Work

1. ~~Live forecast inference contract~~ ✅ Done
2. ~~Dashboard forecast layer integration~~ ✅ Done
3. ~~Model evaluation tooling & false-alarm controls~~ ✅ Done (v5)
   - Eval API, rolling CV, FP/FN map, flood-excess labels, water temper
   - **Precision target not met:** best v5 balanced precision **12.9%** vs baseline **16.6%**
4. ~~Model comparison (RF / XGBoost)~~ ✅ Done (Colab)
   - Hypothesis *"XGBoost/RF will raise precision"* was **tested and rejected**
   - Suite best: Random Forest **P=10.8%** (still below active v5 **12.9%** and flood_extent **16.6%**)
   - Interpretation: likely **data/signal limit**, not a missing tree-model architecture
   - **Winner kept:** `maubin-flood-event-logistic-v5` (explainable, integrated, most stable of evaluated set)
5. Independent SAR / more flood-event labels (highest leverage for precision)
   - Pipeline ready: `gee_export_maubin_sar_events.js` → `import_flood_sar_events` → `evaluate_sar_label_validation`
   - **Awaiting:** Earth Engine export + import (user action)
6. Optional feature expansion (rain anomaly, wetness, flow accumulation, …)
7. Auth / sensors / production hardening — for operational readiness, not hackathon score chase

## 6. Short Conclusion

Hackathon MVP should **stop endless model tuning**. Logistic / RF / XGBoost / HistGB
are all evaluated; none beat the flood_extent baseline precision bar under flood_excess
labels. Keep **v5 logistic** for demos; next quality gains come from **labels + features
+ GeoAI story polish**, not another booster. See `docs/MODEL_CARD_FLOOD_EVENT.md`.

