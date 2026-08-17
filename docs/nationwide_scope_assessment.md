# Myanmar Nationwide DeltaWatch Scope Assessment

**Branch:** `feat/myanmar`  
**Status:** Architecture and evidence assessment only; no nationwide flood probability, predicted label, public alert, or life-safety decision is enabled.

## Decision boundary

Myanmar has seven States, seven Regions, and one Union Territory, making the Admin 1 level a practical first regional partition for a country-scale dashboard.[1] A verified current boundary package is still required before any production grid is generated; the MIMU GeoNode endpoint was access-blocked during assessment, so its search listing is not treated as a downloadable source of record.

> **Decision:** Reuse the Maubin feature logic as an experimental monitoring framework, but do **not** reuse its single-area seed, metrics, or thresholds as a nationwide prediction model. Country-scale processing must be regional, tiled, and evaluated separately by geography and time.

## Workload comparison

UNdata lists Myanmar’s surface area as 676,577 km².[2] The following figures are transparent upper-bound sizing calculations only. A real build must use an authoritative boundary, land/water mask, and eligible terrain mask instead of generating cells over the entire surface area.

| Measure | Maubin baseline | Myanmar theoretical upper bound | Implication |
|---|---:|---:|---|
| Terrain-screening cells | 5,549 | 676,577 at a 1 km² equivalent | About **121.92×** the Maubin cell count before masks. |
| Coarse 5 km²-equivalent cells | N/A | 27,063 | A reasonable first index scale for regional coverage discovery, not a prediction resolution. |
| Static v7-feature seed | 1.32 MiB | ~161.14 MiB if linearly scaled | Suitable only as chunked regional data, not a single browser payload. |
| Spatial GeoJSON seed | 7.07 MiB | ~862.12 MiB if linearly scaled | Must be vector-tiled or simplified; a monolithic endpoint is unsafe. |
| V7 hindcast seed | 13.45 MiB | ~1.60 GiB if linearly scaled | Historical event predictions must be stored and retrieved by event, region, and zoom. |
| Eight future target-date feature vectors | 44,392 cells | ~5.41 million cell vectors | Six-hour work must be partitioned, idempotent, and retention-controlled. |

The storage estimates use actual Maubin managed-seed sizes and the 5,549-cell baseline. They intentionally do not claim actual nationwide storage because imagery masks, geometry complexity, event coverage, and region-specific feature availability will change the final size.

## Eligible data sources and limits

| Data category | Potential nationwide source | What it supports | Critical constraint |
|---|---|---|---|
| Administrative partition | MIMU administrative layers, pending direct access and provenance verification | Regional/township filters and per-region batch partitioning | The endpoint was access-blocked; a vetted current export is required. |
| Elevation and terrain context | Copernicus DEM GLO-30 | Nationwide terrain-derived screening features; GLO-30 provides worldwide 30 m coverage.[3] | It is a **Digital Surface Model**, not a bare-earth local flood-survey elevation model; delta/coastal vertical uncertainty requires special caution.[3] |
| Land-cover context | ESA WorldCover 2020/2021 | Global 10 m Sentinel-1/Sentinel-2 land-cover baseline, accessible as Cloud-Optimized GeoTIFF tiles or through supported services.[4] | The 2020 and 2021 maps use different algorithm versions, so map-to-map changes cannot be interpreted solely as land-cover change. It is a historical baseline, not a current land-use or flood observation.[4] |
| River-network features | HydroRIVERS v1 | Consistent global river reach network with stream order, length, upstream/outlet distance, estimated long-term discharge, and HydroBASINS linkage.[5] | It includes reaches meeting stated catchment/flow thresholds, so smaller canals and local drains are incomplete; it is not a real-time hydrometric feed.[5] |
| Local waterways context | HOT OpenStreetMap Waterways of Myanmar | Recent map context for rivers, streams, canals, lakes, and other water features, sourced from OpenStreetMap contributors.[6] | Feature completeness and attributes vary by area; it must not be treated as calibrated discharge, channel capacity, or flood-outcome evidence.[6] |
| Historical flood labels | Global Flood Database v1 | Country-filterable historical flood-event maps, permanent-water masking, and event-level temporal records.[7] | Coverage is 2000–2018, event selection is not a complete census of every flood, and its licence is CC BY-NC 4.0.[7] |
| Rainfall antecedents | ERA5 / ERA5T | Nationwide precipitation-lag and wetness features using a consistent meteorological source | Reanalysis is not a local gauge; ingest must be tiled and source latency recorded. |
| River and wetness proxy | GloFAS historical / forecast products | Global daily river discharge, soil-wetness index, runoff, upstream area, and elevation proxies.[8] | GloFAS forecasts focus on rivers and do not provide real-time flash-flood, coastal-flood, or inundation-area forecasts.[9] |

