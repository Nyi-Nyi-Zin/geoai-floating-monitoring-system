import "server-only";

export type GeoJSONGeometry = {
  type: string;
  coordinates?: unknown;
  geometries?: GeoJSONGeometry[];
};

export type GeoAsset = {
  type: "Feature";
  id: string;
  geometry: GeoJSONGeometry;
  properties: {
    name: string;
    asset_type: string;
    source_key: string | null;
    description: string | null;
    metadata: Record<string, unknown>;
    created_at: string;
    updated_at: string;
  };
};

type FeatureCollection = {
  type: "FeatureCollection";
  features: GeoAsset[];
  meta: {
    page: number;
    page_size: number;
    total: number;
    pages: number;
  };
};

export type Health = {
  status: "healthy" | "degraded";
  service: string;
  version: string;
  environment: string;
  database: {
    status: "healthy" | "unhealthy" | "not_configured";
    detail: string | null;
  };
};

export type RainfallForecast = {
  status: "available";
  location: {
    name: string;
    latitude: number;
    longitude: number;
    timezone: string;
  };
  fetched_at: string;
  source: string;
  attribution_url: string;
  cached: boolean;
  hourly: {
    time: string;
    precipitation_mm: number;
    probability_percent: number | null;
  }[];
  daily: {
    date: string;
    precipitation_sum_mm: number;
    probability_max_percent: number | null;
  }[];
};

export type RainfallHistory = {
  status: "available" | "unavailable";
  source_key: string;
  source_name: string;
  model: "ERA5";
  source_resolution_m: number;
  grid_cell_count: number;
  daily: {
    date: string;
    mean_precipitation_mm: number;
    max_precipitation_mm: number;
    p90_precipitation_mm: number;
    accumulation_3d_mm: number;
    accumulation_7d_mm: number;
    accumulation_30d_mm: number;
  }[];
  summary: {
    start_date: string | null;
    end_date: string | null;
    days: number;
    wet_days: number;
    total_mean_precipitation_mm: number;
    peak_daily_mean_mm: number;
    peak_daily_mean_date: string | null;
    peak_7d_mm: number;
    peak_7d_end_date: string | null;
  };
  attribution: string;
  limitations: string[];
};

export type FloodMlPredictionIndexItem = {
  id: string;
  probability: number;
  risk_band: "LOW" | "MODERATE" | "HIGH" | "VERY_HIGH";
  predicted_label: boolean;
  flooded_fraction: number;
  historical_event_count: number;
  historical_event_density: number;
  explanation: Record<string, unknown>;
};

export type FloodMlPredictionIndex = {
  model: {
    id: string;
    model_version: string;
    algorithm: string;
    status: string;
    target_name: string;
    target_threshold: number;
    training_rows: number;
    positive_rows: number;
    negative_rows: number;
    feature_names: string[];
    metrics: Record<string, unknown>;
    feature_importance: Record<string, number>;
    methodology: Record<string, unknown>;
    trained_at: string;
    operational_forecast: false;
  };
  items: FloodMlPredictionIndexItem[];
  summary: {
    total_cells: number;
    mean_probability: number;
    predicted_positive_cells: number;
    band_counts: Record<"LOW" | "MODERATE" | "HIGH" | "VERY_HIGH", number>;
  };
  limitations: string[];
};

export type FloodEventMlPredictionItem = {
  id: string;
  probability: number;
  predicted_label: boolean;
  flooded_fraction: number;
  outcome?: "tp" | "fp" | "fn" | "tn";
  decision_probability?: number;
};

export type FloodEventMlEventSummary = {
  event_id: string;
  event_start_date: string;
  split: "validation" | "test";
  total_cells: number;
  observed_positive_cells: number;
};

export type FloodEventMlEvaluationReport = {
  model_version: string;
  algorithm: string;
  trained_at: string;
  active_threshold_mode: string;
  decision_threshold: number;
  water_temper_beta: number;
  test: Record<string, unknown>;
  test_by_threshold_mode: Record<string, unknown>;
  test_by_event: Record<string, unknown>;
  rolling_origin_summary: Record<string, unknown>;
  ranking_quality: Record<string, unknown>;
  test_calibration: Record<string, unknown>;
  false_positive_diagnostics: Array<Record<string, unknown>>;
  recommendation: string;
  limitations: string[];
};

