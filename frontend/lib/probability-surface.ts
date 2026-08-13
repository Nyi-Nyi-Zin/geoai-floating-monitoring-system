/** Continuous flood probability color scale (0 = green → 1 = red). */
export const PROBABILITY_COLOR_STOPS = [
  { t: 0.0, rgb: [34, 197, 94] as const },
  { t: 0.2, rgb: [163, 230, 53] as const },
  { t: 0.4, rgb: [234, 179, 8] as const },
  { t: 0.6, rgb: [249, 115, 22] as const },
  { t: 0.8, rgb: [239, 68, 68] as const },
  { t: 1.0, rgb: [220, 38, 38] as const },
] as const;

export const PROBABILITY_GRADIENT_CSS =
  "linear-gradient(to right, #22c55e 0%, #a3e635 20%, #eab308 40%, #f97316 60%, #ef4444 80%, #dc2626 100%)";

export type ProbabilitySample = {
  lat: number;
  lng: number;
  probability: number;
  id?: string;
};

export type SampleSpatialIndex = {
  cellSizeM: number;
  cells: Map<string, ProbabilitySample[]>;
};

/** Grid cell size used for model predictions (meters). */
export const PREDICTION_CELL_SIZE_M = 500;

/**
 * Max distance for IDW blending — roughly one cell diagonal so we smooth
 * between adjacent predictions without extrapolating far beyond coverage.
 */
export const PROBABILITY_INTERPOLATION_RADIUS_M =
  PREDICTION_CELL_SIZE_M * Math.SQRT2 * 0.55;

function clampProbability(probability: number) {
  return Math.max(0, Math.min(1, probability));
}

function interpolateRgb(
  start: readonly [number, number, number],
  end: readonly [number, number, number],
  ratio: number,
): [number, number, number] {
  return [
    Math.round(start[0] + (end[0] - start[0]) * ratio),
    Math.round(start[1] + (end[1] - start[1]) * ratio),
    Math.round(start[2] + (end[2] - start[2]) * ratio),
  ];
}

export function probabilityColorRgb(probability: number): [number, number, number] {
  const p = clampProbability(probability);
  for (let index = 1; index < PROBABILITY_COLOR_STOPS.length; index += 1) {
    const upper = PROBABILITY_COLOR_STOPS[index];
    const lower = PROBABILITY_COLOR_STOPS[index - 1];
    if (p <= upper.t) {
      const span = upper.t - lower.t || 1;
      const ratio = (p - lower.t) / span;
      return interpolateRgb(lower.rgb, upper.rgb, ratio);
    }
  }
  return [...PROBABILITY_COLOR_STOPS[PROBABILITY_COLOR_STOPS.length - 1].rgb];
}

export function continuousProbabilityColor(probability: number): string {
  const [r, g, b] = probabilityColorRgb(probability);
  return `rgb(${r}, ${g}, ${b})`;
}

/** @deprecated Use continuousProbabilityColor for probability layers. */
export function mlProbabilityColor(probability: number): string {
  return continuousProbabilityColor(probability);
}

export function distanceMeters(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number,
): number {
  const meanLatRad = ((lat1 + lat2) * Math.PI) / 360;
  const dLat = (lat2 - lat1) * 111_320;
  const dLng = (lng2 - lng1) * 111_320 * Math.cos(meanLatRad);
  return Math.hypot(dLat, dLng);
}

function spatialCellKey(lat: number, lng: number, cellSizeM: number): string {
  const latIndex = Math.floor((lat * 111_320) / cellSizeM);
  const lngIndex = Math.floor(
    (lng * 111_320 * Math.cos((lat * Math.PI) / 180)) / cellSizeM,
  );
  return `${latIndex}:${lngIndex}`;
}

function nearbySpatialCellKeys(
  lat: number,
  lng: number,
  cellSizeM: number,
  ring: number,
): string[] {
  const latIndex = Math.floor((lat * 111_320) / cellSizeM);
  const lngIndex = Math.floor(
    (lng * 111_320 * Math.cos((lat * Math.PI) / 180)) / cellSizeM,
  );
  const keys: string[] = [];
  for (let dLat = -ring; dLat <= ring; dLat += 1) {
    for (let dLng = -ring; dLng <= ring; dLng += 1) {
      keys.push(`${latIndex + dLat}:${lngIndex + dLng}`);
    }
  }
  return keys;
}

