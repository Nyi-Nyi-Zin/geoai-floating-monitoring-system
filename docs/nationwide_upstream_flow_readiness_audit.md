# Nationwide Upstream-Flow Readiness Audit

**Status:** suitable for bounded, non-predictive readiness acquisition; not sufficient to authorize a nationwide predictive candidate.

## Official source assessment

The Copernicus Global Flood Awareness System (GloFAS) supplies global, gridded modelled river-discharge data. The CEMS Early Warning Data Store describes the historical GloFAS product as daily, 0.05° global hydrological data, available from 1 January 1979 to near-real time in GloFAS v5.0, with daily updates. It includes daily river discharge as well as upstream-area and elevation ancillary context.[1]

GloFAS forecast data are available through the CEMS Early Warning Data Store, operational MARS access, an on-request FTP service, and WMS-T layers.[2] The official GloFAS description says daily forecasts have been produced since 2011, are updated once per day, and concern rivers only. It explicitly does not provide flash-flood, coastal-flood, or inundation-area forecasts.[3]

| Readiness criterion | Finding | Decision |
| --- | --- | --- |
| Coverage | Global 0.05° grid includes Myanmar | Eligible for bounded Admin 1 centroid or nearest-upstream-grid context |
| Historical temporal span | 1979 to near real time, daily | Suitable for feature-provenance audit; version consistency must be pinned |
| Forecast issue-time lineage | Official forecasts are daily since 2011 | Potential future source only after an issue-time retrieval and latency audit |
| Access | EWDS registration/licence and supported API workflow required | Do not assume an automated forecast endpoint remains available without an authenticated retrieval test |
| Domain limitation | River flow only; excludes flash, coastal, and inundation forecasts | Cannot fill tide, coastal surge, drainage, levee, or local-stage gaps |
| Predictive readiness | No national prospective outcomes and no demonstrated issue-time forecast archive match | **No nationwide candidate fit or promotion authorized** |

## Bounded next action

The next permitted engineering action is a **metadata and historical-readiness acquisition** at the 18 Admin 1 representative locations only. It must retain exact dataset/version, retrieval timestamp, source grid coordinates, and the distinction between consolidated versus intermediate history. It must not calculate flood probabilities, risk scores, predicted labels, forecasts, or alerts.

An operational forecast feature is still blocked until the project demonstrates a reproducible daily issue-time request, records availability latency and source version, and accumulates timestamped prospective inputs matched to verified local outcomes. Any later model experiment must remain subject to the frozen chronological split and promotion gates.

## References

[1] [CEMS Early Warning Data Store — River discharge and related historical data from GloFAS](https://ewds.climate.copernicus.eu/datasets/cems-glofas-historical)

[2] [Copernicus EMS — GloFAS Data and Services](https://global-flood.emergency.copernicus.eu/general-information/data-and-services/)

[3] [Copernicus EMS — About GloFAS](https://global-flood.emergency.copernicus.eu/general-information/about-glofas/)
