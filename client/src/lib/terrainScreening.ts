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

export const HISTORICAL_HINCAST_HEATMAP_BANDS = [
  { key: "LOW", label: "Lower historical model output", color: "#312e81" },
  { key: "MODERATE", label: "Moderate historical model output", color: "#7e22ce" },
  { key: "ELEVATED", label: "Elevated historical model output", color: "#c026d3" },
  { key: "HIGH", label: "Higher historical model output", color: "#e11d48" },
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

export function historicalHindcastHeatmapStyle(probability: number | null | undefined, visible: boolean) {
  const value = Math.max(0, Math.min(1, Number(probability ?? 0)));
  const band = value < 0.25 ? HISTORICAL_HINCAST_HEATMAP_BANDS[0]
    : value < 0.5 ? HISTORICAL_HINCAST_HEATMAP_BANDS[1]
      : value < 0.75 ? HISTORICAL_HINCAST_HEATMAP_BANDS[2]
        : HISTORICAL_HINCAST_HEATMAP_BANDS[3];
  return {
    color: "#fdf4ff",
    weight: 0,
    fillColor: band.color,
    fillOpacity: visible ? 0.68 : 0,
  };
}
