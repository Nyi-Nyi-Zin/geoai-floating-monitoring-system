"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type {
  DataSource,
  ImageryProvider,
  ScreenSpaceEventHandler as CesiumScreenSpaceEventHandler,
  Viewer,
} from "cesium";
import type {
  Feature,
  FeatureCollection,
  GeoJsonProperties,
  Geometry,
} from "geojson";
import "cesium/Build/Cesium/Widgets/widgets.css";
import type {
  FloodEventMlPredictionItem,
  FloodMlPredictionIndexItem,
  ForecastPredictionItem,
  GeoAsset,
  SensorStation,
  TerrainScreeningIndexItem,
} from "@/lib/api";
import { continuousProbabilityColor } from "@/lib/probability-surface";
import styles from "./interactive-map-cesium.module.css";

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
type ImageryMode = "satellite" | "streets";

export type InteractiveMapCesiumProps = {
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
  sensorStations?: SensorStation[];
  chromeless?: boolean;
};

type CesiumModule = typeof import("cesium");

type Readout = {
  latitude: number;
  longitude: number;
  heightKm: number;
  heading: number;
  pitch: number;
};

type LayerSources = {
  terrain?: DataSource;
  waterways?: DataSource;
  boundary?: DataSource;
  floodExtents?: DataSource;
  sensors?: DataSource;
};

let cesiumRuntimePromise: Promise<CesiumModule> | null = null;

function loadCesiumRuntime(): Promise<CesiumModule> {
  if (window.Cesium) return Promise.resolve(window.Cesium);
  if (cesiumRuntimePromise) return cesiumRuntimePromise;
  cesiumRuntimePromise = new Promise<CesiumModule>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      'script[data-cesium-runtime="true"]',
    );
    const script = existing ?? document.createElement("script");
    const handleLoad = () => {
      if (window.Cesium) resolve(window.Cesium);
      else reject(new Error("Cesium runtime loaded without a global API."));
    };
    const handleError = () =>
      reject(new Error("Cesium runtime script could not be loaded."));
    script.addEventListener("load", handleLoad, { once: true });
    script.addEventListener("error", handleError, { once: true });
    if (!existing) {
      script.src = "/cesium/Cesium.js";
      script.async = true;
      script.dataset.cesiumRuntime = "true";
      document.head.appendChild(script);
    }
  }).catch((error: unknown) => {
    cesiumRuntimePromise = null;
    throw error;
  });
  return cesiumRuntimePromise;
}

const MAUBIN_CENTER: [number, number] = [95.6687, 16.7247];
const DEFAULT_TILE_URL =
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const DEFAULT_ARCGIS_TERRAIN_URL =
  "https://elevation3d.arcgis.com/arcgis/rest/services/WorldElevation3D/Terrain3D/ImageServer";
const DEFAULT_ARCGIS_SATELLITE_URL =
  "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer";

