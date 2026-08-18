import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";
import { historicalHindcastHeatmapStyle } from "../client/src/lib/terrainScreening";

describe("Maubin historical-event HGB v7 heatmap", () => {
  it("uses four categorical replay bands and remains hidden while its separate layer is disabled", () => {
    expect(historicalHindcastHeatmapStyle(0.1, true)).toMatchObject({ fillColor: "#312e81", fillOpacity: 0.68 });
    expect(historicalHindcastHeatmapStyle(0.3, true)).toMatchObject({ fillColor: "#7e22ce" });
    expect(historicalHindcastHeatmapStyle(0.6, true)).toMatchObject({ fillColor: "#c026d3" });
    expect(historicalHindcastHeatmapStyle(0.9, true)).toMatchObject({ fillColor: "#e11d48" });
    expect(historicalHindcastHeatmapStyle(0.9, false)).toMatchObject({ fillOpacity: 0 });
  });

  it("keeps the historical replay control separate from terrain screening and forbids a current or future public output", async () => {
    const source = await readFile(new URL("../client/src/pages/Home.tsx", import.meta.url), "utf8");
    expect(source).toContain('"historicalModelHeatmap", "Historical HGB v7 heatmap"');
    expect(source).toContain("historicalHindcastHeatmapStyle(");
    expect(source).toContain("replay only — experimental HGB v7 output for the selected past event");
    expect(source).toContain("Not a current or future flood probability, forecast, or warning.");
    expect(source).toContain("terrainScreeningStyle(band, layers.gridCells, layers.floodRisk)");
    expect(source).toContain("How to read the monitoring layers");
    expect(source).toContain("Flood Risk</b> is static terrain screening");
    expect(source).toContain("Historical HGB v7</b> is a selected past-event model replay");
    expect(source).toContain("Prospective monitoring</b> logs incoming inputs for validation only");
    expect(source).toContain("public alerts and probabilities are disabled");
  });
});
