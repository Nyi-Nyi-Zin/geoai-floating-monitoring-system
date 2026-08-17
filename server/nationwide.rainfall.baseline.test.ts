import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";

describe("nationwide rainfall-only temporal baseline", () => {
  it("records the sparse baseline as rejected and blocks model-output promotion", async () => {
    const evaluation = await readFile(new URL("../model_pipeline/myanmar_rainfall_temporal_baseline_evaluation.md", import.meta.url), "utf8");
    expect(evaluation).toContain("**Status:** Rejected diagnostic baseline; not a nationwide prediction model.");
    expect(evaluation).toContain("The frozen 2018 holdout was not used for threshold selection.");
    expect(evaluation).toContain("No model artefact, probability, forecast, risk score, or alert has been exported.");
  });
});
