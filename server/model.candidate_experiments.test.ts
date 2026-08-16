import fs from "node:fs";
import { describe, expect, it } from "vitest";

type Metrics = { f1: number; pr_auc: number; roc_auc: number };
type CandidateReport = { models: Record<string, { validation: Metrics; test: Metrics }> };

const output = "/home/ubuntu/deltawatch-model-outputs";

function readReport(name: string): CandidateReport {
  return JSON.parse(fs.readFileSync(`${output}/${name}`, "utf8")) as CandidateReport;
}

describe("v9-v12 candidate promotion guardrail", () => {
  it("retains v7 unless an experiment improves validation and independent 2018 discrimination", () => {
    const v9 = readReport("candidate_metrics_v9_regularization.json");
    const v10 = readReport("candidate_metrics_v10_historical_susceptibility.json");
    const v11 = readReport("candidate_metrics_v11_spatial_location.json");
    const v12 = readReport("candidate_metrics_v12_feature_representation.json");
    const baseline = v9.models.v7_hgb_reproduction;

    expect(baseline.validation.f1).toBe(0.4933);
    expect(baseline.test).toMatchObject({ f1: 0.1884, pr_auc: 0.132, roc_auc: 0.7088 });

    const candidates = [
      v9.models.v9_hgb_regularized_sqrt_weight,
      v10.models.v10_hgb_prior_flood_rate_only,
      v11.models.v11_hgb_centroid_coordinates,
      v12.models.v12_hgb_onehot_landcover,
    ];

    for (const candidate of candidates) {
      const qualifies = candidate.validation.f1 > baseline.validation.f1
        && candidate.test.f1 >= baseline.test.f1
        && candidate.test.pr_auc >= baseline.test.pr_auc
        && candidate.test.roc_auc >= baseline.test.roc_auc;
      expect(qualifies).toBe(false);
    }
  });

  it("documents strict historical-label and pre-event leakage controls", () => {
    const v10Source = fs.readFileSync("/home/ubuntu/deltawatch-permanent/model_pipeline/train_v10_historical_susceptibility.py", "utf8");
    const v12Source = fs.readFileSync("/home/ubuntu/deltawatch-permanent/model_pipeline/train_v12_feature_representation_candidates.py", "utf8");
    expect(v10Source).toContain("event_start >= pd.Timestamp(TEST_START)");
    expect(v10Source).toContain("No labels from the test interval can become historical predictors.");
    expect(v12Source).toContain("pre-event hydrologic ratios");
  });
});
