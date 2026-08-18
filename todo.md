# Project TODO

- [x] Document the permanent hosting architecture, including the Node server, colocated FastAPI spatial API, persistent data model, and autoscale constraints.
- [x] Build a polished full-screen Maubin Leaflet map with satellite and terrain basemaps.
- [x] Add township-boundary, river, canal, terrain-risk, historical-flood, grid-cell, and label layer controls.
- [x] Persist and serve the 5,549 terrain-screening cells with LOWER, MODERATE, HIGH, and VERY_HIGH bands.
- [x] Add live seven-day Open-Meteo rainfall bars and a thirty-day rainfall-history sparkline.
- [x] Persist pixel-level GFD v3 event polygons for the 17 historical events and expose a historical-flood layer.
- [x] Add a v6 experimental event-hindcast panel with per-cell probabilities and an always-visible precision/recall disclaimer.
- [x] Add a system status bar with exact terrain_screening risk-basis label, spatial database status, and open-alert count.
- [x] Create an accessible About and methodology modal naming Copernicus DEM, ESA WorldCover, GFD v3, and ERA5 with model limitations.
- [x] Create deploy-compatible Python/FastAPI spatial-service integration and a custom Dockerfile with required client libraries.
- [x] Add an idempotent nightly /api/scheduled rainfall handler that upserts current-month Open-Meteo data into rainfall_history.
- [x] Add schema migrations, seed data, service tests, API tests, and UI tests for core monitoring flows.
- [x] Verify responsive visual rendering, create a final checkpoint, and prepare the site for user-initiated publishing.
- [x] After publication, create and verify the project-level nightly Heartbeat job.
- [x] Push the latest verified DeltaWatch project state to the configured GitHub repository.
- [x] Inspect and report current deployment, database, spatial-service, and nightly-refresh job status.
- [x] Verify and report the v6 flood-hindcast model’s current performance, proper use, and limitations.
- [x] Assess authoritative Maubin-relevant sources for river levels, tidal conditions, upstream inflow proxies, rainfall lags, drainage and levee features, and additional validated flood events.
- [x] Acquire and spatially-temporally align eligible new predictors with the historical flood-event labels.
- [x] Retrain candidate flood models with leakage-safe chronological validation and compare calibration, precision, recall, F1, PR-AUC, and ROC-AUC.
- [x] Update durable model seeds, metadata, methodology, dashboard metrics, tests, and source documentation for the selected candidate.
- [x] Verify the updated production dashboard, publish the model upgrade, synchronize GitHub, and report the final comparison.
- [x] Deliver the final v6-versus-v7 comparison, production URL, GitHub synchronization reference, and remaining tide-data limitation to the user.
- [x] Assess Maubin-local and regional river-stage, tide/surge, upstream-flow, and independently validated flood-label data coverage, access terms, and temporal completeness.
- [x] Acquire and quality-control only eligible river, tide/surge, and additional flood-validation data; preserve documented gaps rather than synthesizing values.
- [x] Integrate accepted new predictors into a leakage-safe chronological model experiment and compare candidates against v7 on a common holdout.
- [x] Define and implement a clearly labelled non-life-safety monitoring-alert workflow only if its input evidence and evaluation support it; the coastal proxy is currently unsupported, so the implemented workflow remains explicitly disabled and dashboard-only.
- [x] Verify, publish, synchronize GitHub, and report any validated next-stage model or monitoring improvements.
- [x] Obtain a user-authorized C3S API credential or Maubin/Nyaungdon local-gauge file that covers the 2002–2018 model event period before adding a tide/surge or local-stage predictor.
- [x] Document a concrete disabled non-life-safety alert workflow proposal, including activation gates, labels, thresholds, delivery channel, and verification requirements.
- [x] Audit the v7 training pipeline, event-split performance, feature coverage, calibration, and documented data gaps before selecting new model-improvement work.
- [x] Research and acquire only eligible Maubin-relevant river-stage, tide/surge, upstream-flow, rainfall, exposure, or validated flood-label evidence with clear provenance and temporal coverage; the CEMS GloFAS wetness candidate is documented but deferred pending separate EWDS licence authorization.
- [x] Engineer leakage-safe candidate features and retrain comparative models against the v7 baseline on a common chronological evaluation.
- [x] Promote only a demonstrably improved candidate; otherwise retain v7 and document the negative experiment evidence and remaining blockers.
- [x] Verify any qualified release, synchronize GitHub, and report the model-improvement findings and operational limitations.
- [x] Audit the DeltaWatch phone layout for map visibility, panel overflow, touch targets, and status readability at common mobile widths.
- [x] Implement responsive mobile layout rules for the map controls, rainfall and hindcast information panels, and status bar without weakening safety disclosures.
- [x] Verify mobile and desktop rendering, publish the responsive release, synchronize GitHub, and report the result.
- [x] Audit eligible current and forecast rainfall, upstream-flow, river-stage, and tide/surge data for a prospective Maubin prediction pipeline, including latency and provenance.
- [x] Compare safe automated prediction operating modes and establish monitoring-only activation gates, prospective validation requirements, and data-quality controls.
- [x] Build only the eligible monitoring-only ingestion and future-time prediction components; retain v7 historical hindcast when inputs or validation are insufficient.
- [x] Initialize timestamped prospective validation, verify technical automation behavior, publish safe monitoring-only outputs, synchronize GitHub, and report remaining outcome-data readiness limits.
- [x] Create a six-hour forecast snapshot store with immutable issue timestamps, source coverage, quality flags, and monitoring-only output metadata.
- [x] Implement idempotent forecast rainfall, soil-moisture, and GloFAS-discharge ingestion that does not emit alerts.
- [x] Implement and durably retain per-cell future-time v7 feature projections by combining forecast inputs with the existing static terrain, land-cover, drainage, and levee context for each target date.
- [x] Add end-to-end regression coverage that verifies durable per-cell prospective features are retrievable for a target date while probability, alert, and predicted-label fields remain absent.
- [x] Create and verify the project-level six-hour refresh schedule, expose a clearly labelled prospective monitoring status, and preserve audit-ready validation records.
- [x] Add an integration regression test that exercises stored-snapshot prospective feature retrieval and confirms all per-cell features are retrievable without probability, predicted-label, or alert fields.
- [x] Push the latest prospective-monitoring release to GitHub and verify the public production dashboard exposes its monitoring-only prospective status.
- [x] Define field-observation evidence standards, required provenance fields, permitted review states, and protected access controls for prospective validation.
- [x] Create durable observation and photo-reference storage with authenticated submission and secure server-side uploads.
- [x] Add mobile-friendly field-observation capture and analyst review views that remain clearly separate from public flood alerts.
- [x] Test the evidence workflow, publish the monitoring-only release, synchronize GitHub, and report validation-readiness limitations.
- [x] Add automated success-path coverage for protected observation persistence, managed photo-reference upload, and administrator review updates without fabricating field evidence in production.
- [x] Add a higher-level protected-API regression that verifies successful submission and administrator review through the router while mocked persistence prevents fabricated production evidence.
- [x] Push the final field-evidence release, tests, and tracker state to the DeltaWatch GitHub branch.
- [x] Audit verified field observations and timestamped prospective snapshot coverage without creating synthetic evidence.
- [x] Define and document field-to-grid matching, lead-time windows, exclusions, calibration metrics, and non-promotion thresholds.
- [x] Generate an evidence-backed prospective calibration report or a zero-evidence baseline that explicitly withholds unsupported accuracy metrics.
- [x] Validate, publish, synchronize GitHub, and report prospective-calibration readiness limitations.
- [x] Audit production readiness across data freshness, schedule health, API resilience, evidence governance, security controls, and user-facing operational disclosures.
- [x] Implement prioritized data-quality and operational-observability improvements that are safe in autoscale hosting and retain monitoring-only safeguards.
- [x] Strengthen validation auditability and analyst workflow controls without fabricating evidence or enabling unsupported public alerts.
- [x] Verify, publish, synchronize GitHub, and report material production-readiness improvements and remaining safety limits.
- [x] Prevent field-photo object-key collisions and strengthen photo-upload integrity checks without storing image bytes in the database.
- [x] Add prospective-refresh freshness and schedule-health status fields so stale or failed monitoring inputs are visible to users and analysts.
- [x] Add regression coverage for storage-key uniqueness, freshness-state classification, and schedule-health disclosure.
- [x] Record sanitized scheduled-refresh failures in persistent job state and present source freshness plus job health in the public dashboard without exposing scheduler credentials.
- [x] Backfill completed current-month ERA5 rainfall through the existing idempotent service so the historical-rainfall panel is populated before the first scheduled run.
- [x] Correct operational rainfall freshness to report the latest observed ERA5 date when a batch shares write timestamps.
- [x] Add database-backed submission throttling for protected field observations to reduce spam and duplicate evidence without suppressing legitimate reporters.
- [x] Enforce one-time analyst disposition: only a submitted observation may be verified or rejected, and missing observations must return a controlled error.
- [x] Add service and protected-router regression coverage for observation throttling and immutable review-state transitions.
- [x] Publish an in-repository operator runbook covering data freshness states, safe rainfall backfill, schedule-failure response, field-evidence governance, and the non-alert policy.
- [x] Publish a complete production-readiness audit that records scope, evidence, residual risks, and mitigations across data freshness, scheduler health, API resilience, evidence governance, security, and user disclosures.
- [x] Surface explicit prospective-input freshness and six-hour job health in the dashboard, including a clear failed-refresh state that remains separate from alerts.
- [x] Add regression coverage that verifies sanitized failed prospective-refresh state is disclosed through the public operational-health contract.
- [x] Add an endpoint-level regression that supplies a failed prospective schedule record and verifies public operational status exposes only sanitized failed state and no scheduler or raw-error details.
- [x] Save the verified production-readiness checkpoint and publish the updated monitoring-only site.
- [x] Commit and synchronize the production-readiness release to the configured GitHub branch, then verify remote alignment.
- [x] Deliver the released production-readiness summary and unresolved monitoring-only safety limits.
- [x] Deliver a user-facing production-readiness release summary covering the deployed URL, checkpoint version, GitHub branch commit, key improvements, validation results, and remaining monitoring-only limits.

