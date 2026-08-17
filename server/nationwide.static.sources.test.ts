import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";

describe("nationwide static source aggregation safeguards", () => {
  it("uses bounded remote COG overviews and retains the no-prediction boundary", async () => {
    const [dem, worldcover] = await Promise.all([
      readFile(new URL("../scripts/aggregate_myanmar_copernicus_dem_admin1.py", import.meta.url), "utf8"),
      readFile(new URL("../scripts/aggregate_myanmar_worldcover_admin1.py", import.meta.url), "utf8"),
    ]);

    expect(dem).toContain("OVERVIEW_SIDE = 100");
    expect(dem).toContain("deltawatch-myanmar-admin1-copernicus-dem-static-v1");
    expect(dem).toContain("No model is fitted and no predictive or life-safety output is created");
    expect(worldcover).toContain("OVERVIEW_SIDE = 120");
    expect(worldcover).toContain("Resampling.mode");
    expect(worldcover).toContain("deltawatch-myanmar-admin1-worldcover-static-v1");
    expect(worldcover).toContain("No model is fitted and no predictive or life-safety output is created");
  });
});
