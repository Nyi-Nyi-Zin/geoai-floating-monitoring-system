export const TERRAIN_SCREENING_COLORS = {
  LOWER: "#60a5fa",
  MODERATE: "#facc15",
  HIGH: "#fb923c",
  VERY_HIGH: "#ef4444",
} as const;

export const TERRAIN_SCREENING_BANDS = [
  { key: "LOWER", label: "Lower terrain screening", color: TERRAIN_SCREENING_COLORS.LOWER },
  { key: "MODERATE", label: "Moderate terrain screening", color: TERRAIN_SCREENING_COLORS.MODERATE },
  { key: "HIGH", label: "High terrain screening", color: TERRAIN_SCREENING_COLORS.HIGH },
  { key: "VERY_HIGH", label: "Very high terrain screening", color: TERRAIN_SCREENING_COLORS.VERY_HIGH },
] as const;

export type TerrainScreeningBand = keyof typeof TERRAIN_SCREENING_COLORS;

export function terrainScreeningStyle(band: string | null | undefined, showGridCells: boolean, showRiskLayer: boolean) {
  const normalizedBand = band && band in TERRAIN_SCREENING_COLORS ? band as TerrainScreeningBand : "LOWER";
  return {
    color: "#0f172a",
    weight: showGridCells ? 0.3 : 0,
    fillColor: TERRAIN_SCREENING_COLORS[normalizedBand],
    fillOpacity: showRiskLayer ? 0.46 : 0,
  };
}
