import fs from "node:fs/promises";
import mysql from "mysql2/promise";

const outputPath = new URL("../model_pipeline/prospective_calibration_report_baseline.md", import.meta.url);
const jsonPath = new URL("../model_pipeline/prospective_calibration_report_baseline.json", import.meta.url);
const formatInstant = value => value ? new Date(value).toISOString() : null;

if (!process.env.DATABASE_URL) throw new Error("DATABASE_URL is required to generate the prospective calibration report.");
const connection = await mysql.createConnection(process.env.DATABASE_URL);
try {
  const [observationRows] = await connection.query("SELECT review_status AS reviewStatus, COUNT(*) AS count, MIN(observed_at) AS earliestObservedAt, MAX(observed_at) AS latestObservedAt FROM field_observations GROUP BY review_status");
  const [snapshotRows] = await connection.query("SELECT COUNT(*) AS snapshotCount, COUNT(DISTINCT issue_key) AS issueCount, MIN(issue_time) AS earliestIssueTime, MAX(issue_time) AS latestIssueTime, MIN(target_date) AS earliestTargetDate, MAX(target_date) AS latestTargetDate FROM prospective_forecast_snapshots");
  const observations = Object.fromEntries(observationRows.map(row => [row.reviewStatus, { count: Number(row.count), earliestObservedAt: row.earliestObservedAt, latestObservedAt: row.latestObservedAt }]));
  const snapshot = snapshotRows[0];
  const baseline = {
    generatedAtUtc: new Date().toISOString(),
    evidence: { submitted: observations.submitted?.count ?? 0, verified: observations.verified?.count ?? 0, rejected: observations.rejected?.count ?? 0, verifiedCoverage: observations.verified ?? null },
    prospectiveSnapshots: { snapshotCount: Number(snapshot.snapshotCount), issueCount: Number(snapshot.issueCount), earliestIssueTime: formatInstant(snapshot.earliestIssueTime), latestIssueTime: formatInstant(snapshot.latestIssueTime), earliestTargetDate: snapshot.earliestTargetDate, latestTargetDate: snapshot.latestTargetDate },
    metricsStatus: "withheld_no_verified_matched_outcomes_and_no_prospective_scores",
  };
  const submitted = observations.submitted ?? {};
  const verified = observations.verified ?? {};
  const rejected = observations.rejected ?? {};
  const lines = [
    "# DeltaWatch prospective calibration baseline", "", `**Generated:** ${baseline.generatedAtUtc}  `, "**Scope:** Maubin Township; monitoring-only prospective records; no public alert decision.", "",
    "## Evidence audit", "", "| Evidence state | Count | Earliest | Latest |", "|---|---:|---|---|",
    `| Submitted field observations | ${baseline.evidence.submitted} | ${submitted.earliestObservedAt ?? "—"} | ${submitted.latestObservedAt ?? "—"} |`,
    `| Verified field observations | ${baseline.evidence.verified} | ${verified.earliestObservedAt ?? "—"} | ${verified.latestObservedAt ?? "—"} |`,
    `| Rejected field observations | ${baseline.evidence.rejected} | ${rejected.earliestObservedAt ?? "—"} | ${rejected.latestObservedAt ?? "—"} |`, "",
    "| Prospective archive item | Value |", "|---|---:|", `| Immutable target-date snapshots | ${baseline.prospectiveSnapshots.snapshotCount} |`, `| Distinct forecast issues | ${baseline.prospectiveSnapshots.issueCount} |`,
    `| Issue-time coverage | ${baseline.prospectiveSnapshots.earliestIssueTime ?? "—"} to ${baseline.prospectiveSnapshots.latestIssueTime ?? "—"} |`, `| Target-date coverage | ${baseline.prospectiveSnapshots.earliestTargetDate ?? "—"} to ${baseline.prospectiveSnapshots.latestTargetDate ?? "—"} |`, "",
    "## Current finding", "", `No prospective accuracy, precision, recall, F1, PR-AUC, ROC-AUC, Brier score, calibration slope, or threshold metric is reported. There are **${baseline.evidence.verified} verified field observations**, and the prospective archive intentionally retains model-ready per-cell features without flood probabilities or predicted labels. Producing an accuracy number would therefore be unsupported.`, "", "> This baseline is evidence-ready, not a performance claim. The historical v7 hindcast metrics must not be reused as prospective performance.", "",
    "## Pre-registered matching protocol", "", "A future evaluation record is eligible only when its observation is administrator-verified, has an observation timestamp and valid location, and is matched to a snapshot issued no later than the observation time. The primary forecast target is the same UTC target date, with lead time calculated from the stored issue time. Each location must be mapped to the applicable DeltaWatch terrain cell; records outside the mapped study extent or without auditable time/location provenance are excluded.", "",
    "| Element | Fixed rule before scoring |", "|---|---|", "| Outcome class | flooded, water_on_road, or access_disrupted is a positive impact evidence class; no_flood_observed is a negative evidence class. |", "| Reporter evidence | Only administrator-verified records are eligible. Submitted and rejected entries remain excluded. |", "| Temporal linkage | Select the most recent immutable issue time at or before observation time; preserve issue key, target date, and lead time. |", "| Spatial linkage | Link to the cell containing the verified coordinates; exclude unresolved or out-of-extent locations. |", "| Duplicate control | Keep the first verified record per contributor, cell, impact class, and target day unless a later review explicitly records a materially distinct condition. |", "| Forecast output | Do not score until a frozen analyst-only v7 probability output is archived beside the same per-cell feature vector. |", "",
    "## Metrics and release gates", "", "When the frozen prospective score exists and both evidence classes are available, report the confusion matrix, precision, recall, F1, specificity, balanced accuracy, and PR-AUC/ROC-AUC where score coverage supports them. Report Brier score, calibration intercept/slope, and reliability bins only for probabilities. Confidence intervals must be event-aware rather than treating nearby cells as independent.", "", "The first public-facing calibration summary should remain withheld until the evaluation includes at least 30 verified positive and 30 verified negative observations spanning at least three distinct rainfall or flood episodes, with no episode contributing more than half of either class. These are operational minimum gates for an exploratory summary, not a safety-alert activation rule.", "",
    "## Readiness actions", "", "1. Collect signed-in field observations with time, location, impact class, and review rationale.", "2. Verify evidence through the administrator queue; include both observed impacts and verified no-flood controls.", "3. Archive an analyst-only, frozen prospective v7 score after the model-governance decision permits scoring.", "4. Re-run this generator and compute metrics only for the pre-registered matched cohort.", "",
    "## Provenance", "", "This report is generated directly from the managed field_observations and prospective_forecast_snapshots tables. Evidence governance is defined in [field_observation_protocol.md](./field_observation_protocol.md); prospective-input retention is defined in [prospective_validation_protocol.md](./prospective_validation_protocol.md).",
  ];
  await fs.writeFile(outputPath, `${lines.join("\n")}\n`, "utf8");
  await fs.writeFile(jsonPath, `${JSON.stringify(baseline, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(baseline));
} finally {
  await connection.end();
}
process.exit(0);