### Historical-label sizing and bounded batch topology

The public GFD quality-control catalog yielded **12 Myanmar/Burma-tagged historical records** under the documented source-metadata selection rule. Their matching `gfd_v1_4` archive metadata totals **175.70 MB** across 12 ZIP archives; the largest single archive is **25.19 MB**. No archive bytes or labels were downloaded in this sizing step. This volume is practical for an offline, resumable data-preparation run but does **not** make a country-wide 500 m all-cell event table practical inside a single autoscale request.

To keep future processing bounded, the vetted OCHA/MIMU Admin 1 source geometry was reduced to a compact **18-partition** manifest. Each partition retains the original Admin 1 P-code, English and Myanmar name, source center, geographic bounding box, reported source area, and source validity date. The public endpoint exposes the manifest only; it contains no features, labels, scores, probabilities, or predictions. Any later archive extraction must apply event geometry and feature construction inside these Admin 1 partitions with explicit temporal holdouts.
| Local outcome evidence | Field observations and local gauges | Future regional calibration and local reliability checks | Present verified nationwide coverage is absent; no accuracy claim may be generalized without it. |

## Recommended architecture

The first nationwide release should be a **coverage and monitoring index**, not a nationwide reproduction of the Maubin 1 km cell map. It should expose Admin 1 selection, source freshness, regional data-coverage state, and monitoring-only limitations. The map must request simplified boundaries or vector tiles at country view; detailed terrain cells should load only after the user chooses an eligible region and suitable zoom.

The ingestion design should process one administrative region or fixed spatial tile at a time, use a durable input/version key, retry only transient source failures, and write region-scoped outputs idempotently. Six-hour prospective inputs should retain a small, documented number of target dates and use lifecycle rules so a single refresh cannot create an uncontrolled multi-million-row payload. The database should store metadata and aggregates separately from per-cell geometry and feature blobs.

Before displaying any nationwide risk score, the project must construct a leakage-safe regional and chronological evaluation. A model that performs in Maubin may not transfer to upland, riverine, coastal, urban, or flash-flood conditions. Every output must therefore carry a region coverage state such as `not_assessed`, `data_incomplete`, `historical_screening_only`, or `prospective_validation_pending`.

## Readiness conclusion

Nationwide expansion is technically feasible as a phased monitoring project, but it is materially larger than Maubin. A direct clone would create an estimated 0.8+ GiB spatial payload and millions of prospective feature vectors, which exceeds the intended design envelope of the current autoscaled map experience. The next safe implementation step is to obtain a vetted national boundary, create a lightweight Admin 1 coverage index, and build a tile-partitioned processing contract before training or showing nationwide prediction outputs.

## References

[1] [Northwestern Pritzker Legal Research Center, *Administrative Structure & Maps — Myanmar*](https://library.law.northwestern.edu/myanmar/maps)  
[2] [UNdata, *Myanmar country profile*](https://data.un.org/en/iso/mm.html)  
[3] [Copernicus Data Space Ecosystem, *Copernicus DEM — Global and European Digital Elevation Model*](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM)  
[4] [ESA WorldCover, *Data Access*](https://esa-worldcover.org/en/data-access)  
[5] [HydroSHEDS, *HydroRIVERS v1*](https://www.hydrosheds.org/products/hydrorivers)  
[6] [HDX, *Waterways of Myanmar*](https://data.humdata.org/dataset/hotosm_mmr_waterways)  
[7] [Google Earth Engine Data Catalog, *Global Flood Database v1 (2000–2018)*](https://developers.google.com/earth-engine/datasets/catalog/GLOBAL_FLOOD_DB_MODIS_EVENTS_V1)  
[8] [CEMS Early Warning Data Store, *GloFAS historical river discharge and related data*](https://ewds.climate.copernicus.eu/datasets/cems-glofas-historical)  
[9] [Copernicus Emergency Management Service, *About GloFAS*](https://global-flood.emergency.copernicus.eu/general-information/about-glofas/)
