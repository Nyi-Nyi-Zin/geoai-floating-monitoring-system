# DeltaWatch Non-Login Continuation Plan

## Goal

Continue developing the DeltaWatch Myanmar flood-risk monitoring website and nationwide evidence foundation without requiring the user to log in to the Copernicus EWDS account or accept the GloFAS dataset licence. Preserve the system as **Monitoring only**: no public nationwide flood probabilities, risk scores, predictions, alerts, or life-safety decisions may be enabled.

## Scope and assumptions

The official EWDS GloFAS issue-time retrieval is currently blocked by the dataset licence acceptance requirement. This plan therefore treats EWDS issue-time data as unavailable and does not attempt to bypass authentication or terms acceptance. Existing bounded Open-Meteo/GloFAS source-availability snapshots may remain visible only as provenance/readiness context, not as authorized model features.

The work remains isolated on `feat/myanmar`; `feat/maubin` and `main` remain untouched. Existing safety disclosures, frozen chronological splits, rejected rainfall-only baseline, no-fit candidate gate, field-evidence governance, and production monitoring controls remain binding.

## Step 1 — Preserve and document the access blocker

Retain the sanitized EWDS probe manifest containing the request date, dataset, area, endpoint, access status, and blocker classification. Update the nationwide source-provenance documentation to state that official issue-time GloFAS retrieval was not authorized because terms acceptance requires user action. Do not store credentials, raw API errors, or downloaded forecast data in the deployed project.

## Step 2 — Expand non-login nationwide data-quality readiness

Audit and test all existing non-login sources that are legally and technically accessible: ERA5 rainfall freshness, Open-Meteo rainfall, the bounded Open-Meteo/GloFAS flow snapshot, Copernicus DEM, ESA WorldCover, HydroRIVERS, GFD historical archives, Admin 1 boundaries, and prospective field-observation records. Add provenance fields for retrieval time, source version, spatial representative point, missingness, latency, and suitability status. These outputs remain audit artefacts only.

## Step 3 — Strengthen prospective validation without fabricating evidence

Implement readiness contracts and tests for matching future monitoring snapshots to verified field observations. Add explicit states for no observations, unmatched observations, insufficient lead-time coverage, stale inputs, and verified matched outcomes. Do not synthesize gauges, tides, river stages, outcomes, or labels. Keep the candidate gate closed while verified nationwide prospective outcomes are absent.

## Step 4 — Improve operator and analyst workflows

Add a protected analyst-facing readiness view or extend the existing Evidence/Methodology interface to show source freshness, upstream-flow proxy status, missing EWDS authorization, field-evidence counts, matching status, and the exact reasons a model cannot be promoted. Keep all public pages free of unsupported risk output. Add mobile-responsive, accessible status labels and sanitized failure states.

## Step 5 — Improve country-scale interaction and performance

Continue bounded Admin 1 interaction improvements that do not imply risk: region search, source-coverage filtering, static-context provenance detail, lightweight geometry loading, accessible keyboard focus, clear loading/error states, and map performance checks. Keep the country-scale view labelled as a coverage/evidence index, not a forecast or risk layer.

## Step 6 — Run safe model-preparation work only

Maintain the joined rainfall-plus-static regional table as a non-predictive preparation artefact. Add feature-contract validation, missingness reports, temporal leakage checks, and source-version consistency checks. Do not fit or export a nationwide candidate until official issue-time flow lineage or an explicitly authorized substitute, verified prospective outcomes, and the frozen promotion criteria are all satisfied.

## Step 7 — Verification and release

Run TypeScript validation, the complete regression suite, production build, endpoint-contract checks, non-predictive safety tests, and browser verification for Maubin and nationwide coverage modes. Confirm no output contains probability, score, predicted label, forecast, or alert fields in nationwide mode. Update `todo.md`, save a WebDev checkpoint, push only `feat/myanmar`, and report the deployed URL, test count, GitHub SHA, completed work, and remaining blockers.

## Promotion gates and risks

A nationwide candidate remains **not fitted and not promoted** until issue-time source lineage, full regional coverage, verified prospective matching, adequate evidence volume, and both validation and frozen holdout thresholds are met. The main open risk is the absent EWDS licence acceptance and therefore absent official issue-time forecast-run archive. A second risk is the absence of verified nationwide gauge/field outcomes. Any future public operational claim must remain disabled until those risks are resolved through documented evidence.

## Expected deliverables

The implementation phase should produce updated provenance and readiness documentation, bounded non-predictive audit manifests, source-contract and safety regressions, improved analyst/operator disclosures, a clean production build, a synchronized `feat/myanmar` commit, and a final checkpoint. No EWDS login or licence acceptance is included in the implementation scope.
