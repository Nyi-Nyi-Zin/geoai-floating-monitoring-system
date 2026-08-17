# Maubin Local River-Stage and Tide Evidence Audit

**Audit date:** 17 August 2026 UTC  
**System posture:** **Monitoring only**; no stage threshold, flood probability, forecast, alert, or life-safety decision is enabled.

## Decision

The audit found one **published historical river-stage context source** in nearby Nyaungdon Township, Maubin District, but no verified Maubin-equivalent live river-stage feed. It also confirmed the existence of an official Haing Gyi Kyun coastal tide station, yet its public IOC tabular endpoint returned **NO DATA** and its official station list reported the station as down with a 1,933-day delay at the audit time. Neither source is authorized as a live monitoring feature or model input.

> The resulting dashboard disclosure is provenance context, not a water-level warning product. The nationwide and Maubin candidate gates remain closed.

## Source findings

| Evidence family | Verified finding | Coverage or condition | Authorization decision |
| --- | --- | --- | --- |
| Historical river stage | The open PLOS supporting workbook contains annual highest Panhlaing River water level and published danger-level entries for Nyaungdon station. | 32 dated records from 1985-08-09 through 2016-08-16; 17 entries are at or above the workbook’s published danger stage. | **Historical context only**. Nyaungdon is nearby Maubin-District evidence, not a Maubin Township gauge equivalent. |
| Live river stage | Myanmar DMH documents 22 hydrological stations and water-level observation three times per day. | No verified public Maubin/Nyaungdon download endpoint, live telemetry, common datum, or issue-time lineage was found in this audit. | **Not authorized** for ingestion or model use. |
| Tide and coastal water | Haing Gyi Kyun is an official Myanmar sea-level station in Ayeyarwady Region. IOC metadata identifies a radar sensor and one-minute sampling declaration. | The public tabular endpoint returned `NO DATA`; the station was listed down with a 1,933-day delay on 17 August 2026 UTC. The IOC service explicitly says it does not provide vertical-datum information. | **Not authorized** for live tide/coastal-water context, thresholds, or model use. |

## Published Nyaungdon historical context

Khaing et al. publish observed streamflow, Nyaungdon river stage, and rainfall in the openly available supporting workbook for their Nyaungdon flood-hazard study.[1] The audited table labels the records `Panhling_River`, `Highest Wl (ft)`, and `Danger level`. Its exact workbook SHA-256 is retained as `ce1c7875ae66b52e5461a26436528fccd794d5037e4b808192862122376a7dc6`, and the bounded extracted context is stored outside the web project as `nyaungdon_panhlaing_historical_stage_context.json`.

This source is useful for confirming that a documented, historical Maubin-District river-stage record exists. It does **not** prove continuous telemetry, spatial interchangeability with Maubin Township, a common datum with DeltaWatch terrain, a current danger-level regime, or future-time availability. It is therefore not fitted into the v7 model and is not shown as a current water level.

## Official network and tide evidence

DMH describes a hydrological network with 22 hydrological stations and three water-level observations per day, which establishes that water-level observation is an official activity in Myanmar.[2] However, this documentation does not supply a public Maubin/Nyaungdon API or downloadable current series with station metadata and datum controls.

Myanmar’s GLOSS national report identifies Hainggyigyun as one of three national tide-gauge sites and notes its 2014 installation.[3] The current IOC station page confirms the Haing Gyi Kyun station coordinates, radar sensor, and one-minute sampling metadata. The same official service reported the station down, its tabular view returned `NO DATA`, and its FAQ states that the service has relative data rather than absolute vertical-datum information.[4] Those conditions prevent any safe conversion to a Maubin water-level threshold or tide model feature.

## Implementation and safety controls

The project now retains a compact managed readiness seed and a public spatial endpoint at `/api/spatial/maubin/local-water-evidence-readiness`. The dashboard presents the historical Nyaungdon record count and coverage, then explicitly says it is **not a Maubin live gauge**. It separately displays that the coastal station is down and public data were unavailable at audit time. The endpoint returns readiness information only and omits score, probability, prediction, forecast, and alert fields.

The following gates remain mandatory before local-water evidence can influence a future candidate experiment:

| Required gate | Current state | Consequence |
| --- | --- | --- |
| Live Maubin-equivalent stage feed | Missing | No live river-stage feature. |
| Station datum, location, and QC metadata | Missing | No stage threshold or terrain comparison. |
| Maubin-calibrated tide/coastal record | Missing | No coastal influence feature. |
| Archived issue-time lineage | Missing | No prospective feature authorization. |
| Verified field/gauge outcomes across events | Missing | No prospective accuracy or alert claim. |

## References

[1] [Khaing et al. (2019), *Flood hazard mapping and assessment in data-scarce Nyaungdon area, Myanmar*, PLOS ONE](https://doi.org/10.1371/journal.pone.0224558)  
[2] [Myanmar Department of Meteorology and Hydrology — Hydrological Division](https://www.moezala.gov.mm/en/bay-bulletin/96)  
[3] [Myanmar National Report to GLOSS (2015)](https://gloss-sealevel.org/sites/gloss/files/publications/documents/national-report-myanmar-2015.pdf)  
[4] [IOC Sea Level Station Monitoring Facility — Haing Gyi Kyun station](https://www.ioc-sealevelmonitoring.org/station.php?code=hain) and [service documentation](https://www.ioc-sealevelmonitoring.org/service.php)
