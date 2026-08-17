import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";

describe("nationwide GloFAS readiness acquisition", () => {
  it("records a bounded source snapshot while prohibiting issue-time feature use and predictive outputs", async () => {
    const source = await readFile(new URL("../scripts/acquire_myanmar_admin1_glofas_readiness.py", import.meta.url), "utf8");

    expect(source).toContain('"past_days": 1');
    expect(source).toContain('"forecast_days": 7');
    expect(source).toContain('"region_count": len(records)');
    expect(source).toContain('"official_issue_timestamp_present": False');
    expect(source).toContain('"usable_as_issue_time_model_feature": False');
    expect(source).toContain('"Monitoring only: this acquisition does not fit a model');
    expect(source).toContain("score, probability, forecast, predicted label, alert");
    expect(source).not.toContain("sklearn");
    expect(source).not.toContain("predict_proba");
  });
});
