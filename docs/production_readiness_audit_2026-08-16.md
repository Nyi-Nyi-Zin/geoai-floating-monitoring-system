# DeltaWatch Production-Readiness Audit

**Assessment date:** 2026-08-16  
**System posture:** **Monitoring only**; no public flood alert, probability, or life-safety decision feature is enabled.

## Scope and method

This audit reviews the deployed DeltaWatch codebase, current database state, dashboard rendering, regression results, and operational documentation. It is an engineering readiness review rather than an independent penetration test, an external security certification, a load test, or a validation of hydrologic accuracy. Claims below distinguish verified implementation evidence from outstanding risk.

| Review area | Verified evidence | Current assessment |
|---|---|---|
| Data freshness | The dashboard now exposes ERA5 history freshness, latest completed observation date, prospective-input freshness, and sanitized job status. | **Implemented**. Stale and unavailable states are visible rather than silently treated as current. |
| Rainfall history | The controlled, idempotent backfill inserted 15 real ERA5 records for 2026-08-01 through 2026-08-15. | **Initialized**. The nightly scheduled run remains necessary for continued coverage. |
| Scheduler resilience | Source retrieval uses bounded retry and a 20-second request timeout. Scheduled handlers persist sanitized `success` or `failed` outcomes. | **Implemented with limits**. The system has no separate pager or external incident-notification path. |
| Public safety posture | Alert readiness remains disabled; prospective records contain feature context only, without probability, predicted label, or alert output. | **Implemented**. This must not change without the documented evidence and validation gates. |
| Evidence integrity | Reports require authentication; uploads use unique object keys, accepted bytes are checked against image signatures, and submission rate is limited to three per rolling hour. | **Implemented**. The control reduces ordinary duplication and spam; it is not a substitute for analyst review. |
| Analyst governance | A report may be reviewed only once from `submitted` to `verified` or `rejected`; a review rationale is required at the protected interface. | **Implemented**. Verified evidence count remains zero, so prospective performance metrics remain withheld. |
| Dashboard usability | Desktop and 375 × 812 phone layouts were visually checked after adding health cards and a five-item status grid. | **Verified visually**. The mobile layout prioritizes the freshness card and retains the monitoring-only label. |
| Regression and build | The latest local validation completed **28 passing tests across 14 files**, followed by a successful production build. | **Verified locally**. This is not a substitute for external traffic or incident simulation. |

## Data and operational controls

The operational-health endpoint publishes only source freshness, label, expected interval, sanitized status, and timestamps. It does **not** expose scheduler task identifiers, source credentials, or raw exception details. A persisted failure is classified as `failed`, allowing the public dashboard to display a failed prospective refresh while keeping it separate from the alert workflow.

The current ERA5 historical history is an authorized real-source backfill, not a synthetic seed. The source-date query orders by observation date, which avoids displaying the earliest value when a batch shares write timestamps. The backfill is documented in the operator runbook and reuses the nightly job’s idempotent upsert service.

## Security and evidence-governance controls

| Control | Implementation | Residual risk |
|---|---|---|
| Authentication and authorization | Submission is protected; review queue and review mutation are administrator-only. | Role assignment remains an operational administrative responsibility. |
| Input bounds | Router validation constrains evidence coordinates, timestamps, enumerated impact class, text length, image MIME type, and numeric ranges. | Geographic bounds are broad enough for field operations and are not a substitute for a township-boundary containment check. |
| Photo integrity | Managed-storage references are unique per submission; JPEG, PNG, and WebP signatures are checked before upload. | The application verifies a file signature, not the truth, source, or semantic relevance of a photograph. |
| Submission abuse control | Three protected submissions per reporter in a rolling hour are allowed. | Rate limits do not stop coordinated multi-account abuse; authentication and analyst review remain necessary. |
| Review immutability | Only an unreviewed record may receive a disposition, and missing/reviewed records return controlled errors. | The current workflow does not provide a separate correction or appeal ledger; add one before changing review policy. |

## Remaining readiness limits

The system is more operationally observable and evidence-safe, but it is **not** ready for public flood-warning use. The model remains an experimental historical hindcast. No local river-stage series, calibrated coastal-water or tide/surge record, complete drainage-capacity/levee-condition series, or verified prospective outcome set is available for promotion.

The operator runbook explains recovery steps for scheduled failures, but there is no external paging integration. The first scheduled nightly ERA5 job has not yet demonstrated a live successful post-backfill run. The frontend build also retains a large JavaScript bundle warning, and map rendering performance should be profiled on representative low-end phones before any higher-traffic rollout.

| Priority | Required next step | Promotion or safety effect |
|---|---|---|
| P0 | Collect timestamped local stage/tide evidence and verified positive/negative field observations under the existing protocol. | Required before prospective accuracy metrics or model-promotion claims. |
| P0 | Observe at least one successful normal nightly ERA5 execution and continued six-hour prospective runs after this release. | Confirms scheduling behavior beyond controlled initialization. |
| P1 | Add operator-facing notification or external incident routing for repeated job failures if an accountable operations team is available. | Improves response time; it does not authorize alerts. |
| P1 | Profile initial map and JavaScript load on low-end phones, then lazy-load nonessential historical assets if warranted. | Improves usability and reliability under constrained connections. |
| P2 | Design an auditable evidence-correction/appeal ledger before allowing any review changes. | Preserves governance if the analyst process expands. |

> **Release conclusion:** DeltaWatch can be used as a monitored, evidence-collection and historical-analysis dashboard with explicit freshness and safety disclosures. It must continue to be described as **Monitoring only**. The documented residual risks prohibit presenting it as a validated real-time flood-prediction or public-warning system.