export type FloodEventMlPredictionIndex = {
  model: {
    id: string;
    model_version: string;
    algorithm: string;
    status: "experimental";
    target_name: string;
    target_threshold: number;
    decision_threshold: number;
    dataset_rows: number;
    train_rows: number;
    positive_rows: number;
    negative_rows: number;
    event_count: number;
    feature_names: string[];
    metrics: Record<string, unknown>;
    feature_importance: Record<string, number>;
    split_events: Record<string, string[]>;
    methodology: Record<string, unknown>;
    trained_at: string;
    operational_forecast: false;
    display_mode: "historical_hindcast";
    operating_mode: "screening" | "balanced" | "conservative" | "model_default";
  };
  event: FloodEventMlEventSummary;
  available_events: FloodEventMlEventSummary[];
  items: FloodEventMlPredictionItem[];
  summary: {
    total_cells: number;
    mean_probability: number;
    predicted_positive_cells: number;
    observed_positive_cells: number;
    true_positive_cells: number;
    false_positive_cells: number;
    false_negative_cells: number;
    precision: number;
    recall: number;
  };
  limitations: string[];
};

export type ForecastPredictionItem = {
  id: string;
  probability: number;
  predicted_label: boolean;
  risk_band: "LOW" | "MODERATE" | "HIGH" | "VERY_HIGH";
};

export type ForecastRunSummary = {
  id: string;
  run_version: string;
  model_id: string;
  model_version: string;
  status: string;
  forecast_type: string;
  rainfall_source: string;
  rainfall_fetched_at: string;
  forecast_horizon_days: number;
  target_date: string;
  decision_threshold: number;
  threshold_mode: string;
  cell_count: number;
  flagged_cell_count: number;
  summary_metrics: Record<string, unknown>;
  limitations: string[];
  created_at: string;
  experimental: true;
};

export type ForecastPredictionIndex = {
  run: ForecastRunSummary;
  items: ForecastPredictionItem[];
  summary: {
    total_cells: number;
    mean_probability: number;
    flagged_cells: number;
    band_counts: Record<"LOW" | "MODERATE" | "HIGH" | "VERY_HIGH", number>;
  };
  limitations: string[];
  display_mode: "scenario_forecast";
};

export type HydroObservation = {
  type: "Feature";
  id: string;
  geometry: GeoJSONGeometry;
  properties: {
    station_id: string;
    station_name: string;
    observed_at: string;
    rainfall_mm: number | null;
    water_level_m: number | null;
    discharge_m3s: number | null;
    soil_moisture_percent: number | null;
    battery_percent: number | null;
    source: string;
    quality_status: "unverified" | "provisional" | "verified" | "rejected";
    notes: string | null;
    created_at: string;
    updated_at: string;
  };
};

export type SensorStation = {
  type: "Feature";
  id: string;
  geometry: GeoJSONGeometry;
  properties: {
    station_id: string;
    name: string;
    river_name: string | null;
    description: string | null;
    status: "active" | "offline" | "maintenance";
    warning_level_cm: number | null;
    danger_level_cm: number | null;
    critical_level_cm: number | null;
    metadata: Record<string, unknown>;
    installed_at: string | null;
    last_seen_at: string | null;
    created_at: string;
    updated_at: string;
  };
};

export type Alert = {
  id: string;
  station_id: string;
  observation_id: string;
  risk_level: "MEDIUM" | "HIGH" | "CRITICAL";
  water_level_cm: number;
  threshold_cm: number;
  message: string;
  status: "open" | "acknowledged";
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  acknowledgement_notes: string | null;
  created_at: string;
};

export type MQTTStatus = {
  enabled: boolean;
  status: "disabled" | "connecting" | "connected" | "disconnected" | "error";
  topic: string;
  qos: number;
  tls_enabled: boolean;
  messages_received: number;
  readings_created: number;
  duplicate_messages: number;
  invalid_messages: number;
  last_message_at: string | null;
  last_error: string | null;
};

export type ScreeningBand = "LOWER" | "MODERATE" | "HIGH" | "VERY_HIGH";

export type TerrainScreeningFactor = {
  key: "low_elevation" | "waterway_proximity" | "flatness";
  label: string;
  normalized_score: number;
  weight: number;
  contribution: number;
  observed_value: number;
  unit: string;
  interpretation: string;
};