export function buildSampleSpatialIndex(
  samples: ProbabilitySample[],
  cellSizeM = PREDICTION_CELL_SIZE_M,
): SampleSpatialIndex {
  const cells = new Map<string, ProbabilitySample[]>();
  for (const sample of samples) {
    const key = spatialCellKey(sample.lat, sample.lng, cellSizeM);
    const bucket = cells.get(key);
    if (bucket) {
      bucket.push(sample);
    } else {
      cells.set(key, [sample]);
    }
  }
  return { cellSizeM, cells };
}

function idwFromSamples(
  lat: number,
  lng: number,
  samples: Iterable<ProbabilitySample>,
  maxDistanceM: number,
  power: number,
): number | null {
  let weightSum = 0;
  let valueSum = 0;

  for (const sample of samples) {
    const distance = distanceMeters(lat, lng, sample.lat, sample.lng);
    if (distance > maxDistanceM) continue;
    if (distance < 0.5) return sample.probability;
    const weight = 1 / distance ** power;
    weightSum += weight;
    valueSum += weight * sample.probability;
  }

  if (weightSum === 0) return null;
  return valueSum / weightSum;
}

/**
 * Inverse-distance weighting limited to nearby grid samples.
 * Returns null outside the interpolation radius (no false precision).
 */
export function interpolateProbabilityIdw(
  lat: number,
  lng: number,
  samples: ProbabilitySample[],
  maxDistanceM = PROBABILITY_INTERPOLATION_RADIUS_M,
  power = 2,
): number | null {
  return idwFromSamples(lat, lng, samples, maxDistanceM, power);
}

export function interpolateProbabilityIdwIndexed(
  lat: number,
  lng: number,
  index: SampleSpatialIndex,
  maxDistanceM = PROBABILITY_INTERPOLATION_RADIUS_M,
  power = 2,
): number | null {
  const ring = Math.max(1, Math.ceil(maxDistanceM / index.cellSizeM));
  const keys = nearbySpatialCellKeys(lat, lng, index.cellSizeM, ring);
  const nearbySamples: ProbabilitySample[] = [];
  for (const key of keys) {
    const bucket = index.cells.get(key);
    if (bucket) nearbySamples.push(...bucket);
  }
  return idwFromSamples(lat, lng, nearbySamples, maxDistanceM, power);
}

/** Nearest grid sample for map click selection. */
export function findNearestSample(
  lat: number,
  lng: number,
  index: SampleSpatialIndex,
  maxDistanceM = PREDICTION_CELL_SIZE_M * 0.55,
): ProbabilitySample | null {
  const ring = Math.max(1, Math.ceil(maxDistanceM / index.cellSizeM));
  let nearest: ProbabilitySample | null = null;
  let nearestDistance = maxDistanceM;

  for (const key of nearbySpatialCellKeys(lat, lng, index.cellSizeM, ring)) {
    const bucket = index.cells.get(key);
    if (!bucket) continue;
    for (const sample of bucket) {
      const distance = distanceMeters(lat, lng, sample.lat, sample.lng);
      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearest = sample;
      }
    }
  }

  return nearest;
}

export function polygonCentroid(
  coordinates: unknown,
): [number, number] | null {
  const ring = extractOuterRing(coordinates);
  if (!ring.length) return null;

  let sumLat = 0;
  let sumLng = 0;
  for (const [lng, lat] of ring) {
    sumLat += lat;
    sumLng += lng;
  }
  return [sumLat / ring.length, sumLng / ring.length];
}

function extractOuterRing(value: unknown): [number, number][] {
  if (!Array.isArray(value)) return [];
  if (
    value.length >= 2 &&
    typeof value[0] === "number" &&
    typeof value[1] === "number"
  ) {
    return [[value[0], value[1]]];
  }
  if (
    value.length > 0 &&
    Array.isArray(value[0]) &&
    typeof value[0][0] === "number"
  ) {
    return value as [number, number][];
  }
  if (value.length > 0 && Array.isArray(value[0])) {
    return extractOuterRing(value[0]);
  }
  return [];
}
