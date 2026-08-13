type GeoJSONGeometry = {
  type: string;
  coordinates?: unknown;
  geometries?: GeoJSONGeometry[];
};

export type ObservedWaterExtentGeoAsset = {
  type: "Feature";
  id: string;
  geometry: GeoJSONGeometry;
  properties: {
    name: string;
    asset_type: "observed_water_extent";
    source_key: string | null;
    description: string | null;
    metadata: Record<string, unknown>;
    created_at: string;
    updated_at: string;
  };
};

type ObservedWaterExtentFeature = {
  type: "Feature";
  id: string;
  geometry: GeoJSONGeometry;
  properties: {
    source_key: string;
    name: string;
    observed_at: string;
    source: string;
    method: string;
    confidence_score: number | null;
    event_id: string | null;
    source_name: string;
    source_url: string;
    license_name: string;
    notes: string | null;
    area_km2: number;
    metadata: Record<string, unknown>;
    product_type: "observed_water_extent";
    created_at: string;
    updated_at: string;
  };
};

export type ObservedWaterExtentCollection = {
  features: ObservedWaterExtentFeature[];
  summary: {
    latest_observed_at: string | null;
    latest_source: string | null;
    latest_method: string | null;
  };
  limitations: string[];
};

export function observedWaterExtentToGeoAsset(
  feature: ObservedWaterExtentFeature,
): ObservedWaterExtentGeoAsset {
  return {
    type: "Feature",
    id: feature.id,
    geometry: feature.geometry,
    properties: {
      name: feature.properties.name,
      asset_type: "observed_water_extent",
      source_key: feature.properties.source_key,
      description: feature.properties.notes,
      metadata: {
        ...feature.properties.metadata,
        observed_at: feature.properties.observed_at,
        source: feature.properties.source,
        method: feature.properties.method,
        confidence_score: feature.properties.confidence_score,
        event_id: feature.properties.event_id,
        source_name: feature.properties.source_name,
        source_url: feature.properties.source_url,
        license_name: feature.properties.license_name,
        area_km2: feature.properties.area_km2,
        product_type: feature.properties.product_type,
      },
      created_at: feature.properties.created_at,
      updated_at: feature.properties.updated_at,
    },
  };
}

export async function fetchObservedWaterExtents(
  apiBaseUrl: string,
  signal?: AbortSignal,
): Promise<{
  features: ObservedWaterExtentGeoAsset[];
  summary: ObservedWaterExtentCollection["summary"];
  limitations: string[];
}> {
  const response = await fetch(
    `${apiBaseUrl.replace(/\/$/, "")}/observed-water-extents?page=1&page_size=500`,
    { signal },
  );
  if (!response.ok) {
    throw new Error(
      `Observed water extents API returned HTTP ${response.status}`,
    );
  }
  const collection = (await response.json()) as ObservedWaterExtentCollection;
  return {
    features: collection.features.map(observedWaterExtentToGeoAsset),
    summary: collection.summary,
    limitations: collection.limitations,
  };
}
