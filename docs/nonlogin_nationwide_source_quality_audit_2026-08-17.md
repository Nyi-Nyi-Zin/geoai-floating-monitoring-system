# Nationwide Non-Login Source-Quality Audit

**Audit date:** 17 August 2026 UTC  
**Scope:** Existing real nationwide inputs only. EWDS login and CEMS-FLOODS licence acceptance are explicitly excluded from this workstream.  
**Decision:** **No nationwide candidate is fitted, promoted, or displayed.**

## Findings

The reproducible manifest `myanmar_nonlogin_source_quality_manifest.json` confirms complete 18-Admin-1 coverage for the existing leakage-safe rainfall-lag table and the three bounded static-context artefacts: Copernicus DEM, ESA WorldCover, and HydroRIVERS. Their coverage does not authorize a predictive feature set because the source contract still lacks verified prospective outcomes and official issue-time upstream-flow lineage.

| Source family | Coverage finding | Feature authorization | Limitation |
| --- | --- | --- | --- |
| Event rainfall lags | 216 event-region rows across all 18 Admin 1 regions | Preparation only | The table is leakage-safe but not a fitted nationwide model. |
| Copernicus DEM GLO-30 | 18 regions | Static context only | Coarse static surface context; no current water condition. |
| ESA WorldCover 2021 v200 | 18 regions | Static context only | Historical land-cover context; not dynamic land use or flood label. |
| HydroRIVERS Asia v1 | 18 regions | Static context only | River-network geometry; no observed stage or discharge telemetry. |
| Open-Meteo/GloFAS bounded snapshot | Representative-point source availability recorded | Not authorized | It does not retain an official forecast issue timestamp or forecast-run identifier. |

## EWDS issue-time access result

The smallest documented authenticated EWDS GloFAS forecast request was executed for one Myanmar representative-area query and one 24-hour control-forecast lead time. The sanitized audit recorded `access_blocked` with the blocker `dataset_terms_not_accepted`. No credential values, raw errors, or forecast files are retained in the project.

This result is an **authorization blocker**, not a claim that GloFAS is unavailable. The official EWDS workflow requires account access and manual acceptance of the CEMS-FLOODS dataset terms. Because login is outside this workstream, no bypass is attempted. The pre-existing Open-Meteo/GloFAS snapshot remains a source-availability check only; it is not an official issue-time feature.[1] [2]

## Candidate gate

> **No-fit authorization remains active.** Neither an issue-time upstream-flow feature nor verified nationwide prospective outcomes are available. Therefore, no nationwide score, probability, prediction, forecast, alert, or life-safety decision may be produced.

The next permitted work without EWDS login is prospective-evidence readiness: record the absence or presence of verified observations, preserve time/location matching eligibility, and disclose readiness states without creating labels or metrics from synthetic evidence.

## References

[1] [CEMS Early Warning Data Store — GloFAS forecast dataset](https://ewds.climate.copernicus.eu/datasets/cems-glofas-forecast)  
[2] [CEMS Early Warning Data Store — API guidance](https://ewds.climate.copernicus.eu/how-to-api)  
[3] [Open-Meteo Flood API](https://open-meteo.com/en/docs/flood-api)