## Maubin Login-Free Public Evidence Access

- [x] Audit Maubin’s current authentication-gated evidence procedures, client redirects, and persistence boundary.
- [x] Replace public evidence sign-in with a privacy-preserving browser-scoped contributor identity while retaining throttling and immutable protected review.
- [x] Add regression coverage and visual verification for anonymous evidence submission, no public review decision, and monitoring-only disclosures.
- [x] Publish, synchronize GitHub, and report the verified login-free Maubin release.

## Maubin Flood Risk Visualization

- [x] Audit the active Maubin terrain-screening data, polygon styling, legend, and historical map presentation to explain the current red-and-blue display.
- [x] Restore a readable multi-band terrain-screening palette and legend without presenting it as real-time flood probability, gauge status, or an alert.
- [x] Add regression coverage and visually verify the corrected map layer and monitoring-only disclosures.
- [x] Explicitly verify in the browser that all four terrain-screening colors, the static legend, and no-warning disclosure render together in the Maubin Flood Risk layer.
- [x] Strengthen the terrain-screening regression guard against reintroducing historical-hindcast binary red/blue styling.
- [x] Record an explicit rendered-map confirmation that blue, yellow, orange, and red terrain-screening cells are all visibly present with the static legend and no-warning disclosure in `docs/maubin_terrain_screening_visual_verification_2026-08-18.md`.
- [x] Publish, synchronize GitHub, and report the corrected Maubin risk-layer presentation.

