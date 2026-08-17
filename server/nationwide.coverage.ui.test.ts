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
    expect(source).toContain("Static context & candidate gate");
    expect(source).toContain("No nationwide candidate fitted");
    expect(source).toContain("Upstream-flow readiness");
    expect(source).toContain("not a model feature");
    expect(source).toContain("Official issue-time flow access");
    expect(source).toContain("EWDS terms acceptance required");
    expect(source).toContain("Non-login source quality");
    expect(source).toContain("no candidate");
    expect(source).toContain("Prospective validation");
    expect(source).toContain("No verified nationwide outcomes yet");
    expect(source).toContain("not a forecast");
  });
});
