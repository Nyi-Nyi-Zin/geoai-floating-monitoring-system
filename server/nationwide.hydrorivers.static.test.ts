import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";

describe("nationwide HydroRIVERS static aggregation", () => {
  it("uses Admin 1 geometric intersections and preserves the no-prediction boundary", async () => {
    const source = await readFile(new URL("../scripts/aggregate_myanmar_hydrorivers_admin1.py", import.meta.url), "utf8");
    expect(source).toContain("line.intersection(geometries[region_index])");
    expect(source).toContain("deltawatch-myanmar-admin1-hydrorivers-static-v1");
    expect(source).toContain("does not create features for a fitted model, risk score, probability, forecast, or alert");
  });
});
