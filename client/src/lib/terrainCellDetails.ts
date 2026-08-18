import type { Feature, Geometry } from "geojson";

export type TerrainCellFeature = Feature<Geometry, Record<string, unknown>>;

export type TerrainCellDetail = {
  cellId: string;
  gridReference: string;
  screeningBand: string;
  screeningScore: number | null;
  meanElevationM: number | null;
  localReliefM: number | null;
  distanceToWaterwayM: number | null;
  dominantLandCover: string;
  source: string;
};

function asFiniteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asText(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

export function terrainCellDetail(properties: Record<string, unknown>): TerrainCellDetail {
  const gridI = asFiniteNumber(properties.grid_i);
  const gridJ = asFiniteNumber(properties.grid_j);
  return {
    cellId: asText(properties.id, "Unknown cell"),
    gridReference: gridI === null || gridJ === null ? "Not available" : `${gridI} / ${gridJ}`,
    screeningBand: asText(properties.screening_band, "LOWER"),
    screeningScore: asFiniteNumber(properties.screening_score),
    meanElevationM: asFiniteNumber(properties.elevation_mean_m),
    localReliefM: asFiniteNumber(properties.local_relief_m),
    distanceToWaterwayM: asFiniteNumber(properties.distance_to_waterway_m),
    dominantLandCover: asText(properties.land_cover_dominant_name, "Not available"),
    source: asText(properties.source, "Terrain source"),
  };
}

function pointInRing(lng: number, lat: number, ring: number[][]): boolean {
  let inside = false;
  for (let index = 0, previous = ring.length - 1; index < ring.length; previous = index++) {
    const [currentLng, currentLat] = ring[index] ?? [];
    const [previousLng, previousLat] = ring[previous] ?? [];
    if (currentLng === undefined || currentLat === undefined || previousLng === undefined || previousLat === undefined) continue;
    const crossesLatitude = (currentLat > lat) !== (previousLat > lat);
    const intersectionLng = ((previousLng - currentLng) * (lat - currentLat)) / (previousLat - currentLat) + currentLng;
    if (crossesLatitude && lng < intersectionLng) inside = !inside;
  }
  return inside;
}

function polygonContainsPoint(lng: number, lat: number, rings: number[][][]): boolean {
  return Boolean(rings[0]) && pointInRing(lng, lat, rings[0]) && rings.slice(1).every(ring => !pointInRing(lng, lat, ring));
}

export function findTerrainCellAtLatLng(features: TerrainCellFeature[], lat: number, lng: number): TerrainCellFeature | null {
  for (const feature of features) {
    if (feature.geometry.type === "Polygon" && polygonContainsPoint(lng, lat, feature.geometry.coordinates)) return feature;
    if (feature.geometry.type === "MultiPolygon" && feature.geometry.coordinates.some(polygon => polygonContainsPoint(lng, lat, polygon))) return feature;
  }
  return null;
}