## Maubin Grid-Cell Detail Interaction

- [x] Audit the active grid-cell click handler, popup/detail UI, and selected historical-hindcast data path to identify why per-cell information no longer appears.
- [x] Restore an accessible grid-cell detail panel with static terrain context and separately labelled historical-hindcast information, without public probability, forecast, or alert output.
- [x] Add regression coverage and browser verification for grid-cell detail selection, close behavior, and monitoring-only disclosure.
- [x] Add selected-event historical-hindcast cell context to the restored detail panel without exposing a public probability, forecast, or alert.
- [x] Publish, synchronize GitHub, and report the restored Maubin grid-cell detail interaction.

## Maubin Historical Model Heatmap

- [x] Audit the available historical HGB v7 per-cell outputs and define a replay-only heatmap contract that cannot be mistaken for a live forecast or warning.
- [x] Add a separate Layer Control toggle and multi-band heatmap for the selected historical event, preserving the static terrain-screening layer.
- [x] Add regression coverage and browser verification for toggle behavior, selected-event changes, experimental replay disclosure, and absence of current/future output.
- [x] Publish, synchronize GitHub, and report the safe historical model heatmap enhancement.


## Active Clarification Work

- [x] Clarify the public distinction between static Flood Risk terrain screening, historical HGB v7 replay, and prospective monitoring.
- [x] Add regression coverage for the distinction and no-current/future-probability safety language.
- [x] Verify, publish, synchronize GitHub, and report the clarified behavior.
