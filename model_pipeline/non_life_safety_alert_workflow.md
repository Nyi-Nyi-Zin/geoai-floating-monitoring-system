# DeltaWatch non-life-safety alert workflow proposal

## Current state

DeltaWatch does **not** issue alerts at present. The production v7 model is an experimental historical-hindcast and terrain-screening tool. The authorised GTSM coastal proxy experiment did not satisfy the promotion criteria, and its nearest modelled coastal node is not a Maubin local gauge. No email, SMS, push notification, automated alert, evacuation instruction, or danger-level label is enabled.

> **Safety boundary:** any future workflow may indicate that analysts should review elevated evidence. It must never be described as a flood warning, an evacuation trigger, or a life-safety decision system.

## Proposed gated workflow

| Stage | Candidate dashboard label | Meaning | Delivery path | Current status |
|---|---|---|---|---|
| 0 | `Monitoring only` | Normal operating mode; no validated event-level signal. | Dashboard status bar only. | Active. |
| 1 | `Review rainfall and flow` | A reproducible, data-complete rule identifies elevated antecedent rainfall and upstream-flow conditions. | Dashboard evidence card; no outbound notification. | Disabled pending validation. |
| 2 | `Analyst review recommended` | Stage-1 rule plus an independently validated local river-stage or calibrated coastal-forcing source. | Dashboard evidence card with source timestamps and a manual-review checklist. | Disabled pending local evidence. |

## Required activation gates

The workflow may be implemented only after every gate below is documented and passed on a truly held-out chronological test.

| Gate | Minimum requirement |
|---|---|
| Locality | A Maubin- or Nyaungdon-near stage record, or a documented calibrated transformation from a hydrodynamic node to a local reference. |
| Completeness | All feature inputs have timestamp coverage and latency checks for at least 95% of the evaluated event period. |
| Predictive value | The candidate must improve both validation and common 2018 held-out PR-AUC or F1 versus v7 without a material calibration regression. |
| Stability | Threshold and performance must be reported by chronological fold, not only as a pooled result. |
| Governance | Each message must show source age, model version, experimental status, a non-life-safety disclaimer, and an analyst-review action. |
| Failure handling | Missing, stale, or conflicting inputs must return `Data incomplete — no signal`, never an optimistic risk result. |

## Implementation and verification plan

When these gates are met, the first release should be dashboard-only and should use a server-side evidence record with immutable timestamps, source identifiers, model version, rule outcome, and reason codes. Unit tests must cover stale-input, missing-input, below-threshold, review-stage, and error states. A manual visual test must confirm that the non-life-safety wording remains visible on desktop and mobile. Outbound channels may be considered only after a separate governance review and must preserve the same safeguards.
