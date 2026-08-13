"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl, {
  type GeoJSONSource,
  type Map as MapLibreMap,
  type MapMouseEvent,
  type MapGeoJSONFeature,
  type StyleSpecification,
} from "maplibre-gl";
import type {
  Feature,
  FeatureCollection,
  GeoJsonProperties,
  Geometry,
} from "geojson";
import "maplibre-gl/dist/maplibre-gl.css";
import type {
  FloodEventMlPredictionItem,
  FloodMlPredictionIndexItem,
  ForecastPredictionItem,
  GeoAsset,
  TerrainScreeningIndexItem,
} from "@/lib/api";
import styles from "./interactive-map-3d.module.css";

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

export type InteractiveMap3DProps = {
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

type Readout = {
  latitude: number;
  longitude: number;
  zoom: number;
  pitch: number;
};

const MAUBIN_CENTER: [number, number] = [95.6687, 16.7247];
const MAUBIN_BOUNDS: [[number, number], [number, number]] = [
  [95.403, 16.501],
  [95.883, 16.923],
];
const EMPTY_COLLECTION: FeatureCollection = {
  type: "FeatureCollection",
  features: [],
};
const DEFAULT_TILE_URL =
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const DEFAULT_TERRAIN_URL =
  "https://tiles.mapterhorn.com/tilejson.json";

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

function toFeature(
  asset: GeoAsset,
  properties: GeoJsonProperties,
): Feature<Geometry, GeoJsonProperties> {
  return {
    type: "Feature",
    id: asset.id,
    geometry: asset.geometry as Geometry,
    properties: {
      ...properties,
      asset_id: asset.id,
      asset_name: asset.properties.name,
      asset_type: asset.properties.asset_type,
    },
  };
}

function makeStyle(
  tileUrl: string,
  terrainUrl: string,
): StyleSpecification {
  return {
    version: 8,
    sources: {
      osm: {
        type: "raster",
        tiles: [tileUrl],
        tileSize: 256,
        attribution:
          '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      },
      terrain: {
        type: "raster-dem",
        url: terrainUrl,
        tileSize: 512,
        encoding: "terrarium",
        attribution:
          '© <a href="https://mapterhorn.com/attribution">Mapterhorn</a>',
      },
      terrainCells: {
        type: "geojson",
        data: EMPTY_COLLECTION,
      },
      waterways: {
        type: "geojson",
        data: EMPTY_COLLECTION,
      },
      floodExtents: {
        type: "geojson",
        data: EMPTY_COLLECTION,
      },
      boundary: {
        type: "geojson",
        data: EMPTY_COLLECTION,
      },
    },
    terrain: {
      source: "terrain",
      exaggeration: 5,
    },
    layers: [
      {
        id: "osm-basemap",
        type: "raster",
        source: "osm",
        paint: {
          "raster-saturation": -0.2,
          "raster-contrast": 0.04,
          "raster-brightness-max": 0.97,
        },
      },
      {
        id: "terrain-hillshade",
        type: "hillshade",
        source: "terrain",
        paint: {
          "hillshade-exaggeration": 0.45,
          "hillshade-shadow-color": "#123d3a",
          "hillshade-highlight-color": "#efffd8",
          "hillshade-accent-color": "#406f68",
        },
      },
      {
        id: "terrain-cells",
        type: "fill",
        source: "terrainCells",
        paint: {
          "fill-color": ["get", "fill_color"],
          "fill-opacity": [
            "case",
            ["boolean", ["get", "selected"], false],
            0.82,
            0.52,
          ],
          "fill-outline-color": [
            "case",
            ["boolean", ["get", "selected"], false],
            "#fff5ad",
            "#173f3d",
          ],
        },
      },
      {
        id: "selected-cell-outline",
        type: "line",
        source: "terrainCells",
        filter: ["==", ["get", "selected"], true],
        paint: {
          "line-color": "#fff5ad",
          "line-width": 4,
          "line-opacity": 1,
        },
      },
      {
        id: "historical-flood-extents",
        type: "fill",
        source: "floodExtents",
        paint: {
          "fill-color": ["get", "fill_color"],
          "fill-opacity": [
            "case",
            ["boolean", ["get", "selected"], false],
            0.72,
            0.5,
          ],
          "fill-outline-color": [
            "case",
            ["boolean", ["get", "selected"], false],
            "#fff5ad",
            "#484bbf",
          ],
        },
      },
      {
        id: "township-boundary",
        type: "line",
        source: "boundary",
        paint: {
          "line-color": "#103f3b",
          "line-width": 3,
          "line-dasharray": [2, 1.5],
          "line-opacity": 0.95,
        },
      },
      {
        id: "waterways",
        type: "line",
        source: "waterways",
        paint: {
          "line-color": ["get", "line_color"],
          "line-width": [
            "case",
            ["boolean", ["get", "selected"], false],
            6,
            ["get", "line_width"],
          ],
          "line-opacity": 0.96,
        },
      },
    ],
  };
}

export default function InteractiveMap3D({
  assets,
  terrainCells,
  screeningById,
  predictionById,
  layer,
  selectedId,
  onSelect,
  showHindcastOutcomes = false,
}: InteractiveMap3DProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const assetByIdRef = useRef(new Map<string, GeoAsset>());
  const onSelectRef = useRef(onSelect);
  const [ready, setReady] = useState(false);
  const [terrainError, setTerrainError] = useState<string | null>(null);
  const [exaggeration, setExaggeration] = useState(5);
  const [readout, setReadout] = useState<Readout>({
    latitude: MAUBIN_CENTER[1],
    longitude: MAUBIN_CENTER[0],
    zoom: 9.2,
    pitch: 62,
  });

  const tileUrl =
    process.env.NEXT_PUBLIC_MAP_TILE_URL?.trim() || DEFAULT_TILE_URL;
  const terrainUrl =
    process.env.NEXT_PUBLIC_TERRAIN_TILEJSON_URL?.trim() ||
    DEFAULT_TERRAIN_URL;

  const assetById = useMemo(
    () =>
      new Map(
        [...assets, ...terrainCells].map((asset) => [asset.id, asset]),
      ),
    [assets, terrainCells],
  );

  useEffect(() => {
    assetByIdRef.current = assetById;
  }, [assetById]);

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  const terrainCollection = useMemo<FeatureCollection>(() => {
    if (layer === "network" || layer === "flood_history") {
      return EMPTY_COLLECTION;
    }
    return {
      type: "FeatureCollection",
      features: terrainCells.map((asset) => {
        const screening = screeningById.get(asset.id);
        const prediction = predictionById.get(asset.id);
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
            ? screeningColor(asNumber(screening?.screening_score))
            : layer === "landcover"
              ? LAND_COVER_COLORS[
                  asNumber(
                    asset.properties.metadata.land_cover_dominant_code,
                  )
                ] ?? "#7e8c88"
              : terrainColor(
                  asNumber(
                    asset.properties.metadata.elevation_percentile,
                  ),
                );
        return toFeature(asset, {
          fill_color: fillColor,
          selected: asset.id === selectedId,
          tooltip:
            layer === "ml_prediction" && prediction
              ? `${"risk_band" in prediction ? prediction.risk_band.replaceAll("_", " ") : "ML"} · ${(prediction.probability * 100).toFixed(1)}% historical susceptibility`
            : layer === "event_hindcast" && prediction
              ? `${(prediction.probability * 100).toFixed(1)}% historical event hindcast${
                  "outcome" in prediction && showHindcastOutcomes
                    ? ` · ${String(prediction.outcome).toUpperCase()}`
                    : ""
                }`
            : layer === "screening" && screening
              ? `${screening.screening_band.replaceAll("_", " ")} · ${screening.screening_score.toFixed(1)}/100`
              : layer === "landcover"
                ? String(
                    asset.properties.metadata
                      .land_cover_dominant_name ?? "Land cover unavailable",
                  )
                : `Mean elevation ${asNumber(
                    asset.properties.metadata.elevation_mean_m,
                  ).toFixed(1)} m`,
        });
      }),
    };
  }, [
    layer,
    predictionById,
    screeningById,
    selectedId,
    showHindcastOutcomes,
    terrainCells,
  ]);

  const waterwayCollection = useMemo<FeatureCollection>(
    () => ({
      type: "FeatureCollection",
      features: assets
        .filter((asset) =>
          ["river_segment", "canal_segment"].includes(
            asset.properties.asset_type,
          ),
        )
        .map((asset) =>
          toFeature(asset, {
            selected: asset.id === selectedId,
            line_color:
              asset.properties.asset_type === "river_segment"
                ? "#00bfe9"
                : "#8cdb38",
            line_width:
              asset.properties.asset_type === "river_segment" ? 3.2 : 2.6,
            tooltip: asset.properties.name,
          }),
        ),
    }),
    [assets, selectedId],
  );

  const boundaryCollection = useMemo<FeatureCollection>(
    () => ({
      type: "FeatureCollection",
      features: assets
        .filter(
          (asset) =>
            asset.properties.asset_type === "township_boundary",
        )
        .map((asset) => toFeature(asset, {})),
    }),
    [assets],
  );

  const floodExtentCollection = useMemo<FeatureCollection>(
    () => ({
      type: "FeatureCollection",
      features:
        layer === "flood_history"
          ? assets
              .filter(
                (asset) =>
                  asset.properties.asset_type === "historical_flood_extent",
              )
              .map((asset) =>
                toFeature(asset, {
                  selected: asset.id === selectedId,
                  fill_color: historicalFloodColor(
                    asNumber(asset.properties.metadata.event_count),
                  ),
                  event_count: asNumber(
                    asset.properties.metadata.event_count,
                  ),
                  tooltip: `${asset.properties.name} · ${asNumber(
                    asset.properties.metadata.event_count,
                  )} observed events`,
                }),
              )
          : [],
    }),
    [assets, layer, selectedId],
  );

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: makeStyle(tileUrl, terrainUrl),
      center: MAUBIN_CENTER,
      zoom: 9.2,
      pitch: 62,
      bearing: -24,
      maxPitch: 82,
      minZoom: 7,
      maxZoom: 18,
      canvasContextAttributes: { antialias: true },
      attributionControl: false,
    });
    mapRef.current = map;
    map.addControl(
      new maplibregl.NavigationControl({
        visualizePitch: true,
        showCompass: true,
        showZoom: true,
      }),
      "top-right",
    );
    map.addControl(new maplibregl.FullscreenControl(), "top-right");
    map.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      "bottom-right",
    );

    const updateReadout = () => {
      const center = map.getCenter();
      setReadout({
        latitude: center.lat,
        longitude: center.lng,
        zoom: map.getZoom(),
        pitch: map.getPitch(),
      });
    };
    const updatePointer = (event: MapMouseEvent) => {
      setReadout((current) => ({
        ...current,
        latitude: event.lngLat.lat,
        longitude: event.lngLat.lng,
      }));
    };
    const selectFeature = (
      event: MapMouseEvent & {
        features?: MapGeoJSONFeature[];
      },
    ) => {
      const assetId = String(
        event.features?.[0]?.properties?.asset_id ?? "",
      );
      const asset = assetByIdRef.current.get(assetId);
      if (asset) onSelectRef.current(asset);
    };
    const showPointer = () => {
      map.getCanvas().style.cursor = "pointer";
    };
    const clearPointer = () => {
      map.getCanvas().style.cursor = "";
    };

    map.on("load", () => {
      setReady(true);
      setTerrainError(null);
    });
    map.on("moveend", updateReadout);
    map.on("mousemove", updatePointer);
    map.on("click", "terrain-cells", selectFeature);
    map.on("click", "historical-flood-extents", selectFeature);
    map.on("click", "waterways", selectFeature);
    map.on("mouseenter", "terrain-cells", showPointer);
    map.on("mouseenter", "historical-flood-extents", showPointer);
    map.on("mouseenter", "waterways", showPointer);
    map.on("mouseleave", "terrain-cells", clearPointer);
    map.on("mouseleave", "historical-flood-extents", clearPointer);
    map.on("mouseleave", "waterways", clearPointer);
    map.on("error", (event) => {
      const message = event.error?.message ?? "";
      if (
        message.includes("terrain") ||
        message.includes("mapterhorn")
      ) {
        setTerrainError("3D terrain tiles are temporarily unavailable.");
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [terrainUrl, tileUrl]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    (
      map.getSource("terrainCells") as GeoJSONSource | undefined
    )?.setData(terrainCollection);
    (
      map.getSource("waterways") as GeoJSONSource | undefined
    )?.setData(waterwayCollection);
    (
      map.getSource("boundary") as GeoJSONSource | undefined
    )?.setData(boundaryCollection);
    (
      map.getSource("floodExtents") as GeoJSONSource | undefined
    )?.setData(floodExtentCollection);
  }, [
    boundaryCollection,
    floodExtentCollection,
    ready,
    terrainCollection,
    waterwayCollection,
  ]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    map.setTerrain({
      source: "terrain",
      exaggeration,
    });
  }, [exaggeration, ready]);

  const resetView = () => {
    mapRef.current?.fitBounds(MAUBIN_BOUNDS, {
      padding: 42,
      pitch: 62,
      bearing: -24,
      duration: 900,
    });
  };

  return (
    <div className={styles.mapShell}>
      <div ref={containerRef} className={styles.map} />
      {!ready ? (
        <div className={styles.loading}>
          <i />
          <span>Building 3D terrain scene…</span>
        </div>
      ) : null}
      {terrainError ? (
        <div className={styles.error}>{terrainError}</div>
      ) : null}
      <div className={styles.modeBadge}>
        <i />
        3D terrain
      </div>
      <button
        type="button"
        className={styles.resetButton}
        onClick={resetView}
      >
        Maubin
      </button>
      <label className={styles.exaggeration}>
        <span>
          Vertical scale
          <strong>{exaggeration.toFixed(1)}×</strong>
        </span>
        <input
          type="range"
          min="1"
          max="8"
          step="0.5"
          value={exaggeration}
          onChange={(event) =>
            setExaggeration(Number(event.target.value))
          }
        />
        <small>Visual exaggeration only</small>
      </label>
      <div className={styles.readout} aria-live="polite">
        <span>EPSG:3857</span>
        <span>
          {readout.latitude.toFixed(5)}°,{" "}
          {readout.longitude.toFixed(5)}°
        </span>
        <span>Z{readout.zoom.toFixed(1)}</span>
        <span>{readout.pitch.toFixed(0)}° pitch</span>
      </div>
      <div className={styles.gestureHint}>
        Drag to pan · right-drag to rotate · scroll to zoom
      </div>
    </div>
  );
}
