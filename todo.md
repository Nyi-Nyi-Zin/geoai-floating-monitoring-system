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

- [x] Define the nationwide Myanmar monitoring boundary, spatial resolution, administrative-region hierarchy, and preserved monitoring-only safety policy.
- [x] Quantify nationwide cell count, storage, API payload, map-rendering, and six-hour compute implications relative to the 5,549-cell Maubin prototype.
- [x] Inventory available nationwide rainfall, terrain, land-cover, waterways, discharge proxies, flood labels, and local validation coverage without fabricating missing evidence.
- [x] Design a phased country-scale architecture that can reuse Maubin feature engineering while avoiding a single oversized map payload.
- [x] Evaluate region-aware model transfer and chronological validation before showing any nationwide risk output; the frozen gate audit recorded no fit because mandatory upstream-flow provenance and prospective validation are absent.
- [x] Define and freeze a leakage-safe nationwide chronological event-split protocol before constructing features or fitting any regional model candidate.
- [x] Acquire and audit real ERA5-based daily rainfall history for the 18 Admin 1 source centroids before constructing any nationwide temporal feature table.
- [x] Construct and audit a leakage-safe Admin 1 event-level rainfall-lag table that ends before each GFD event begins and remains a non-predictive preparation artifact.
- [x] Evaluate rainfall-only regional temporal baselines against the frozen protocol, retaining only documented rejection or non-promotion outcomes and producing no nationwide prediction output.
- [x] Acquire and audit nationwide static terrain, land-cover, and waterways features before attempting any region-aware predictive candidate beyond the rejected rainfall-only baseline.
- [x] Verify bounded, reproducible acquisition paths for nationwide terrain, land-cover, and river-network aggregates at the Admin 1 level before downloading high-volume static geospatial sources.
- [x] Download the documented HydroRIVERS Asia source and aggregate true-polygon river-network descriptors by Myanmar Admin 1 without generating flood-risk outputs.
- [x] Derive provenance-preserving Admin 1 terrain summaries from bounded Copernicus DEM GLO-30 remote COG overview reads without retaining full rasters or creating flood-risk outputs.
- [x] Derive provenance-preserving Admin 1 dominant land-cover context from bounded ESA WorldCover 2021 v200 remote COG overview reads without retaining full rasters or creating flood-risk outputs.
- [x] Join event issue-time rainfall lags, observed Admin 1 labels, and versioned static descriptors into an auditable regional analysis table without fitting a model or creating risk outputs.
- [x] Audit the frozen nationwide candidate-promotion gates against the joined source contract, recording an explicit no-fit outcome if any mandatory issue-time source or regional evidence prerequisite is missing.
- [x] Surface the audited nationwide static-context and no-fit candidate-gate state through the evidence-readiness endpoint and coverage panel without adding predictive output.
- [x] Build a reproducible Myanmar historical-flood event catalog from documented GFD/DFO metadata before downloading or labeling nationwide model-training events.
- [x] Audit the public archive sizes and geographic label-processing implications for the selected Myanmar GFD events before downloading any nationwide flood rasters.
- [x] Derive an Admin 1 partition manifest with real source P-codes and bounding boxes to support bounded regional label and feature-processing batches without creating predictions.
- [x] Download and checksum-verify the bounded 12-event Myanmar GFD archive set outside the deployed project for offline label-preparation assessment.
- [x] Inspect the native raster metadata and Myanmar partition overlap for the acquired historical events before constructing any regional label table.
- [x] Compute a true-Admin-1, event-level historical flood-coverage summary from the acquired GFD source rasters without producing nationwide model probabilities or alerts.
- [x] Aggregate historical Admin 1 source coverage into evidence-readiness categories without treating observed event frequency as a flood forecast.
- [x] Expose the non-predictive Admin 1 historical-source readiness summary through the nationwide coverage interface with wording that prevents interpretation as flood risk or forecast output.
- [x] Add endpoint-level regression coverage for the public nationwide evidence-readiness response, including its explicit non-predictive interpretation.
- [x] Run the complete regression suite and production build after nationwide evidence-readiness changes, then re-verify the coverage panel loads the summary through the normal spatial-service lifecycle.
- [x] Add country-scale map filters, progressive loading, and explicit regional data-coverage disclosures.
- [x] Verify, publish, synchronize GitHub, and report nationwide expansion timing, readiness, and safety limits.
- [x] Deliver a user-facing nationwide expansion report covering workload, implementation status, validation evidence, and remaining blockers.

## Nationwide Expansion Workstream

