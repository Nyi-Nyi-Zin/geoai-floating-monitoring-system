import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";
import { findTerrainCellAtLatLng, terrainCellDetail } from "../client/src/lib/terrainCellDetails";

describe("Maubin grid-cell detail interaction", () => {
  it("maps actual terrain-cell properties into static context without exposing a public flood probability", () => {
    const detail = terrainCellDetail({
      id: "cell-42",
      grid_i: 12,
      grid_j: 34,
      screening_band: "HIGH",
      screening_score: 73.2,
      elevation_mean_m: 1.8,
      local_relief_m: 0.3,
      distance_to_waterway_m: 56.7,
      land_cover_dominant_name: "Cropland",
      source: "Copernicus DEM GLO-30",
    });
    expect(detail).toMatchObject({ cellId: "cell-42", gridReference: "12 / 34", screeningBand: "HIGH", screeningScore: 73.2, dominantLandCover: "Cropland" });
    expect(detail).not.toHaveProperty("probability");
    expect(detail).not.toHaveProperty("alert");
  });

  it("binds terrain-cell clicks to a closeable monitoring-only detail card", async () => {
    const source = await readFile(new URL("../client/src/pages/Home.tsx", import.meta.url), "utf8");
    expect(source).toContain("onEachFeature={bindTerrainCellDetail}");
    expect(source).toContain("TerrainCellClickCapture terrain={overlayTerrain} onSelect={setSelectedCell}");
    expect(source).toContain("Terrain cell details");
    expect(source).toContain("Selected historical event context");
    expect(source).toContain("selectedHindcastCell.predicted_label");
    expect(source).toContain("Static terrain context only — not a flood probability, forecast, or warning.");
    expect(source).toContain("setSelectedCell(null)");
    expect(source).not.toContain("Selected cell probability");
  });

  it("resolves a clicked map coordinate to the matching terrain polygon before opening a detail card", () => {
    const feature = {
      type: "Feature" as const,
      properties: { id: "cell-a" },
      geometry: { type: "Polygon" as const, coordinates: [[[95, 16], [96, 16], [96, 17], [95, 17], [95, 16]]] },
    };
    expect(findTerrainCellAtLatLng([feature], 16.5, 95.5)?.properties.id).toBe("cell-a");
    expect(findTerrainCellAtLatLng([feature], 18, 95.5)).toBeNull();
  });
});