export type TerrainScreeningFeature = {
  type: "Feature";
  id: string;
  geometry: GeoJSONGeometry | null;
  properties: {
    name: string;
    source_key: string | null;
    screening_score: number;
    screening_band: ScreeningBand;
    factors: TerrainScreeningFactor[];
    elevation_mean_m: number;
    elevation_percentile: number;
    distance_to_waterway_m: number;
    local_relief_m: number;
    source_resolution_m: number;
    cell_size_m: number;
    methodology_version: "terrain-screening-v1";
    screening_only: true;
  };
};

export type TerrainScreeningCollection = {
  type: "FeatureCollection";
  features: TerrainScreeningFeature[];
  meta: {
    page: number;
    page_size: number;
    total: number;
    pages: number;
  };
  summary: {
    total_cells: number;
    returned_cells: number;
    mean_score: number;
    band_counts: Record<ScreeningBand, number>;
    generated_at: string;
  };
  methodology: {
    version: "terrain-screening-v1";
    title: string;
    weights: Record<string, number>;
    band_thresholds: Record<string, string>;
    input_data: string[];
    limitations: string[];
  };
};

export type TerrainScreeningIndexItem = {
  id: string;
  screening_score: number;
  screening_band: ScreeningBand;
  low_elevation_score: number;
  waterway_proximity_score: number;
  flatness_score: number;
};

export type TerrainScreeningIndex = {
  items: TerrainScreeningIndexItem[];
  summary: TerrainScreeningCollection["summary"];
  methodology: TerrainScreeningCollection["methodology"];
};

export type LandCoverSummary = {
  status: "available" | "unavailable";
  dataset_id: string;
  source_name: string;
  reference_year: number;
  source_resolution_m: number;
  cells_enriched: number;
  total_pixels: number;
  classes: {
    class_code: number;
    class_name: string;
    color: string;
    pixel_count: number;
    percentage: number;
  }[];
  attribution: string;
  limitations: string[];
};

export type DataLayer = {
  type: "Feature";
  id: string;
  geometry: GeoJSONGeometry | null;
  properties: {
    layer_key: string;
    name: string;
    category: string;
    data_kind: "raster" | "vector" | "timeseries" | "service";
    provider: string;
    source_url: string;
    license_name: string;
    license_url: string | null;
    attribution: string;
    usage_constraints: string | null;
    spatial_resolution_m: number | null;
    temporal_coverage_start: string | null;
    temporal_coverage_end: string | null;
    update_frequency: string | null;
    quality_status: "verified" | "limited" | "unreviewed" | "deprecated";
    quality_notes: string;
    provenance: Record<string, unknown>;
    is_active: boolean;
    created_at: string;
    updated_at: string;
  };
};

export type FloodIntelligenceSummary = {
  susceptibility_available: boolean;
  forecast_available: boolean;
  sar_validation: {
    status: "awaiting_sar_labels" | "complete";
    model_version: string | null;
    gfd_event_count: number;
    sar_event_count: number;
    paired_event_count: number;
    overall_model_vs_sar: Record<string, unknown> | null;
    paired_events?: Array<Record<string, unknown>>;
    message: string | null;
    interpretation: string | null;
  };
  exposure: {
    flagged_cells: number;
    affected_area_km2: number;
    buildings_at_risk: number;
    built_up_area_km2: number;
    high_risk_cells: number;
    risk_basis: string;
  } | null;
  scenario: {
    ml_probability: number;
    sar_detected: boolean;
    scenario:
      | "low_risk"
      | "high_predicted_risk"
      | "observed_flood_alert"
      | "confirmed_high_risk";
    headline: string;
    detail: string;
  } | null;
  early_warning: {
    probability: number;
    level: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
    recommendation: string;
  } | null;
  limitations: string[];
};