- [x] Inspect the current Maubin spatial seed dimensions and feature schema as the baseline for nationwide sizing.
- [x] Estimate nationwide processing and storage from real source-grid or administrative-boundary data rather than simulated cells.
- [x] Record a nationwide scope decision and phased rollout recommendation before implementing country-scale prediction outputs.
- [x] Preserve Monitoring only status until nationwide regional validation and local evidence support any broader operational claim.
- [x] Push the completed Maubin production-readiness commit to GitHub branch `feat/maubin` and verify the remote SHA.
- [x] Create GitHub branch `feat/myanmar` from the verified Maubin baseline, check it out locally, and verify branch isolation before nationwide edits.
- [x] Prepare a provenance-preserving Myanmar Admin 0/Admin 1 boundary seed from the vetted OCHA/MIMU package and expose it through a lightweight spatial service contract.
- [x] Add a nationwide coverage mode that loads the real Admin 1 index only on demand and labels every region as not yet assessed rather than implying a flood prediction.
- [x] Fix the nationwide coverage loader lifecycle so a successful Admin 1 response is not discarded during its own loading-state rerender.
- [x] Generate and serve a separately simplified Admin 1 display geometry so the country-scale map avoids shipping the full 4.9 MB source boundary payload on demand.
- [x] Reduce the client build’s existing >500 kB JavaScript chunk before expanding country-scale interaction beyond the lightweight Admin 1 coverage index.
- [x] Inspect and document a nationwide land-cover source and a nationwide waterways source, including provenance, coverage, access status, and operational limitations.
- [x] Update the nationwide scope assessment with explicit verified land-cover and waterways inventory rows before closing data-inventory feasibility.
- [x] Diagnose and fix the reported production blank-screen rendering failure on the deployed DeltaWatch dashboard.
- [x] Audit documented, eligible nationwide upstream-flow sources and latency constraints before ingesting any new candidate feature.
- [x] Implement only a bounded, provenance-preserving nationwide upstream-flow readiness acquisition that cannot create model scores, predictions, or alerts.
- [x] Extend nationwide evidence-readiness disclosures with upstream-flow and prospective-validation availability states while preserving the no-fit gate.
- [x] Verify, publish, synchronize GitHub, and report the resulting nationwide monitoring readiness update.
- [x] Validate official EWDS GloFAS dataset acceptance, credential compatibility, and a minimal issue-time forecast retrieval contract without creating predictive outputs; the sanitized result is a dataset-terms-not-accepted blocker.
- [x] If authenticated access succeeds, run a bounded official GloFAS forecast-run provenance and latency audit for one documented Myanmar representative point; otherwise document the access blocker and retain the no-fit gate.
- [x] Update nationwide readiness disclosures only with verified official-retrieval findings; the verified blocker is displayed without initiating a login, and the no-fit gate remains closed.

## Approved Non-Login Continuation

- [x] Document the EWDS GloFAS terms-acceptance blocker and the sanitized one-point probe result without requesting login.
- [x] Build a non-login nationwide source-quality readiness manifest covering freshness, provenance, spatial coverage, missingness, and feature authorization for existing inputs.
- [x] Add prospective field-evidence matching readiness states for unmatched, stale, insufficient, and verified evidence without fabricating observations.
- [x] Expose non-login readiness and EWDS-blocker status in the analyst-facing monitoring disclosures while preserving the public no-fit gate.
- [x] Verify, publish, synchronize GitHub, and report the approved non-login continuation update.
- [x] Correct the production managed-storage reference for the v4 nationwide evidence-readiness seed and re-verify the public contract.

The earlier EWDS items remain intentionally open until the user completes the separate account login and licence-acceptance action.

## Branch Audit

- [x] Audit protected `feat/maubin` branch state, completed features, production safeguards, and remaining work without changing its code.

## Maubin Local Water Evidence

- [x] Audit official and public Maubin/Nyaungdon river-stage and tide/coastal-water evidence sources, including access, temporal coverage, datum, and provenance constraints.
- [x] Implement bounded ingestion only for a verified accessible local-water source; otherwise persist a documented no-source readiness decision without fabricating data.
- [x] Surface Maubin river-stage and tide evidence readiness in monitoring disclosures without enabling a model score, prediction, probability, forecast, or alert.
- [x] Verify, publish, synchronize GitHub, and report the Maubin local-water evidence update.

## Public Access Without Login

- [x] Audit all authentication-gated dashboard, field-evidence, and administration paths and define a safe public-access boundary.
- [x] Remove public login requirements while retaining privacy-preserving submission identifiers, throttling, immutable reviews, and protected administrative decisions.
- [x] Add regression coverage for anonymous public access and retained evidence-governance safeguards.
- [x] Verify, publish, synchronize GitHub, and report the login-free DeltaWatch access update.

## Maubin Flow Diagram

- [x] Inspect only the protected `feat/maubin` implementation and its operational documentation to define the deployed monitoring flow.
- [x] Create and render a three-column Maubin flow diagram covering public user, core system, and operator pathways without adding unsupported alert or prediction steps.
- [x] Validate and deliver the diagram artifact without changing Maubin or Myanmar application behavior.
- [x] Redesign the Maubin flow as a reference-style infographic with numbered cards, blue/green side panels, a central system card, and clear operational arrows.
- [x] Validate and deliver the reference-style Maubin flow infographic without changing application behavior.
- [x] Redesign the infographic as a public-only DeltaWatch flow with no Admin / Operator section, no login step, and no Maubin naming.
- [x] Validate and deliver the revised public login-free infographic without changing application behavior.
