import { describe, expect, it } from "vitest";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

describe("nationwide non-login source-quality manifest", () => {
  it("records real coverage and preserves the EWDS terms blocker with no predictive authorization", async () => {
    const { stdout } = await execFileAsync("python3", ["scripts/build_myanmar_nonlogin_source_quality_manifest.py"], { cwd: process.cwd() });
    const manifest = JSON.parse(stdout) as {
      expected_admin1_region_count: number;
      sources: Array<{ artefact: string; region_count?: number; region_coverage_complete?: boolean; model_feature_authorized?: boolean }>;
      ewds_issue_time_probe: { status: string; blocker: string; issue_time_feature_authorized: boolean; model_feature_authorized: boolean };
      candidate_gate: { status: string; model_status: string; promotion_authorized: boolean };
      safety: string;
    };
    expect(manifest.expected_admin1_region_count).toBe(18);
    expect(manifest.sources.filter(source => source.region_coverage_complete).map(source => source.artefact)).toEqual(expect.arrayContaining([
      "myanmar_admin1_event_rainfall_lags.csv",
      "myanmar_admin1_copernicus_dem_static.json",
      "myanmar_admin1_worldcover_static.json",
      "myanmar_admin1_hydrorivers_static.json",
    ]));
    expect(manifest.sources.every(source => source.model_feature_authorized === false)).toBe(true);
    expect(manifest.ewds_issue_time_probe).toMatchObject({
      status: "access_blocked",
      blocker: "dataset_terms_not_accepted",
      issue_time_feature_authorized: false,
      model_feature_authorized: false,
    });
    expect(manifest.candidate_gate).toMatchObject({ status: "no_fit_authorized", model_status: "not_fitted", promotion_authorized: false });
    expect(manifest.safety).toContain("no scores, probabilities, predictions, forecasts, alerts");
  });
});
