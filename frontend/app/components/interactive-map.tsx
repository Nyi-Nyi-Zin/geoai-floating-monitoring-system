"use client";

import { useEffect, useId, useMemo, useState } from "react";
import { useTranslation } from "@/lib/i18n";
import {
  GeoJSON,
  MapContainer,
  TileLayer,
  useMap,
  useMapEvents,
  ZoomControl,
} from "react-leaflet";
import type {
  Feature,
  FeatureCollection,
  GeoJsonProperties,
  Geometry,
} from "geojson";
import type {
  LatLngBoundsExpression,
  Layer,
  PathOptions,
} from "leaflet";
import "leaflet/dist/leaflet.css";
import type {
  FloodEventMlPredictionItem,
  FloodMlPredictionIndexItem,
  ForecastPredictionItem,
  GeoAsset,
  TerrainScreeningIndexItem,
} from "@/lib/api";
import styles from "./interactive-map.module.css";

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

export type InteractiveMapProps = {
  assets: GeoAsset[];
  terrainCells: GeoAsset[];
  screeningById: Map<string, TerrainScreeningIndexItem>;
  predictionById: Map<
    string,
    FloodMlPredictionIndexItem | FloodEventMlPredictionItem | ForecastPredictionItem
  >;
  layer: MapLayer;
  selectedId: string | null;
  onSelect: (asset: GeoAsset) => void;
  showHindcastOutcomes?: boolean;
};

const MAUBIN_BOUNDS: LatLngBoundsExpression = [
  [16.501, 95.403],
  [16.923, 95.883],
];

const DEFAULT_TILE_URL =
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

function asNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function formatNumber(value: number, digits = 0) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

function terrainColor(percentile: number) {
  if (percentile <= 20) return "#42b8cc";
  if (percentile <= 40) return "#55cbb4";
  if (percentile <= 60) return "#a7c85f";
  if (percentile <= 80) return "#e3b54d";
  return "#dc794d";
}

function screeningColor(score: number) {
  if (score < 25) return "#40b99b";
  if (score < 50) return "#b5c83f";
  if (score < 75) return "#ef982f";
  return "#df453d";
}

function mlProbabilityColor(probability: number) {
  if (probability < 0.25) return "#40b99b";
  if (probability < 0.5) return "#b5c83f";
  if (probability < 0.75) return "#ef982f";
  return "#df453d";
}

function hindcastOutcomeColor(outcome: string | undefined) {
  if (outcome === "tp") return "#2f80ed";
  if (outcome === "fp") return "#d64545";
  if (outcome === "fn") return "#f0a202";
  return "#6f8f86";
}

function validationCompareColor(outcome: string | undefined) {
  if (outcome === "tp") return "#9b59f5";
  if (outcome === "fp") return "#d64545";
  if (outcome === "fn") return "#2f80ed";
  return "#6f8f86";
}

function historicalFloodColor(eventCount: number) {
  if (eventCount <= 2) return "#8be6ff";
  if (eventCount <= 4) return "#4298e8";
  if (eventCount <= 7) return "#6d45c7";
  return "#d72f8a";
}

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

function toFeature(asset: GeoAsset): Feature<Geometry, GeoJsonProperties> {
  return asset as unknown as Feature<Geometry, GeoJsonProperties>;
}

function MapReadout() {
  const map = useMap();
  const center = map.getCenter();
  const [readout, setReadout] = useState({
    latitude: center.lat,
    longitude: center.lng,
    zoom: map.getZoom(),
  });

  useMapEvents({
    mousemove(event) {
      setReadout((current) => ({
        ...current,
        latitude: event.latlng.lat,
        longitude: event.latlng.lng,
      }));
    },
    moveend() {
      const nextCenter = map.getCenter();
      setReadout({
        latitude: nextCenter.lat,
        longitude: nextCenter.lng,
        zoom: map.getZoom(),
      });
    },
    zoomend() {
      const nextCenter = map.getCenter();
      setReadout({
        latitude: nextCenter.lat,
        longitude: nextCenter.lng,
        zoom: map.getZoom(),
      });
    },
  });

  return (
    <div className={styles.readout} aria-live="polite">
      <span>EPSG:3857</span>
      <span>
        {readout.latitude.toFixed(5)}°, {readout.longitude.toFixed(5)}°
      </span>
      <span>Z{readout.zoom}</span>
    </div>
  );
}

