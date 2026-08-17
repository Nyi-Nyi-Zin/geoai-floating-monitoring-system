import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";

describe("nationwide coverage mode", () => {
  it("loads Admin 1 geometry only after the coverage mode is selected and preserves the no-prediction boundary", async () => {
    const source = await readFile(new URL("../client/src/pages/Home.tsx", import.meta.url), "utf8");
    expect(source).toContain('fetch("/api/spatial/national-admin/regions")');
    expect(source).toContain('fetch("/api/spatial/national-admin/evidence-readiness")');
    expect(source).toContain("if (!nationwideMode || nationalRegions) return;");
    expect(source).toContain("setNationalLoading(true);");
    expect(source).toContain("historical source coverage only");
    expect(source).toContain("Flood prediction, probability, and regional accuracy are not yet assessed.");
    expect(source).toContain("Historical source evidence");
    expect(source).toContain("not a forecast");
  });
});
