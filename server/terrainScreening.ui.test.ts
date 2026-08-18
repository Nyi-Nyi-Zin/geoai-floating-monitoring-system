import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";
import { TERRAIN_SCREENING_COLORS, terrainScreeningStyle } from "../client/src/lib/terrainScreening";

describe("Maubin terrain-screening presentation", () => {
  it("renders four static terrain bands instead of colouring the public layer with historical hindcast probabilities", async () => {
    const source = await readFile(new URL("../client/src/pages/Home.tsx", import.meta.url), "utf8");
    expect(source).toContain("Terrain screening bands");
    expect(source).toContain("Static terrain screening, not a real-time probability or warning.");
    expect(source).toContain("terrainScreeningStyle(band, layers.gridCells, layers.floodRisk)");
    expect(source).toContain("const riskStyle = (feature?: SpatialFeature) => {");
  });

  it("maps every actual terrain-screening band to its stable color and never derives a public style from hindcast probability", () => {
    expect(terrainScreeningStyle("LOWER", false, true)).toMatchObject({ fillColor: TERRAIN_SCREENING_COLORS.LOWER, fillOpacity: 0.46, weight: 0 });
    expect(terrainScreeningStyle("MODERATE", false, true)).toMatchObject({ fillColor: TERRAIN_SCREENING_COLORS.MODERATE });
    expect(terrainScreeningStyle("HIGH", true, true)).toMatchObject({ fillColor: TERRAIN_SCREENING_COLORS.HIGH, weight: 0.3 });
    expect(terrainScreeningStyle("VERY_HIGH", false, true)).toMatchObject({ fillColor: TERRAIN_SCREENING_COLORS.VERY_HIGH });
    expect(terrainScreeningStyle("unknown", false, true)).toMatchObject({ fillColor: TERRAIN_SCREENING_COLORS.LOWER });
    expect(terrainScreeningStyle("HIGH", false, false)).toMatchObject({ fillOpacity: 0 });
  });
});
