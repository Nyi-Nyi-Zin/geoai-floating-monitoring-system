import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

type ModelSeed = {
  model: {
    version: string;
    status: string;
    threshold: number;
    metrics: { f1: number; roc_auc: number; precision: number };
    comparison: { v6: { f1: number }; v7: { f1: number } };
    predictors: { tide: string };
  };
  predictions: Array<{ event_id: string; cell_id: string; probability: number; prediction_status: string }>;
};

describe("v7 hindcast seed", () => {
  it("contains experimental out-of-sample predictions and improves the common held-out F1 over v6", () => {
    const seed = JSON.parse(readFileSync("/home/ubuntu/webdev-static-assets/maubin_hindcast_seed_v7.json", "utf8")) as ModelSeed;

    expect(seed.model.version).toBe("maubin-flood-event-hgb-v7");
    expect(seed.model.status).toBe("experimental");
    expect(seed.model.threshold).toBe(0.71);
    expect(seed.model.metrics.roc_auc).toBeGreaterThan(0.7);
    expect(seed.model.comparison.v7.f1).toBeGreaterThan(seed.model.comparison.v6.f1);
    expect(seed.model.predictors.tide).toContain("deferred");
    expect(seed.predictions.length).toBeGreaterThan(0);
    expect(seed.predictions.every(prediction => prediction.prediction_status === "chronological_out_of_sample")).toBe(true);
  });
});
