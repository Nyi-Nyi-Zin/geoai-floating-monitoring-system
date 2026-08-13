"use client";

import {
  forwardRef,
  useEffect,
  useId,
  useImperativeHandle,
  useMemo,
  useState,
} from "react";
import {
  GeoJSON,
  MapContainer,
  Marker,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import type {
  Feature,
  FeatureCollection,
  GeoJsonProperties,
  Geometry,
} from "geojson";
import type { LatLngBoundsExpression, Layer, PathOptions } from "leaflet";
import "leaflet/dist/leaflet.css";
import type {
  FloodEventMlPredictionItem,
  FloodMlPredictionIndexItem,
  ForecastPredictionItem,
  GeoAsset,
  HydroObservation,
  SensorStation,
  TerrainScreeningIndexItem,
} from "@/lib/api";
import styles from "./flood-monitoring-map.module.css";

type MapLayer =
  | "terrain"
  | "screening"
  | "landcover"
  | "ml_prediction"
  | "event_hindcast"
  | "forecast"
  | "network"
  | "flood_history"
  | "validation";

import {
  continuousProbabilityColor,
  polygonCentroid,
  type ProbabilitySample,
} from "@/lib/probability-surface";
import type {
  BasemapMode,
  FloodMonitoringMapHandle,
  LayerVisibility,
} from "./flood-monitoring-map.types";
import ProbabilitySurfaceLayer, {
  ProbabilityCellClickHandler,
} from "./probability-surface-layer";

export type { BasemapMode, FloodMonitoringMapHandle, LayerVisibility };

export type FloodMonitoringMapProps = {
  assets: GeoAsset[];
  terrainCells: GeoAsset[];
  screeningById: Map<string, TerrainScreeningIndexItem>;
  predictionById: Map<
    string,
    FloodMlPredictionIndexItem | FloodEventMlPredictionItem | ForecastPredictionItem
  >;
  layer: MapLayer;
  basemapMode?: BasemapMode;
  selectedId: string | null;
  onSelect: (asset: GeoAsset) => void;
  sensorStations?: SensorStation[];
  latestObservations?: HydroObservation[];
  visibility: LayerVisibility;
  onCenterChange?: (latitude: number, longitude: number) => void;
};

const MAUBIN_BOUNDS: LatLngBoundsExpression = [
  [16.501, 95.403],
  [16.923, 95.883],
];

/** Maubin center — used for locate / default pan target */
const MAUBIN_CENTER: [number, number] = [16.7247, 95.6687];

/** No floor — zoom out to full globe like standard web maps */
const MIN_MAP_ZOOM = 0;

const SATELLITE_TILE_URL =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

const TERRAIN_TILE_URL =
  "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png";

const LAND_COVER_COLORS: Record<number, string> = {
  10: "#006400",
  20: "#ffbb22",
  30: "#ffff4c",
  40: "#f096ff",
  50: "#fa0000",
  60: "#b4b4b4",
  70: "#f0f0f0",
  80: "#0064c8",
  90: "#0096a0",
  95: "#00cf75",
  100: "#fae6a0",
};

function asNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function formatNumber(value: number, digits = 1) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

function resolveLandCoverCode(metadata: Record<string, unknown> | undefined) {
  if (!metadata) return null;
  const dominant = metadata.land_cover_dominant_code;
  if (typeof dominant === "number" && Number.isFinite(dominant)) {
    return dominant;
  }
  const percentages = metadata.land_cover_percentages;
  if (!percentages || typeof percentages !== "object") return null;

  let bestCode: number | null = null;
  let bestShare = -1;
  for (const [code, share] of Object.entries(
    percentages as Record<string, unknown>,
  )) {
    const parsedCode = Number(code);
    const parsedShare = typeof share === "number" ? share : Number(share);
    if (!Number.isFinite(parsedCode) || !Number.isFinite(parsedShare)) continue;
    if (parsedShare > bestShare) {
      bestShare = parsedShare;
      bestCode = parsedCode;
    }
  }
  return bestCode;
}

function landCoverColor(metadata: Record<string, unknown> | undefined) {
  const code = resolveLandCoverCode(metadata);
  return code === null ? "#7e8c88" : LAND_COVER_COLORS[code] ?? "#7e8c88";
}

function terrainColor(percentile: number) {
  if (percentile <= 20) return "#42b8cc";
  if (percentile <= 40) return "#55cbb4";
  if (percentile <= 60) return "#a7c85f";
  if (percentile <= 80) return "#e3b54d";
  return "#dc794d";
}

function screeningColor(score: number) {
  if (score < 20) return "#3b82f6";
  if (score < 40) return "#22c55e";
  if (score < 60) return "#eab308";
  if (score < 80) return "#f97316";
  return "#ef4444";
}

function handColor(handM: number) {
  if (handM <= 2) return "#ef4444";
  if (handM <= 5) return "#f97316";
  if (handM <= 10) return "#eab308";
  if (handM <= 20) return "#22c55e";
  return "#3b82f6";
}

function historicalFloodColor(eventCount: number) {
  if (eventCount <= 2) return "#8be6ff";
  if (eventCount <= 4) return "#4298e8";
  if (eventCount <= 7) return "#6d45c7";
  return "#d72f8a";
}

function waterLevelColor(levelM: number) {
  if (levelM < 2) return "#3b82f6";
  if (levelM < 3) return "#eab308";
  if (levelM < 4) return "#f97316";
  return "#ef4444";
}

function toFeature(asset: GeoAsset): Feature<Geometry, GeoJsonProperties> {
  return asset as unknown as Feature<Geometry, GeoJsonProperties>;
}

function flattenCoordinates(value: unknown): [number, number][] {
  if (!Array.isArray(value)) return [];
  if (
    value.length >= 2 &&
    typeof value[0] === "number" &&
    typeof value[1] === "number"
  ) {
    return [[value[0], value[1]]];
  }
  return value.flatMap(flattenCoordinates);
}

function stationPosition(station: SensorStation): [number, number] | null {
  const coords = flattenCoordinates(station.geometry.coordinates);
  if (!coords.length) return null;
  const [lon, lat] = coords[0];
  return [lat, lon];
}

function bindFeatureTooltip(
  leafletLayer: Layer,
  content: string,
  {
    enabled,
    permanent,
  }: {
    enabled: boolean;
    permanent: boolean;
  },
) {
  leafletLayer.unbindTooltip();
  if (!enabled) return;
  leafletLayer.bindTooltip(content, {
    permanent,
    sticky: !permanent,
    direction: "top",
  });
}

function MapController({
  onReady,
  onCenterChange,
}: {
  onReady: (map: L.Map) => void;
  onCenterChange?: (latitude: number, longitude: number) => void;
}) {
  const map = useMap();

  useEffect(() => {
    onReady(map);
    map.invalidateSize();

    const handleResize = () => {
      map.invalidateSize();
    };
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [map, onReady]);

  useMapEvents({
    moveend() {
      const center = map.getCenter();
      onCenterChange?.(center.lat, center.lng);
    },
  });

  return null;
}

function SensorMarkers({
  stations,
  observations,
  showLabels,
}: {
  stations: SensorStation[];
  observations: HydroObservation[];
  showLabels: boolean;
}) {
  const waterByStation = useMemo(() => {
    const latest = new Map<string, number>();
    for (const observation of observations) {
      const level = observation.properties.water_level_m;
      if (level === null) continue;
      const existing = latest.get(observation.properties.station_id);
      if (existing === undefined || level > existing) {
        latest.set(observation.properties.station_id, level);
      }
    }
    return latest;
  }, [observations]);

  return (
    <>
      {stations.map((station) => {
        const position = stationPosition(station);
        if (!position) return null;
        const level =
          waterByStation.get(station.properties.station_id) ??
          asNumber(station.properties.metadata.last_water_level_m);
        const color = waterLevelColor(level || 0);
        const icon = L.divIcon({
          className: "",
          html: `<div class="${styles.sensorMarker}" style="background:${color}">📡</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });
        return (
          <Marker key={station.id} position={position} icon={icon}>
            {showLabels ? (
              <Tooltip permanent direction="top" offset={[0, -16]}>
                <div className={styles.sensorLabel}>
                  WL: {level ? `${formatNumber(level, 2)} m` : "—"}
                </div>
              </Tooltip>
            ) : (
              <Tooltip sticky direction="top">
                {station.properties.name}
                {level ? ` · ${formatNumber(level, 2)} m` : ""}
              </Tooltip>
            )}
          </Marker>
        );
      })}
    </>
  );
}

const FloodMonitoringMap = forwardRef<
  FloodMonitoringMapHandle,
  FloodMonitoringMapProps
>(function FloodMonitoringMap(
  {
    assets,
    terrainCells,
    screeningById,
    predictionById,
    layer,
    basemapMode = "satellite",
    selectedId,
    onSelect,
    sensorStations = [],
    latestObservations = [],
    visibility,
    onCenterChange,
  },
  ref,
) {
  const [mounted, setMounted] = useState(false);
  const [mapInstance, setMapInstance] = useState<L.Map | null>(null);
  const [centerCoords, setCenterCoords] = useState({ lat: 16.7247, lon: 95.6687 });
  const mapInstanceId = useId();

  useEffect(() => {
    setMounted(true);
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      zoomIn: () => mapInstance?.zoomIn(),
      zoomOut: () => mapInstance?.zoomOut(),
      locate: () => {
        mapInstance?.flyTo(MAUBIN_CENTER, 12, { duration: 0.8 });
      },
      resetView: () => {
        mapInstance?.fitBounds(MAUBIN_BOUNDS, { padding: [18, 18] });
      },
    }),
    [mapInstance],
  );

  const assetById = useMemo(
    () =>
      new Map(
        [...assets, ...terrainCells].map((asset) => [asset.id, asset]),
      ),
    [assets, terrainCells],
  );

  const boundaryFeatures = useMemo(
    () =>
      assets
        .filter(
          (asset) => asset.properties.asset_type === "township_boundary",
        )
        .map(toFeature),
    [assets],
  );

  const riverFeatures = useMemo(
    () =>
      assets
        .filter((asset) => asset.properties.asset_type === "river_segment")
        .map(toFeature),
    [assets],
  );

  const canalFeatures = useMemo(
    () =>
      assets
        .filter((asset) => asset.properties.asset_type === "canal_segment")
        .map(toFeature),
    [assets],
  );

  const floodExtentFeatures = useMemo(
    () =>
      assets
        .filter(
          (asset) =>
            asset.properties.asset_type === "historical_flood_extent",
        )
        .map(toFeature),
    [assets],
  );

  const roadFeatures = useMemo(
    () =>
      assets
        .filter((asset) =>
          asset.properties.asset_type === "road_segment" ||
          asset.properties.asset_type.includes("road"),
        )
        .map(toFeature),
    [assets],
  );

  const terrainFeatures = useMemo(
    () => terrainCells.map(toFeature),
    [terrainCells],
  );

  const terrainCollection: FeatureCollection = {
    type: "FeatureCollection",
    features: terrainFeatures,
  };
  const riverCollection: FeatureCollection = {
    type: "FeatureCollection",
    features: riverFeatures,
  };
  const canalCollection: FeatureCollection = {
    type: "FeatureCollection",
    features: canalFeatures,
  };
  const floodExtentCollection: FeatureCollection = {
    type: "FeatureCollection",
    features: floodExtentFeatures,
  };
  const roadCollection: FeatureCollection = {
    type: "FeatureCollection",
    features: roadFeatures,
  };
  const boundaryCollection: FeatureCollection = {
    type: "FeatureCollection",
    features: boundaryFeatures,
  };

  const effectiveLayer: MapLayer =
    basemapMode === "terrain" ? "terrain" : layer;
  const cellOverlayMode: MapLayer | "hand" =
    visibility.buildings
      ? "landcover"
      : visibility.hand
        ? "hand"
        : effectiveLayer;
  const showProbabilitySurface =
    visibility.floodRisk &&
    !visibility.buildings &&
    !visibility.hand &&
    (cellOverlayMode === "ml_prediction" || cellOverlayMode === "forecast") &&
    predictionById.size > 0;
  const showCellOverlay =
    terrainFeatures.length &&
    cellOverlayMode !== "network" &&
    (visibility.gridCells || visibility.buildings || visibility.hand);
  const showTerrainHoverLabelLayer =
    visibility.labels &&
    !showCellOverlay &&
    terrainFeatures.length > 0 &&
    (showProbabilitySurface || visibility.floodRisk);

  const hoverLabelFeatures = useMemo(
    () =>
      showProbabilitySurface
        ? terrainFeatures.filter((feature) =>
            predictionById.has(String(feature.id ?? "")),
          )
        : terrainFeatures,
    [showProbabilitySurface, terrainFeatures, predictionById],
  );
  const hoverLabelCollection: FeatureCollection = {
    type: "FeatureCollection",
    features: hoverLabelFeatures,
  };

  const probabilitySamples = useMemo(() => {
    if (!showProbabilitySurface) return [] as ProbabilitySample[];
    const samples: ProbabilitySample[] = [];
    for (const feature of terrainFeatures) {
      const id = String(feature.id ?? "");
      const prediction = predictionById.get(id);
      if (!prediction) continue;
      const geometry = feature.geometry;
      const coordinates =
        geometry?.type === "Polygon" || geometry?.type === "MultiPolygon"
          ? geometry.coordinates
          : null;
      const centroid = polygonCentroid(coordinates);
      if (!centroid) continue;
      const [lat, lng] = centroid;
      samples.push({
        id,
        lat,
        lng,
        probability: asNumber(prediction.probability),
      });
    }
    return samples;
  }, [
    showProbabilitySurface,
    terrainFeatures,
    predictionById,
  ]);
  const tileUrl =
    basemapMode === "terrain"
      ? process.env.NEXT_PUBLIC_TERRAIN_TILE_URL?.trim() || TERRAIN_TILE_URL
      : process.env.NEXT_PUBLIC_SATELLITE_TILE_URL?.trim() || SATELLITE_TILE_URL;
  const tileAttribution =
    basemapMode === "terrain"
      ? '&copy; <a href="https://opentopomap.org">OpenTopoMap</a>'
      : "Tiles &copy; Esri";

  const styleTerrainCell = (feature?: Feature): PathOptions => {
    const id = String(feature?.id ?? "");
    const asset = assetById.get(id);
    const selected = id === selectedId;
    const prediction = predictionById.get(id);
    const fillColor =
      cellOverlayMode === "hand"
        ? handColor(asNumber(asset?.properties.metadata.hand_mean_m))
        : cellOverlayMode === "ml_prediction" ||
            cellOverlayMode === "event_hindcast" ||
            cellOverlayMode === "forecast" ||
            cellOverlayMode === "validation"
          ? continuousProbabilityColor(asNumber(prediction?.probability))
          : cellOverlayMode === "screening"
            ? screeningColor(asNumber(screeningById.get(id)?.screening_score))
            : cellOverlayMode === "landcover"
              ? landCoverColor(asset?.properties.metadata)
              : terrainColor(
                  asNumber(asset?.properties.metadata.elevation_percentile),
                );
    if (showProbabilitySurface) {
      return {
        color: selected ? "#fff5ad" : "rgba(255,255,255,0.28)",
        weight: selected ? 2 : 0.6,
        opacity: 0.9,
        fillColor,
        fillOpacity: selected ? 0.35 : 0,
      };
    }
    return {
      color: selected ? "#fff5ad" : "transparent",
      weight: selected ? 2 : 0,
      opacity: selected ? 1 : 0,
      fillColor,
      fillOpacity: selected ? 0.82 : basemapMode === "terrain" ? 0.48 : 0.58,
    };
  };

  const terrainTooltip = (
    asset: GeoAsset,
    screening: TerrainScreeningIndexItem | undefined,
    prediction:
      | FloodMlPredictionIndexItem
      | FloodEventMlPredictionItem
      | ForecastPredictionItem
      | undefined,
  ) =>
    cellOverlayMode === "hand"
      ? `HAND ${formatNumber(
          asNumber(asset.properties.metadata.hand_mean_m),
          1,
        )} m`
      : cellOverlayMode === "landcover"
        ? String(
            asset.properties.metadata.land_cover_dominant_name ?? "Land cover",
          )
        : effectiveLayer === "terrain"
          ? `Mean elevation ${formatNumber(
              asNumber(asset.properties.metadata.elevation_mean_m),
              1,
            )} m`
          : (effectiveLayer === "forecast" ||
                effectiveLayer === "ml_prediction") &&
              prediction
            ? `${formatNumber(prediction.probability * 100, 1)}% predicted flood probability`
            : effectiveLayer === "screening" && screening
              ? `${screening.screening_band.replaceAll("_", " ")} · ${formatNumber(
                  screening.screening_score,
                  1,
                )}/100`
              : asset.properties.name;

  const bindTerrainInteraction =
    (permanentLabels: boolean) =>
    (feature: Feature, leafletLayer: Layer) => {
      const id = String(feature.id ?? "");
      const asset = assetById.get(id);
      if (!asset) return;
      bindFeatureTooltip(
        leafletLayer,
        terrainTooltip(
          asset,
          screeningById.get(id),
          predictionById.get(id),
        ),
        { enabled: visibility.labels, permanent: permanentLabels },
      );
      leafletLayer.on("click", () => onSelect(asset));
    };

  const styleProbabilityLabelTarget = (): PathOptions => ({
    color: "transparent",
    weight: 0,
    opacity: 0,
    fillColor: "#000000",
    fillOpacity: 0,
  });

  const styleWaterway = (
    feature?: Feature,
    kind: "river" | "canal" = "river",
  ): PathOptions => {
    const id = String(feature?.id ?? "");
    const selected = id === selectedId;
    return {
      color: selected ? "#ff9d2f" : kind === "river" ? "#00c8ff" : "#62b637",
      weight: selected ? 5 : kind === "river" ? 3 : 2.4,
      opacity: 0.92,
    };
  };

  const bindWaterwayInteraction = (
    feature: Feature,
    leafletLayer: Layer,
  ) => {
    const asset = assetById.get(String(feature.id ?? ""));
    if (!asset) return;
    bindFeatureTooltip(leafletLayer, asset.properties.name, {
      enabled: visibility.labels,
      permanent: true,
    });
    leafletLayer.on("click", () => onSelect(asset));
  };

  const styleFloodExtent = (feature?: Feature): PathOptions => {
    const id = String(feature?.id ?? "");
    const asset = assetById.get(id);
    const selected = id === selectedId;
    return {
      color: selected ? "#fff5ad" : "#484bbf",
      weight: selected ? 3 : 2,
      opacity: 0.92,
      fillColor: historicalFloodColor(
        asNumber(asset?.properties.metadata.event_count),
      ),
      fillOpacity: selected ? 0.72 : 0.52,
    };
  };

  const bindFloodExtentInteraction = (
    feature: Feature,
    leafletLayer: Layer,
  ) => {
    const asset = assetById.get(String(feature.id ?? ""));
    if (!asset) return;
    const eventCount = asNumber(asset.properties.metadata.event_count);
    bindFeatureTooltip(
      leafletLayer,
      `${asset.properties.name} · ${formatNumber(eventCount, 0)} events`,
      { enabled: visibility.labels, permanent: true },
    );
    leafletLayer.on("click", () => onSelect(asset));
  };

  if (!mounted) {
    return (
      <div className={styles.mapShell}>
        <div className={styles.map} aria-hidden />
      </div>
    );
  }

  return (
    <div className={styles.mapShell}>
      <MapContainer
        key={mapInstanceId}
        bounds={MAUBIN_BOUNDS}
        boundsOptions={{ padding: [18, 18] }}
        minZoom={MIN_MAP_ZOOM}
        maxZoom={18}
        worldCopyJump
        scrollWheelZoom
        touchZoom
        zoomControl={false}
        preferCanvas
        className={styles.map}
      >
        <TileLayer
          url={tileUrl}
          maxNativeZoom={basemapMode === "terrain" ? 17 : 19}
          maxZoom={19}
          attribution={tileAttribution}
        />
        <MapController
          onReady={setMapInstance}
          onCenterChange={(latitude, longitude) => {
            setCenterCoords({ lat: latitude, lon: longitude });
            onCenterChange?.(latitude, longitude);
          }}
        />
        {visibility.boundary && boundaryFeatures.length ? (
          <GeoJSON
            key={`boundary-${boundaryFeatures.length}`}
            data={boundaryCollection}
            style={{
              color: "#ffffff",
              weight: 1.5,
              opacity: 0.55,
              dashArray: "6 5",
              fillOpacity: 0,
            }}
          />
        ) : null}
        {showProbabilitySurface ? (
          <>
            <ProbabilitySurfaceLayer
              samples={probabilitySamples}
              opacity={basemapMode === "terrain" ? 0.68 : 0.74}
            />
            <ProbabilityCellClickHandler
              samples={probabilitySamples}
              assetById={assetById}
              onSelect={onSelect}
            />
          </>
        ) : null}
        {showTerrainHoverLabelLayer ? (
          <GeoJSON
            key={`terrain-hover-labels-${hoverLabelFeatures.length}-${cellOverlayMode}-labels-${visibility.labels}`}
            data={hoverLabelCollection}
            style={styleProbabilityLabelTarget}
            onEachFeature={bindTerrainInteraction(false)}
          />
        ) : null}
        {showCellOverlay ? (
          <GeoJSON
            key={`terrain-${terrainFeatures.length}-${cellOverlayMode}-${basemapMode}-labels-${visibility.labels}`}
            data={terrainCollection}
            style={styleTerrainCell}
            onEachFeature={bindTerrainInteraction(visibility.labels)}
          />
        ) : null}
        {visibility.historicalFlood && floodExtentFeatures.length ? (
          <GeoJSON
            key={`flood-history-${floodExtentFeatures.length}-labels-${visibility.labels}`}
            data={floodExtentCollection}
            style={styleFloodExtent}
            onEachFeature={bindFloodExtentInteraction}
          />
        ) : null}
        {visibility.rivers && riverFeatures.length ? (
          <GeoJSON
            key={`rivers-${riverFeatures.length}-labels-${visibility.labels}`}
            data={riverCollection}
            style={(feature) => styleWaterway(feature, "river")}
            onEachFeature={bindWaterwayInteraction}
          />
        ) : null}
        {visibility.canals && canalFeatures.length ? (
          <GeoJSON
            key={`canals-${canalFeatures.length}-labels-${visibility.labels}`}
            data={canalCollection}
            style={(feature) => styleWaterway(feature, "canal")}
            onEachFeature={bindWaterwayInteraction}
          />
        ) : null}
        {visibility.roads && roadFeatures.length ? (
          <GeoJSON
            key={`roads-${roadFeatures.length}-labels-${visibility.labels}`}
            data={roadCollection}
            style={{
              color: "#d1d5db",
              weight: 2,
              opacity: 0.85,
            }}
            onEachFeature={bindWaterwayInteraction}
          />
        ) : null}
        {visibility.sensors ? (
          <SensorMarkers
            key={`sensors-labels-${visibility.labels}`}
            stations={sensorStations}
            observations={latestObservations}
            showLabels={visibility.labels}
          />
        ) : null}
      </MapContainer>
      <div className={styles.compass}>
        <span className={styles.compassIcon}>N</span>
        <span>
          {centerCoords.lat.toFixed(2)}° N, {centerCoords.lon.toFixed(2)}° E
        </span>
      </div>
      <div className={styles.scaleBar}>
        <div className={styles.scaleBarLine} />
        <span>0</span>
        <span>1</span>
        <span>2 km</span>
      </div>
    </div>
  );
});

export default FloodMonitoringMap;
