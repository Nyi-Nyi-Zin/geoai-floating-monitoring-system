import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";

describe("nationwide regional candidate gates", () => {
  it("joins static context under frozen splits and stops before any model output when prerequisites are absent", async () => {
    const [joiner, audit] = await Promise.all([
      readFile(new URL("../scripts/build_myanmar_admin1_static_feature_table.py", import.meta.url), "utf8"),
      readFile(new URL("../scripts/audit_myanmar_admin1_candidate_gates.py", import.meta.url), "utf8"),
    ]);

    expect(joiner).toContain('"observed_flood_presence"');
    expect(joiner).toContain('"flooded_fraction_label"');
    expect(joiner).toContain('4632: "holdout", 4666: "holdout"');
    expect(joiner).toContain("No model is fitted and no flood probability, forecast, risk score, predicted label, or alert is created.");
    expect(audit).toContain('"fit_authorized": False');
    expect(audit).toContain('"promotion_authorized": False');
    expect(audit).toContain('"model_artifact_created": False');
    expect(audit).toContain('"predictive_output_created": False');
    expect(audit).toContain("Mandatory upstream-flow proxy and latency provenance are absent");
  });
});