async function createImageryProvider(
  Cesium: CesiumModule,
  mode: ImageryMode,
  satelliteUrl: string,
  streetTileUrl: string,
): Promise<ImageryProvider> {
  if (mode === "satellite") {
    return Cesium.ArcGisMapServerImageryProvider.fromUrl(satelliteUrl);
  }

  return new Cesium.UrlTemplateImageryProvider({
    url: streetTileUrl,
    credit: new Cesium.Credit(
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    ),
    maximumLevel: 19,
    enablePickFeatures: false,
  });
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

function asBoundaryOutline(feature: Feature<Geometry, GeoJsonProperties>) {
  if (feature.geometry.type === "Polygon") {
    return {
      ...feature,
      geometry: {
        type: "MultiLineString" as const,
        coordinates: feature.geometry.coordinates,
      },
    };
  }
  if (feature.geometry.type === "MultiPolygon") {
    return {
      ...feature,
      geometry: {
        type: "MultiLineString" as const,
        coordinates: feature.geometry.coordinates.flat(),
      },
    };
  }
  return feature;
}

function removeSources(viewer: Viewer, sources: LayerSources) {
  for (const source of Object.values(sources)) {
    if (source) viewer.dataSources.remove(source, true);
  }
}

export default function InteractiveMapCesium({
  assets,
  terrainCells,
  screeningById,
  predictionById,
  layer,
  selectedId,
  onSelect,
  showHindcastOutcomes = false,
  sensorStations = [],
  chromeless = false,
}: InteractiveMapCesiumProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<Viewer | null>(null);
  const cesiumRef = useRef<CesiumModule | null>(null);
  const sourcesRef = useRef<LayerSources>({});
  const selectedSourceRef = useRef<DataSource | null>(null);
  const initializedImageryModeRef = useRef<ImageryMode | null>(null);
  const assetByIdRef = useRef(new Map<string, GeoAsset>());
  const onSelectRef = useRef(onSelect);
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [terrainStatus, setTerrainStatus] = useState("Connecting terrain…");
  const [imageryMode, setImageryMode] =
    useState<ImageryMode>("satellite");
  const [imageryStatus, setImageryStatus] = useState(
    "Connecting satellite imagery…",
  );
  const [exaggeration, setExaggeration] = useState(3);
  const [readout, setReadout] = useState<Readout>({
    latitude: MAUBIN_CENTER[1],
    longitude: MAUBIN_CENTER[0],
    heightKm: 65,
    heading: 336,
    pitch: -52,
  });

  const tileUrl =
    process.env.NEXT_PUBLIC_MAP_TILE_URL?.trim() || DEFAULT_TILE_URL;
  const ionToken = process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN?.trim() || "";
  const terrainUrl =
    process.env.NEXT_PUBLIC_CESIUM_TERRAIN_URL?.trim() ||
    DEFAULT_ARCGIS_TERRAIN_URL;
  const satelliteUrl =
    process.env.NEXT_PUBLIC_CESIUM_SATELLITE_URL?.trim() ||
    DEFAULT_ARCGIS_SATELLITE_URL;

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
      return { type: "FeatureCollection", features: [] };
    }
    return {
      type: "FeatureCollection",
      features: terrainCells.map((asset) => {
        const screening = screeningById.get(asset.id);
        const prediction = predictionById.get(asset.id);
        const fill =
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
                ? continuousProbabilityColor(asNumber(prediction?.probability))
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
        const isProbabilityLayer =
          layer === "ml_prediction" ||
          layer === "forecast" ||
          layer === "event_hindcast" ||
          layer === "validation";
        return toFeature(asset, {
          fill,
          "fill-opacity":
            (layer === "validation" ||
              (layer === "event_hindcast" && showHindcastOutcomes)) &&
            prediction &&
            "outcome" in prediction &&
            prediction.outcome === "tn"
              ? 0.2
              : isProbabilityLayer
                ? 0.72
                : 0.55,
          stroke: isProbabilityLayer ? "#00000000" : "#173f3d",
          "stroke-width": isProbabilityLayer ? 0 : 1,
        });
      }),
    };
  }, [layer, predictionById, screeningById, showHindcastOutcomes, terrainCells]);

  const waterwayCollection = useMemo<FeatureCollection>(
    () => ({
      type: "FeatureCollection",
      features: assets
        .filter((asset) =>
          ["river_segment", "canal_segment"].includes(
            asset.properties.asset_type,
          ),
        )
        .map((asset) => {
          return toFeature(asset, {
            stroke:
              asset.properties.asset_type === "river_segment"
                ? "#00bfe9"
                : "#8cdb38",
            "stroke-width": asset.properties.asset_type === "river_segment"
                ? 4
                : 3,
          });
        }),
    }),
    [assets],
  );

  const boundaryCollection = useMemo<FeatureCollection>(
    () => ({
      type: "FeatureCollection",
      features: assets
        .filter(
          (asset) =>
            asset.properties.asset_type === "township_boundary",
        )
        .map((asset) =>
          asBoundaryOutline(
            toFeature(asset, {
              stroke: "#caff5b",
              "stroke-width": 3,
            }),
          ),
        ),
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
              .map((asset) => {
                return toFeature(asset, {
                  fill: historicalFloodColor(
                    asNumber(asset.properties.metadata.event_count),
                  ),
                  "fill-opacity": 0.52,
                  stroke: "#484bbf",
                  "stroke-width": 2,
                  event_count: asNumber(
                    asset.properties.metadata.event_count,
                  ),
                });
              })
          : [],
    }),
    [assets, layer],
  );

  const sensorCollection = useMemo<FeatureCollection>(() => {
    const features: Feature<Geometry, GeoJsonProperties>[] = sensorStations
      .filter((station) => station.geometry?.type === "Point")
      .map((station) => ({
        type: "Feature" as const,
        id: station.id,
        geometry: station.geometry as Geometry,
        properties: {
          marker: true,
          station_id: station.properties.station_id,
          status: station.properties.status,
          asset_name: station.properties.name,
        },
      }));
    return { type: "FeatureCollection", features };
  }, [sensorStations]);

  useEffect(() => {
    if (!containerRef.current || viewerRef.current) return;
    let disposed = false;
    let inputHandler: CesiumScreenSpaceEventHandler | null = null;

    const initialize = async () => {
      window.CESIUM_BASE_URL = "/cesium/";
      const Cesium = await loadCesiumRuntime();
      if (disposed || !containerRef.current) return;
      cesiumRef.current = Cesium;

      let terrainProvider;
      let resolvedTerrainStatus: string;
      try {
        if (ionToken) {
          Cesium.Ion.defaultAccessToken = ionToken;
          terrainProvider = await Cesium.createWorldTerrainAsync({
            requestVertexNormals: true,
            requestWaterMask: true,
          });
          resolvedTerrainStatus = "Cesium World Terrain";
        } else {
          terrainProvider =
            await Cesium.ArcGISTiledElevationTerrainProvider.fromUrl(
              terrainUrl,
            );
          resolvedTerrainStatus = "ArcGIS World Elevation terrain";
        }
      } catch {
        terrainProvider = new Cesium.EllipsoidTerrainProvider();
        resolvedTerrainStatus = "Ellipsoid fallback · add an ion token";
      }
      if (disposed || !containerRef.current) return;

      let imageryProvider: ImageryProvider;
      let resolvedImageryMode: ImageryMode = "satellite";
      try {
        imageryProvider = await createImageryProvider(
          Cesium,
          "satellite",
          satelliteUrl,
          tileUrl,
        );
        setImageryStatus("Esri World Imagery satellite");
      } catch {
        imageryProvider = await createImageryProvider(
          Cesium,
          "streets",
          satelliteUrl,
          tileUrl,
        );
        resolvedImageryMode = "streets";
        setImageryMode("streets");
        setImageryStatus("Satellite unavailable · Streets fallback");
      }
      if (disposed || !containerRef.current) return;

      const viewer = new Cesium.Viewer(containerRef.current, {
        animation: false,
        timeline: false,
        baseLayerPicker: false,
        geocoder: false,
        homeButton: false,
        sceneModePicker: false,
        navigationHelpButton: false,
        fullscreenButton: true,
        selectionIndicator: false,
        infoBox: false,
        baseLayer: new Cesium.ImageryLayer(imageryProvider),
        terrainProvider,
        scene3DOnly: true,
        requestRenderMode: true,
        maximumRenderTimeChange: Number.POSITIVE_INFINITY,
      });
      viewerRef.current = viewer;
      initializedImageryModeRef.current = resolvedImageryMode;
      viewer.scene.globe.depthTestAgainstTerrain = true;
      // Lighting and fog cause an extra terrain shading pass while the user
      // navigates. The coloured analytical overlays remain readable without it.
      viewer.scene.globe.enableLighting = false;
      viewer.scene.fog.enabled = false;
      viewer.scene.verticalExaggeration = 3;
      viewer.scene.verticalExaggerationRelativeHeight = 0;
      viewer.scene.screenSpaceCameraController.minimumZoomDistance = 30;
      viewer.scene.screenSpaceCameraController.maximumZoomDistance = 2_000_000;

      const updateReadout = () => {
        const position = viewer.camera.positionCartographic;
        setReadout({
          latitude: Cesium.Math.toDegrees(position.latitude),
          longitude: Cesium.Math.toDegrees(position.longitude),
          heightKm: position.height / 1000,
          heading: Cesium.Math.toDegrees(viewer.camera.heading),
          pitch: Cesium.Math.toDegrees(viewer.camera.pitch),
        });
      };

      viewer.camera.moveEnd.addEventListener(updateReadout);
      inputHandler = new Cesium.ScreenSpaceEventHandler(
        viewer.scene.canvas,
      );
      inputHandler.setInputAction(
        (movement: CesiumScreenSpaceEventHandler.PositionedEvent) => {
          const picked = viewer.scene.pick(movement.position) as
            | { id?: { id?: string } }
            | undefined;
          const assetId = picked?.id?.id ?? "";
          const asset = assetByIdRef.current.get(assetId);
          if (asset) onSelectRef.current(asset);
        },
        Cesium.ScreenSpaceEventType.LEFT_CLICK,
      );

      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(
          MAUBIN_CENTER[0],
          MAUBIN_CENTER[1],
          65_000,
        ),
        orientation: {
          heading: Cesium.Math.toRadians(-24),
          pitch: Cesium.Math.toRadians(-52),
          roll: 0,
        },
        duration: 0,
      });
      updateReadout();
      setTerrainStatus(resolvedTerrainStatus);
      setLoadError(null);
      setReady(true);
    };

    void initialize().catch((error: unknown) => {
      if (disposed) return;
      setLoadError(
        error instanceof Error
          ? error.message
          : "Cesium scene could not be initialized.",
      );
    });

    return () => {
      disposed = true;
      inputHandler?.destroy();
      const viewer = viewerRef.current;
      if (viewer && !viewer.isDestroyed()) viewer.destroy();
      viewerRef.current = null;
      cesiumRef.current = null;
      sourcesRef.current = {};
      selectedSourceRef.current = null;
      initializedImageryModeRef.current = null;
    };
  }, [ionToken, satelliteUrl, terrainUrl, tileUrl]);

  useEffect(() => {
    const viewer = viewerRef.current;
    const Cesium = cesiumRef.current;
    if (!viewer || !Cesium || !ready) return;
    let disposed = false;

    // The initial Viewer already owns this imagery layer. Avoid fetching the
    // same visible tiles a second time immediately after startup.
    if (initializedImageryModeRef.current === imageryMode) {
      initializedImageryModeRef.current = null;
      return;
    }

    const replaceImagery = async () => {
      setImageryStatus(
        imageryMode === "satellite"
          ? "Loading satellite imagery…"
          : "Loading street map…",
      );
      try {
        const provider = await createImageryProvider(
          Cesium,
          imageryMode,
          satelliteUrl,
          tileUrl,
        );
        if (disposed || viewer.isDestroyed()) return;
        viewer.imageryLayers.removeAll(true);
        viewer.imageryLayers.addImageryProvider(provider);
        viewer.scene.requestRender();
        setImageryStatus(
          imageryMode === "satellite"
            ? "Esri World Imagery satellite"
            : "OpenStreetMap streets",
        );
      } catch {
        if (disposed || imageryMode === "streets") return;
        setImageryStatus("Satellite unavailable · switching to streets");
        setImageryMode("streets");
      }
    };

    void replaceImagery();
    return () => {
      disposed = true;
    };
  }, [imageryMode, ready, satelliteUrl, tileUrl]);

  useEffect(() => {
    const viewer = viewerRef.current;
    const Cesium = cesiumRef.current;
    const asset = selectedId ? assetById.get(selectedId) : undefined;
    if (!viewer || !Cesium || !ready) return;
    let disposed = false;

    const replaceSelection = async () => {
      if (selectedSourceRef.current) {
        viewer.dataSources.remove(selectedSourceRef.current, true);
        selectedSourceRef.current = null;
      }
      if (!asset) {
        viewer.scene.requestRender();
        return;
      }
      const selected = await Cesium.GeoJsonDataSource.load(
        {
          type: "FeatureCollection",
          features: [
            toFeature(asset, {
              fill: "#fff5ad",
              "fill-opacity": 0.2,
              stroke: "#fff5ad",
              "stroke-width": 4,
            }),
          ],
        },
        { clampToGround: true },
      );
      if (disposed || viewer.isDestroyed()) return;
      await viewer.dataSources.add(selected);
      selectedSourceRef.current = selected;
      viewer.scene.requestRender();
    };

    void replaceSelection();
    return () => {
      disposed = true;
    };
  }, [assetById, ready, selectedId]);

  useEffect(() => {
    const viewer = viewerRef.current;
    const Cesium = cesiumRef.current;
    if (!viewer || !Cesium || !ready) return;
    let disposed = false;

    const replaceSources = async () => {
      const loads = [
        Cesium.GeoJsonDataSource.load(terrainCollection, {
          clampToGround: true,
        }),
        Cesium.GeoJsonDataSource.load(waterwayCollection, {
          clampToGround: true,
        }),
        Cesium.GeoJsonDataSource.load(boundaryCollection, {
          clampToGround: true,
        }),
        Cesium.GeoJsonDataSource.load(floodExtentCollection, {
          clampToGround: true,
        }),
      ];
      if (sensorCollection.features.length) {
        loads.push(
          Cesium.GeoJsonDataSource.load(sensorCollection, {
            clampToGround: true,
          }),
        );
      }
      const results = await Promise.all(loads);
      const terrain = results[0];
      const waterways = results[1];
      const boundary = results[2];
      const floodExtents = results[3];
      const sensors = results[4];
      for (const entity of [
        ...terrain.entities.values,
        ...floodExtents.entities.values,
      ]) {
        if (entity.polygon) {
          entity.polygon.outline = new Cesium.ConstantProperty(false);
        }
      }
      if (sensors) {
        for (const entity of sensors.entities.values) {
          if (entity.position) {
            entity.point = new Cesium.PointGraphics({
              pixelSize: 12,
              color: Cesium.Color.fromCssColorString("#caff5b"),
              outlineColor: Cesium.Color.fromCssColorString("#062324"),
              outlineWidth: 2,
              heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
            });
          }
        }
      }
      if (disposed || viewer.isDestroyed()) return;
      removeSources(viewer, sourcesRef.current);
      const addPromises = [
        viewer.dataSources.add(terrain),
        viewer.dataSources.add(waterways),
        viewer.dataSources.add(boundary),
        viewer.dataSources.add(floodExtents),
      ];
      if (sensors) addPromises.push(viewer.dataSources.add(sensors));
      await Promise.all(addPromises);
      sourcesRef.current = { terrain, waterways, boundary, floodExtents, sensors };
      viewer.scene.requestRender();
    };

    void replaceSources().catch((error: unknown) => {
      if (disposed) return;
      setLoadError(
        error instanceof Error
          ? error.message
          : "Cesium overlays could not be loaded.",
      );
    });
    return () => {
      disposed = true;
    };
  }, [
    boundaryCollection,
    floodExtentCollection,
    ready,
    sensorCollection,
    terrainCollection,
    waterwayCollection,
  ]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;
    viewer.scene.verticalExaggeration = exaggeration;
    viewer.scene.requestRender();
  }, [exaggeration]);

  const resetView = () => {
    const viewer = viewerRef.current;
    const Cesium = cesiumRef.current;
    if (!viewer || !Cesium) return;
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(
        MAUBIN_CENTER[0],
        MAUBIN_CENTER[1],
        65_000,
      ),
      orientation: {
        heading: Cesium.Math.toRadians(-24),
        pitch: Cesium.Math.toRadians(-52),
        roll: 0,
      },
      duration: 0.9,
    });
  };

  return (
    <div className={styles.mapShell}>
      <div ref={containerRef} className={styles.map} />
      {!ready && !loadError ? (
        <div className={styles.loading}>
          <i />
          <span>Building Cesium globe and terrain…</span>
        </div>
      ) : null}
      {loadError ? <div className={styles.error}>{loadError}</div> : null}
      {chromeless ? null : (
        <>
          <div className={styles.modeBadge}>
            <i />
            CesiumJS
          </div>
          <div className={styles.imagerySwitch} aria-label="Cesium basemap">
            <button
              type="button"
              className={imageryMode === "satellite" ? styles.active : ""}
              aria-pressed={imageryMode === "satellite"}
              onClick={() => setImageryMode("satellite")}
            >
              Satellite
            </button>
            <button
              type="button"
              className={imageryMode === "streets" ? styles.active : ""}
              aria-pressed={imageryMode === "streets"}
              onClick={() => setImageryMode("streets")}
            >
              Streets
            </button>
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
          <div className={styles.statusStack}>
            <span>{imageryStatus}</span>
            <span>{terrainStatus}</span>
          </div>
          <div className={styles.readout} aria-live="polite">
            <span>WGS84 globe</span>
            <span>
              {readout.latitude.toFixed(5)}°, {readout.longitude.toFixed(5)}°
            </span>
            <span>{readout.heightKm.toFixed(1)} km</span>
            <span>
              H{readout.heading.toFixed(0)}° · P{readout.pitch.toFixed(0)}°
            </span>
          </div>
          <div className={styles.gestureHint}>
            Drag to orbit · wheel to zoom · Ctrl-drag to tilt
          </div>
        </>
      )}
    </div>
  );
}

declare global {
  interface Window {
    CESIUM_BASE_URL?: string;
    Cesium?: CesiumModule;
  }
}
