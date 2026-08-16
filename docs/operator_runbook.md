# DeltaWatch Operator Runbook

## Purpose and safety boundary

DeltaWatch is a **monitoring and analytical context system**, not a public warning service. The dashboard must remain in **Monitoring only** mode until local water-level or coastal-water evidence, prospective outcomes, and a new validated evaluation satisfy the published activation gates. No dashboard status, model feature, field report, or scheduler event is sufficient on its own to issue a life-safety message.

## Routine checks

An operator should review the dashboard at least once on working days and after a meaningful local rainfall event. The rainfall card, prospective-input status, and status bar expose the operational conditions that can be checked without revealing scheduler identifiers or internal credentials.

| Indicator | Meaning | Operator response |
|---|---|---|
| **ERA5 archive refresh: Current** | Historical daily rainfall is present and was refreshed within the expected operational window. | No action is required beyond normal review. |
| **ERA5 archive refresh: Awaiting first refresh** | No scheduled archive run has completed yet. | Confirm the nightly job is configured. If this is an initial deployment and completed days exist, run the controlled idempotent backfill below. |
| **Needs refresh** or **Late** | The persisted input is older than its expected window. | Check the job-health state, source availability, and server logs. Do not infer flood conditions from stale data. |
| **Last run failed** | A scheduled handler persisted a sanitized failure outcome. | Investigate the source, database, and application logs; correct the root cause; then allow the next scheduled job or an authorized controlled rerun to restore normal state. |
| **Prospective input monitoring** | Forecast rainfall and proxy discharge inputs are being logged for later validation. | Treat it as an audit trail only; it emits neither probability nor public alert. |

## Controlled ERA5 rainfall backfill

The script below uses the same idempotent service as the nightly job. It only writes completed days in the current month and upserts source/date records, so it is suitable for initializing an empty historical-rainfall panel after reviewing the date range.

```bash
pnpm tsx scripts/backfill_current_month_rainfall.mjs
```

After execution, verify that the dashboard reports the expected latest completed date and that the rainfall-history sparkline renders. A failure to backfill must be investigated as a source, network, or database issue; it must not be replaced with estimated or synthetic rainfall.

## Scheduled-refresh failures

Both automated refresh handlers authenticate scheduler-originated requests and record a sanitized success or failure result. Repeated transient source failures receive bounded retries with a request timeout. Operators should use the dashboard health state and server logs to determine whether the failure is transient or persistent. Failure details that could expose internal infrastructure must remain out of public dashboard copy.

If a job is persistently late or failed, retain the current monitoring-only status, preserve historical records, and document the incident and recovery time. Do not delete snapshots to make status appear current. The monitoring system must make staleness visible rather than hiding it.

## Field-evidence governance

Field reports require authenticated submission. Each accepted photo receives a unique managed-storage object key and is verified against the declared image format before upload. A reporter is limited to three submissions in a rolling hour to reduce spam and accidental duplication.

Analysts may only move an observation from **submitted** to either **verified** or **rejected** once. A review rationale is required by the protected interface. Verified reports are evidence for future prospective evaluation; they are not proof that the historical v7 hindcast is accurate and must not be transformed into a public alert.

| Review outcome | Interpretation | Required handling |
|---|---|---|
| **Verified** | An analyst accepted the submitted evidence under the field-observation protocol. | Preserve timestamp, location, evidence reference, and review rationale for future calibration matching. |
| **Rejected** | The evidence did not meet the protocol or could not be verified. | Preserve the review record and rationale; do not delete it or reuse it as a negative flood label without a documented matching rule. |
| **Submitted** | Awaiting analyst disposition. | Do not use for calibration metrics, model promotion, or communication of flood conditions. |

## Incident and release discipline

For application failures, inspect the current server and browser logs, verify the database source state, run the regression suite, and build the production bundle before publishing. Use a saved checkpoint to release verified changes and preserve a rollback point. GitHub synchronization occurs only after the verified project state is saved.

> **Non-alert rule:** No operational intervention may turn a stale input, a proxy discharge feature, a field report, or a historical hindcast probability into a public flood warning. Evidence collection and prospective calibration are required before that policy can be reconsidered.