export type DashboardData = {
  assets: GeoAsset[];
  terrainCells: GeoAsset[];
  terrainScreening: TerrainScreeningIndex | null;
  dataLayers: DataLayer[];
  health: Health | null;
  rainfallForecast: RainfallForecast | null;
  rainfallHistory: RainfallHistory | null;
  floodExtents: GeoAsset[];
  floodMlPredictions: FloodMlPredictionIndex | null;
  floodEventMlPredictions: FloodEventMlPredictionIndex | null;
  forecastPredictions: ForecastPredictionIndex | null;
  floodIntelligence: FloodIntelligenceSummary | null;
  sensorStations: SensorStation[];
  latestObservations: HydroObservation[];
  recentObservations: HydroObservation[];
  openAlerts: Alert[];
  mqttStatus: MQTTStatus | null;
  liveUpdatesUrl: string;
  spatialApiUrl: string;
  error: string | null;
};

const API_BASE_URL = (
  process.env.API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

const MAUBIN_BOUNDS =
  "min_lon=95.35&min_lat=16.45&max_lon=95.95&max_lat=16.98";

const LIVE_UPDATES_URL =
  process.env.NEXT_PUBLIC_WS_URL ??
  `${API_BASE_URL.replace(/^http/, "ws")}/ws/live`;
const SPATIAL_API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

async function getPage(
  assetType: string,
  page: number,
): Promise<FeatureCollection> {
  const response = await fetch(
    `${API_BASE_URL}/geo-assets/within-bounds?${MAUBIN_BOUNDS}&asset_type=${assetType}&page=${page}&page_size=1000`,
    {
      cache: "no-store",
      signal: AbortSignal.timeout(20_000),
    },
  );
  if (!response.ok) {
    throw new Error(`GeoAsset API returned HTTP ${response.status}`);
  }
  return response.json() as Promise<FeatureCollection>;
}

async function getAll(assetType: string): Promise<GeoAsset[]> {
  const firstPage = await getPage(assetType, 1);
  const remainingPages =
    firstPage.meta.pages > 1
      ? await Promise.all(
          Array.from(
            { length: firstPage.meta.pages - 1 },
            (_, index) => getPage(assetType, index + 2),
          ),
        )
      : [];

  return [
    ...firstPage.features,
    ...remainingPages.flatMap((page) => page.features),
  ];
}

export async function getDashboardData(): Promise<DashboardData> {
  try {
    const [
      healthResponse,
      boundary,
      rivers,
      canals,
      forecastResult,
      rainfallHistoryResult,
      floodMlPredictionsResult,
      floodEventMlPredictionsResult,
      forecastPredictionsResult,
      floodIntelligenceResult,
      stationsResult,
      observationsResult,
      recentObservationsResult,
      alertsResult,
      mqttStatusResult,
      dataLayersResult,
    ] =
      await Promise.all([
        fetch(`${API_BASE_URL.replace(/\/api\/v1$/, "")}/health`, {
          cache: "no-store",
          signal: AbortSignal.timeout(20_000),
        }),
        getAll("township_boundary"),
        getAll("river_segment"),
        getAll("canal_segment"),
        fetch(`${API_BASE_URL}/weather/rainfall-forecast?forecast_days=7`, {
          cache: "no-store",
          signal: AbortSignal.timeout(20_000),
        })
          .then(async (response) =>
            response.ok
              ? ((await response.json()) as RainfallForecast)
              : null,
          )
          .catch(() => null),
        fetch(`${API_BASE_URL}/weather/rainfall-history?limit=366`, {
          cache: "no-store",
          signal: AbortSignal.timeout(20_000),
        })
          .then(async (response) =>
            response.ok ? ((await response.json()) as RainfallHistory) : null,
          )
          .catch(() => null),
        fetch(`${API_BASE_URL}/flood-ml/predictions/index`, {
          cache: "no-store",
          signal: AbortSignal.timeout(30_000),
        })
          .then(async (response) =>
            response.ok
              ? ((await response.json()) as FloodMlPredictionIndex)
              : null,
          )
          .catch(() => null),
        fetch(
          `${API_BASE_URL}/flood-ml/event-predictions/index?threshold_mode=balanced`,
          {
          cache: "no-store",
          signal: AbortSignal.timeout(30_000),
        })
          .then(async (response) =>
            response.ok
              ? ((await response.json()) as FloodEventMlPredictionIndex)
              : null,
          )
          .catch(() => null),
        fetch(`${API_BASE_URL}/flood-forecast/predictions/index`, {
          cache: "no-store",
          signal: AbortSignal.timeout(30_000),
        })
          .then(async (response) =>
            response.ok
              ? ((await response.json()) as ForecastPredictionIndex)
              : null,
          )
          .catch(() => null),
        fetch(`${API_BASE_URL}/flood-intelligence/summary`, {
          cache: "no-store",
          signal: AbortSignal.timeout(30_000),
        })
          .then(async (response) =>
            response.ok
              ? ((await response.json()) as FloodIntelligenceSummary)
              : null,
          )
          .catch(() => null),
        fetch(`${API_BASE_URL}/stations?page=1&page_size=500`, {
          cache: "no-store",
          signal: AbortSignal.timeout(20_000),
        })
          .then(async (response) => {
            if (!response.ok) return [];
            const collection = (await response.json()) as {
              features: SensorStation[];
            };
            return collection.features;
          })
          .catch(() => []),
        fetch(`${API_BASE_URL}/hydro-observations/latest?limit=100`, {
          cache: "no-store",
          signal: AbortSignal.timeout(20_000),
        })
          .then(async (response) => {
            if (!response.ok) return [];
            const collection = (await response.json()) as {
              features: HydroObservation[];
            };
            return collection.features;
          })
          .catch(() => []),
        fetch(`${API_BASE_URL}/hydro-observations?page=1&page_size=500`, {
          cache: "no-store",
          signal: AbortSignal.timeout(20_000),
        })
          .then(async (response) => {
            if (!response.ok) return [];
            const collection = (await response.json()) as {
              features: HydroObservation[];
            };
            return collection.features;
          })
          .catch(() => []),
        fetch(`${API_BASE_URL}/alerts?status=open&page=1&page_size=100`, {
          cache: "no-store",
          signal: AbortSignal.timeout(20_000),
        })
          .then(async (response) => {
            if (!response.ok) return [];
            const collection = (await response.json()) as { items: Alert[] };
            return collection.items;
          })
          .catch(() => []),
        fetch(`${API_BASE_URL}/mqtt/status`, {
          cache: "no-store",
          signal: AbortSignal.timeout(20_000),
        })
          .then(async (response) =>
            response.ok ? ((await response.json()) as MQTTStatus) : null,
          )
          .catch(() => null),
        fetch(`${API_BASE_URL}/data-layers?is_active=true&page=1&page_size=100`, {
          cache: "no-store",
          signal: AbortSignal.timeout(20_000),
        })
          .then(async (response) => {
            if (!response.ok) return [];
            const collection = (await response.json()) as {
              features: DataLayer[];
            };
            return collection.features;
          })
          .catch(() => []),
      ]);

    if (!healthResponse.ok) {
      throw new Error(`Health API returned HTTP ${healthResponse.status}`);
    }

    const health = (await healthResponse.json()) as Health;

    return {
      assets: [...boundary, ...rivers, ...canals],
      terrainCells: [],
      terrainScreening: null,
      dataLayers: dataLayersResult,
      health,
      rainfallForecast: forecastResult,
      rainfallHistory: rainfallHistoryResult,
      floodExtents: [],
      floodMlPredictions: floodMlPredictionsResult,
      floodEventMlPredictions: floodEventMlPredictionsResult,
      forecastPredictions: forecastPredictionsResult,
      floodIntelligence: floodIntelligenceResult,
      sensorStations: stationsResult,
      latestObservations: observationsResult,
      recentObservations: recentObservationsResult,
      openAlerts: alertsResult,
      mqttStatus: mqttStatusResult,
      liveUpdatesUrl: LIVE_UPDATES_URL,
      spatialApiUrl: SPATIAL_API_URL,
      error: null,
    };
  } catch (error) {
    return {
      assets: [],
      terrainCells: [],
      terrainScreening: null,
      dataLayers: [],
      health: null,
      rainfallForecast: null,
      rainfallHistory: null,
      floodExtents: [],
      floodMlPredictions: null,
      floodEventMlPredictions: null,
      forecastPredictions: null,
      floodIntelligence: null,
      sensorStations: [],
      latestObservations: [],
      recentObservations: [],
      openAlerts: [],
      mqttStatus: null,
      liveUpdatesUrl: LIVE_UPDATES_URL,
      spatialApiUrl: SPATIAL_API_URL,
      error:
        error instanceof Error
          ? error.message
          : "The GeoAI backend could not be reached.",
    };
  }
}