function ResetViewControl() {
  const map = useMap();
  const { t } = useTranslation();
  return (
    <button
      type="button"
      className={styles.resetButton}
      onClick={() => map.fitBounds(MAUBIN_BOUNDS, { padding: [18, 18] })}
      title={t("map.resetMaubin")}
      aria-label={t("map.resetMaubin")}
    >
      Maubin
    </button>
  );
}

export default function InteractiveMap({
  assets,
  terrainCells,
  screeningById,
  predictionById,
  layer,
  selectedId,
  onSelect,
  showHindcastOutcomes = false,
}: InteractiveMapProps) {
  const [mounted, setMounted] = useState(false);
  const mapInstanceId = useId();

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

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
  const waterwayFeatures = useMemo(
    () =>
      assets
        .filter((asset) =>
          ["river_segment", "canal_segment"].includes(
            asset.properties.asset_type,
          ),
        )
        .map(toFeature),
    [assets],
  );
  const terrainFeatures = useMemo(
    () => terrainCells.map(toFeature),
    [terrainCells],
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

  const terrainCollection: FeatureCollection = {
    type: "FeatureCollection",
    features: terrainFeatures,
  };
  const waterwayCollection: FeatureCollection = {
    type: "FeatureCollection",
    features: waterwayFeatures,
  };
  const boundaryCollection: FeatureCollection = {
    type: "FeatureCollection",
    features: boundaryFeatures,
  };
  const floodExtentCollection: FeatureCollection = {
    type: "FeatureCollection",
    features: floodExtentFeatures,
  };

  const styleTerrain = (feature?: Feature): PathOptions => {
    const id = String(feature?.id ?? "");
    const asset = assetById.get(id);
    const selected = id === selectedId;
    const prediction = predictionById.get(id);
    const fillColor =
      layer === "validation" &&
      prediction &&
      "outcome" in prediction
        ? validationCompareColor(prediction.outcome)
        : layer === "event_hindcast" &&
          showHindcastOutcomes &&
          prediction &&
          "outcome" in prediction
          ? hindcastOutcomeColor(prediction.outcome)
          : layer === "ml_prediction" ||
              layer === "event_hindcast" ||
              layer === "forecast" ||
              layer === "validation"
            ? mlProbabilityColor(asNumber(prediction?.probability))
          : layer === "screening"
            ? screeningColor(asNumber(screeningById.get(id)?.screening_score))
            : layer === "landcover"
              ? LAND_COVER_COLORS[
                  asNumber(asset?.properties.metadata.land_cover_dominant_code)
                ] ?? "#7e8c88"
              : terrainColor(
                  asNumber(asset?.properties.metadata.elevation_percentile),
                );
    return {
      color: selected ? "#fff5ad" : "#173f3d",
      weight: selected ? 3 : 0.45,
      opacity: selected ? 1 : 0.6,
      fillColor,
      fillOpacity:
        selected
          ? 0.9
          : (layer === "validation" ||
              (layer === "event_hindcast" && showHindcastOutcomes)) &&
              prediction &&
              "outcome" in prediction &&
              prediction.outcome === "tn"
            ? 0.22
            : 0.66,
    };
  };

  const bindTerrainInteraction = (
    feature: Feature,
    leafletLayer: Layer,
  ) => {
    const id = String(feature.id ?? "");
    const asset = assetById.get(id);
    if (!asset) return;
    const screening = screeningById.get(id);
    const prediction = predictionById.get(id);
    const tooltip =
      layer === "ml_prediction" && prediction
        ? `${"risk_band" in prediction ? prediction.risk_band.replaceAll("_", " ") : "ML"} · ${formatNumber(
            prediction.probability * 100,
            1,
          )}% historical susceptibility`
      : layer === "event_hindcast" && prediction
        ? `${formatNumber(prediction.probability * 100, 1)}% historical event hindcast${
            "outcome" in prediction && showHindcastOutcomes
              ? ` · ${String(prediction.outcome).toUpperCase()}`
              : ""
          }`
      : layer === "forecast" && prediction
        ? `${formatNumber(prediction.probability * 100, 1)}% flood forecast · ${'risk_band' in prediction ? prediction.risk_band.replaceAll('_', ' ') : ''}`
      : layer === "screening" && screening
        ? `${screening.screening_band.replaceAll("_", " ")} · ${formatNumber(
            screening.screening_score,
            1,
          )}/100`
        : layer === "landcover"
          ? String(
              asset.properties.metadata.land_cover_dominant_name ??
                "Land cover unavailable",
            )
          : `Mean elevation ${formatNumber(
              asNumber(asset.properties.metadata.elevation_mean_m),
              1,
            )} m`;
    leafletLayer.bindTooltip(tooltip, { sticky: true, direction: "top" });
    leafletLayer.on("click", () => onSelect(asset));
  };

  const styleWaterway = (feature?: Feature): PathOptions => {
    const id = String(feature?.id ?? "");
    const asset = assetById.get(id);
    const selected = id === selectedId;
    const river = asset?.properties.asset_type === "river_segment";
    return {
      color: selected ? "#ff9d2f" : river ? "#00a9e8" : "#62b637",
      weight: selected ? 6 : river ? 3.2 : 2.6,
      opacity: selected ? 1 : 0.9,
    };
  };

  const bindWaterwayInteraction = (
    feature: Feature,
    leafletLayer: Layer,
  ) => {
    const asset = assetById.get(String(feature.id ?? ""));
    if (!asset) return;
    leafletLayer.bindTooltip(asset.properties.name, {
      sticky: true,
      direction: "top",
    });
    leafletLayer.on("click", () => onSelect(asset));
  };

  const styleFloodExtent = (feature?: Feature): PathOptions => {
    const id = String(feature?.id ?? "");
    const asset = assetById.get(id);
    const eventCount = asNumber(asset?.properties.metadata.event_count);
    return {
      color: id === selectedId ? "#fff5ad" : "#484bbf",
      weight: id === selectedId ? 3 : 1.5,
      opacity: 0.95,
      fillColor: historicalFloodColor(eventCount),
      fillOpacity: id === selectedId ? 0.72 : 0.52,
    };
  };

  const bindFloodExtentInteraction = (
    feature: Feature,
    leafletLayer: Layer,
  ) => {
    const asset = assetById.get(String(feature.id ?? ""));
    if (!asset) return;
    leafletLayer.bindTooltip(
      `${asset.properties.name} · ${formatNumber(
        asNumber(asset.properties.metadata.event_count),
      )} observed events`,
      { sticky: true, direction: "top" },
    );
    leafletLayer.on("click", () => onSelect(asset));
  };

  const tileUrl =
    process.env.NEXT_PUBLIC_MAP_TILE_URL?.trim() || DEFAULT_TILE_URL;

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
        minZoom={8}
        maxZoom={18}
        scrollWheelZoom
        touchZoom
        zoomControl={false}
        preferCanvas
        className={styles.map}
      >
        <TileLayer
          url={tileUrl}
          maxNativeZoom={19}
          maxZoom={19}
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />
        {boundaryFeatures.length ? (
          <GeoJSON
            key={`boundary-${boundaryFeatures.length}`}
            data={boundaryCollection}
            style={{
              color: "#12685f",
              weight: 2,
              opacity: 0.85,
              dashArray: "7 6",
              fillOpacity: 0.02,
            }}
          />
        ) : null}
        {layer !== "network" &&
        layer !== "flood_history" &&
        terrainFeatures.length ? (
          <GeoJSON
            key={`terrain-${terrainFeatures.length}-${layer}`}
            data={terrainCollection}
            style={styleTerrain}
            onEachFeature={bindTerrainInteraction}
          />
        ) : null}
        {layer === "flood_history" && floodExtentFeatures.length ? (
          <GeoJSON
            key={`flood-history-${floodExtentFeatures.length}-${selectedId}`}
            data={floodExtentCollection}
            style={styleFloodExtent}
            onEachFeature={bindFloodExtentInteraction}
          />
        ) : null}
        {waterwayFeatures.length ? (
          <GeoJSON
            key={`waterways-${waterwayFeatures.length}`}
            data={waterwayCollection}
            style={styleWaterway}
            onEachFeature={bindWaterwayInteraction}
          />
        ) : null}
        <ZoomControl position="topright" />
        <ResetViewControl />
        <MapReadout />
      </MapContainer>
      <div className={styles.basemapBadge}>
        <i />
        OpenStreetMap basemap
      </div>
      <a
        className={styles.reportLink}
        href="https://www.openstreetmap.org/fixthemap"
        target="_blank"
        rel="noreferrer"
      >
        Report a map issue
      </a>
    </div>
  );
}
