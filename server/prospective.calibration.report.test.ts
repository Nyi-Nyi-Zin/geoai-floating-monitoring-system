import fs from "node:fs";
import { describe, expect, it } from "vitest";

const project = "/home/ubuntu/deltawatch-permanent";

describe("prospective calibration baseline", () => {
  it("withholds prospective accuracy metrics when no verified observations and no frozen scores exist", () => {
    const report = fs.readFileSync(`${project}/model_pipeline/prospective_calibration_report_baseline.md`, "utf8");
    const baseline = JSON.parse(fs.readFileSync(`${project}/model_pipeline/prospective_calibration_report_baseline.json`, "utf8"));
    expect(baseline.evidence.verified).toBe(0);
    expect(baseline.prospectiveSnapshots.snapshotCount).toBeGreaterThan(0);
    expect(baseline.metricsStatus).toBe("withheld_no_verified_matched_outcomes_and_no_prospective_scores");
    expect(report).toContain("Producing an accuracy number would therefore be unsupported.");
    expect(report).toContain("30 verified positive and 30 verified negative observations");
  });
});
