type GeoJSONGeometry = {
  type: string;
  coordinates?: unknown;
  geometries?: GeoJSONGeometry[];
};

export type FloodExtentGeoAsset = {
  type: "Feature";
  id: string;
  geometry: GeoJSONGeometry;
  properties: {
    name: string;
    asset_type: "historical_flood_extent";
    source_key: string | null;
    description: string | null;
    metadata: Record<string, unknown>;
    created_at: string;
    updated_at: string;
  };
};

type FloodExtentFeature = {
  type: "Feature";
  id: string;
  geometry: GeoJSONGeometry;
  properties: {
    source_key: string;
    event_name: string;
    observed_date: string;
    sensor: string;
    classification: "flood" | "possible_flood";
    confidence: "high" | "moderate" | "low" | "unknown";
    field_validated: boolean;
    source_name: string;
    source_url: string;
    license_name: string;
    notes: string | null;
    area_km2: number;
    metadata: Record<string, unknown>;
    training_label: true;
    created_at: string;
    updated_at: string;
  };
};

export function floodExtentToGeoAsset(
  feature: FloodExtentFeature,
): FloodExtentGeoAsset {
  return {
    type: "Feature",
    id: feature.id,
    geometry: feature.geometry,
    properties: {
      name: feature.properties.event_name,
      asset_type: "historical_flood_extent",
      source_key: feature.properties.source_key,
      description: feature.properties.notes,
      metadata: {
        ...feature.properties.metadata,
        observed_date: feature.properties.observed_date,
        sensor: feature.properties.sensor,
        classification: feature.properties.classification,
        confidence: feature.properties.confidence,
        field_validated: feature.properties.field_validated,
        source_name: feature.properties.source_name,
        source_url: feature.properties.source_url,
        license_name: feature.properties.license_name,
        area_km2: feature.properties.area_km2,
        training_label: feature.properties.training_label,
      },
      created_at: feature.properties.created_at,
      updated_at: feature.properties.updated_at,
    },
  };
}

export async function fetchFloodExtents(
  apiBaseUrl: string,
  signal?: AbortSignal,
): Promise<FloodExtentGeoAsset[]> {
  const response = await fetch(
    `${apiBaseUrl.replace(/\/$/, "")}/flood-extents?page=1&page_size=500`,
    { signal },
  );
  if (!response.ok) {
    throw new Error(`Flood extents API returned HTTP ${response.status}`);
  }
  const collection = (await response.json()) as {
    features: FloodExtentFeature[];
  };
  return collection.features.map(floodExtentToGeoAsset);
}
