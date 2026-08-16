# Prospective prediction feasibility assessment

## Current evidence

The existing dashboard can obtain future meteorological and upstream-flow **proxies** without adding a paid external feed. A live probe for the Maubin area returned 16 days of hourly Open-Meteo precipitation and deep-soil-moisture data, plus 30 days of daily GloFAS river-discharge forecast and ensemble spread through Open-Meteo's Flood API. The public Flood API uses GloFAS and cautions that its 5 km grid may select a nearby river rather than the intended channel. [1] [2]

| Required feature family | Available prospective source | Resolution and horizon | Suitability |
|---|---|---|---|
| Rainfall | Open-Meteo weather forecast | Hourly; up to 16 days | Eligible input proxy |
| Antecedent wetness | Open-Meteo deep soil moisture | Hourly; up to 16 days | Eligible exploratory proxy |
| Upstream inflow | Open-Meteo Flood API / GloFAS | Daily; 30 days used, up to 210 available | Eligible proxy, not a local gauge |
| Local river stage | None supplied or publicly verified | — | Blocking evidence gap |
| Tide and surge | No calibrated Maubin record | — | Blocking evidence gap |
| Flood outcome labels | Historical GFD event maps only | Historical and event-level | Cannot support immediate prospective calibration |

## Safety decision

This evidence supports building a **monitoring-only prospective prototype**, not a public flood-warning system. The existing v7 model was evaluated as a historical hindcast, so it must not be presented as a live forecast until a prospective log of issued inputs and predictions has accumulated and been evaluated against independently verified outcomes. The dashboard must keep its existing `Monitoring only` label and must not introduce automatic notifications or life-safety decisions.

## Candidate operating modes

| User-facing approach | Behaviour | Trade-off | Setup and cost |
|---|---|---|---|
| Scheduled monitoring refresh | Refresh data and compute a timestamped monitoring record every 6 hours | Matches daily discharge availability while retaining multiple rainfall-forecast snapshots; not instant | Uses the existing managed site and its background schedule; low operational complexity |
| Hourly monitoring refresh | Refresh every hour and preserve each forecast issuance | More detailed rainfall forecast history, but more API calls and most discharge values change daily | Uses the existing managed site and its background schedule; higher operational activity |
| Continuous live service | Keep a process running at all times for sub-hour response | Not justified by the available daily discharge input; adds operating cost | Requires a paid always-on hosting setting; only appropriate if a reliable high-frequency gauge or webhook becomes available |

The recommended starting point is a scheduled monitoring refresh at six-hour intervals. It is sufficient for the currently available data and can be tightened after a validated local-stage feed is available. The system must store **issue time**, **source coverage**, **model/data version**, and **quality flags** for every record so later prospective evaluation is possible.

## References

[1] [Open-Meteo Weather Forecast API](https://open-meteo.com/en/docs)

[2] [Open-Meteo Global Flood API](https://open-meteo.com/en/docs/flood-api)
