"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useTransition,
} from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import type {
  DashboardData,
  FloodEventMlEvaluationReport,
  FloodEventMlPredictionIndex,
  FloodEventMlPredictionItem,
  FloodMlPredictionIndexItem,
  ForecastPredictionIndex,
  ForecastPredictionItem,
  GeoAsset,
  GeoJSONGeometry,
  HydroObservation,
  LandCoverSummary,
  RainfallHistory,
  SensorStation,
  TerrainScreeningIndex,
  TerrainScreeningIndexItem,
} from "@/lib/api";
import styles from "./dashboard.module.css";
import SituationOverview from "./situation-overview";
import FloodExplainability from "./flood-explainability";
import ValidationPanel from "./validation-panel";
import { fetchFloodExtents } from "@/lib/flood-extents";
import LanguageSwitcher from "./language-switcher";
import {
  MapLoading2D,
  MapLoading3D,
  MapLoadingCesium,
} from "./map-loading-fallbacks";
import { useTranslation } from "@/lib/i18n";

type AssetFilter = "all" | "river_segment" | "canal_segment";
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
type Coordinate = [number, number];

const MAP_WIDTH = 1000;
const MAP_HEIGHT = 650;
const MAP_PADDING = 44;
const MAX_MAP_ZOOM = 16;

type ViewBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

const INITIAL_VIEW_BOX: ViewBox = {
  x: 0,
  y: 0,
  width: MAP_WIDTH,
  height: MAP_HEIGHT,
};

function clampViewBox(viewBox: ViewBox): ViewBox {
  const width = Math.min(
    MAP_WIDTH,
    Math.max(MAP_WIDTH / MAX_MAP_ZOOM, viewBox.width),
  );
  const height = width * (MAP_HEIGHT / MAP_WIDTH);
  return {
    x: Math.min(Math.max(0, viewBox.x), MAP_WIDTH - width),
    y: Math.min(Math.max(0, viewBox.y), MAP_HEIGHT - height),
    width,
    height,
  };
}

function flattenCoordinates(value: unknown): Coordinate[] {
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

function geometryCoordinates(geometry: GeoJSONGeometry): Coordinate[] {
  if (geometry.type === "GeometryCollection") {
    return (geometry.geometries ?? []).flatMap(geometryCoordinates);
  }
  return flattenCoordinates(geometry.coordinates);
}

function geometryLines(geometry: GeoJSONGeometry): Coordinate[][] {
  const coordinates = geometry.coordinates;
  if (!Array.isArray(coordinates)) return [];
  if (geometry.type === "LineString") return [coordinates as Coordinate[]];
  if (geometry.type === "MultiLineString" || geometry.type === "Polygon") {
    return coordinates as Coordinate[][];
  }
  if (geometry.type === "MultiPolygon") {
    return (coordinates as Coordinate[][][]).flat();
  }
  return [];
}

const InteractiveMap = dynamic(() => import("./interactive-map"), {
  ssr: false,
  loading: MapLoading2D,
});

const InteractiveMap3D = dynamic(() => import("./interactive-map-3d"), {
  ssr: false,
  loading: MapLoading3D,
});

const InteractiveMapCesium = dynamic(() => import("./interactive-map-cesium"), {
  ssr: false,
  loading: MapLoadingCesium,
});

function localizedAssetLabel(
  assetType: string,
  translate: (key: string) => string,
) {
  if (assetType === "terrain_cell") return translate("common.terrain");
  if (assetType === "river_segment") return translate("common.river");
  if (assetType === "canal_segment") return translate("common.canal");
  if (assetType === "township_boundary") return translate("common.boundary");
  if (assetType === "historical_flood_extent") {
    return translate("common.historicalFlood");
  }
  return assetType.replaceAll("_", " ");
}

function landCoverLabel(code: number, translate: (key: string) => string) {
  const keys: Record<number, string> = {
    10: "landCover.treeCover",
    20: "landCover.shrubland",
    30: "landCover.grassland",
    40: "landCover.cropland",
    50: "landCover.builtUp",
    60: "landCover.bareSparse",
    70: "landCover.snowIce",
    80: "landCover.permanentWater",
    90: "landCover.herbaceousWetland",
    95: "landCover.mangroves",
    100: "landCover.mossLichen",
  };
  return keys[code] ? translate(keys[code]) : String(code);
}

const LAND_COVER_CLASSES: Record<number, { name: string; color: string }> = {
  10: { name: "Tree cover", color: "#006400" },
  20: { name: "Shrubland", color: "#ffbb22" },
  30: { name: "Grassland", color: "#ffff4c" },
  40: { name: "Cropland", color: "#f096ff" },
  50: { name: "Built-up", color: "#fa0000" },
  60: { name: "Bare / sparse vegetation", color: "#b4b4b4" },
  70: { name: "Snow and ice", color: "#f0f0f0" },
  80: { name: "Permanent water", color: "#0064c8" },
  90: { name: "Herbaceous wetland", color: "#0096a0" },
  95: { name: "Mangroves", color: "#00cf75" },
  100: { name: "Moss and lichen", color: "#fae6a0" },
};

function formatNumber(value: number, digits = 0) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Yangon",
  }).format(new Date(value));
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function asNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function assetLabel(assetType: string) {
  if (assetType === "terrain_cell") return "Terrain";
  if (assetType === "river_segment") return "River";
  if (assetType === "canal_segment") return "Canal";
  if (assetType === "township_boundary") return "Boundary";
  if (assetType === "historical_flood_extent") return "Historical flood";
  return assetType.replaceAll("_", " ");
}

function terrainColor(percentile: number) {
  if (percentile <= 20) return "#5cc9d8";
  if (percentile <= 40) return "#77d6c4";
  if (percentile <= 60) return "#b8d98c";
  if (percentile <= 80) return "#e2ca76";
  return "#dc9b67";
}

function screeningColor(score: number) {
  if (score < 25) return "#78c8b2";
  if (score < 50) return "#d1d66f";
  if (score < 75) return "#f2ac57";
  return "#e85f4f";
}

function MiniIcon({
  name,
}: {
  name: "layers" | "river" | "route" | "pulse" | "search" | "refresh";
}) {
  const paths = {
    layers: (
      <>
        <path d="m12 3-9 5 9 5 9-5-9-5Z" />
        <path d="m3 12 9 5 9-5M3 16l9 5 9-5" />
      </>
    ),
    river: <path d="M4 4c4 2 4 6 8 8s4 6 8 8M4 12c3 1 4 3 5 5" />,
    route: (
      <>
        <circle cx="6" cy="18" r="2" />
        <circle cx="18" cy="6" r="2" />
        <path d="M8 18h2a4 4 0 0 0 4-4v-4a4 4 0 0 1 4-4" />
      </>
    ),
    pulse: <path d="M3 12h4l2-6 4 12 2-6h6" />,
    search: (
      <>
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-4-4" />
      </>
    ),
    refresh: (
      <>
        <path d="M20 7v5h-5" />
        <path d="M4 17v-5h5" />
        <path d="M6.1 9A7 7 0 0 1 18 7l2 5M4 12l2 5a7 7 0 0 0 11.9-2" />
      </>
    ),
  };

  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}

export function LegacyAssetMap({
  assets,
  terrainCells,
  screeningById,
  layer,
  selectedId,
  onSelect,
}: {
  assets: GeoAsset[];
  terrainCells: GeoAsset[];
  screeningById: Map<string, TerrainScreeningIndexItem>;
  layer: MapLayer;
  selectedId: string | null;
  onSelect: (asset: GeoAsset) => void;
}) {
  const { t } = useTranslation();
  const svgRef = useRef<SVGSVGElement | null>(null);
  const dragRef = useRef<{
    pointerId: number;
    startClientX: number;
    startClientY: number;
    startViewBox: ViewBox;
    moved: boolean;
  } | null>(null);
  const suppressClickRef = useRef(false);
  const [viewBox, setViewBox] = useState<ViewBox>(INITIAL_VIEW_BOX);
  const [isDragging, setIsDragging] = useState(false);

  const zoomAt = useCallback(
    (factor: number, clientX?: number, clientY?: number) => {
      setViewBox((current) => {
        const rect = svgRef.current?.getBoundingClientRect();
        const anchorX =
          rect && clientX !== undefined
            ? current.x + ((clientX - rect.left) / rect.width) * current.width
            : current.x + current.width / 2;
        const anchorY =
          rect && clientY !== undefined
            ? current.y + ((clientY - rect.top) / rect.height) * current.height
            : current.y + current.height / 2;
        const nextWidth = current.width * factor;
        const nextHeight = nextWidth * (MAP_HEIGHT / MAP_WIDTH);
        const ratioX = (anchorX - current.x) / current.width;
        const ratioY = (anchorY - current.y) / current.height;
        return clampViewBox({
          x: anchorX - ratioX * nextWidth,
          y: anchorY - ratioY * nextHeight,
          width: nextWidth,
          height: nextHeight,
        });
      });
    },
    [],
  );

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const handleWheel = (event: WheelEvent) => {
      event.preventDefault();
      zoomAt(event.deltaY > 0 ? 1.18 : 0.84, event.clientX, event.clientY);
    };
    svg.addEventListener("wheel", handleWheel, { passive: false });
    return () => svg.removeEventListener("wheel", handleWheel);
  }, [zoomAt]);

  const startDrag = (event: React.PointerEvent<SVGSVGElement>) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startViewBox: viewBox,
      moved: false,
    };
    setIsDragging(true);
  };

  const moveDrag = (event: React.PointerEvent<SVGSVGElement>) => {
    const drag = dragRef.current;
    const rect = svgRef.current?.getBoundingClientRect();
    if (!drag || drag.pointerId !== event.pointerId || !rect) return;
    const deltaX = event.clientX - drag.startClientX;
    const deltaY = event.clientY - drag.startClientY;
    if (Math.abs(deltaX) + Math.abs(deltaY) > 3) drag.moved = true;
    setViewBox(
      clampViewBox({
        ...drag.startViewBox,
        x:
          drag.startViewBox.x - (deltaX / rect.width) * drag.startViewBox.width,
        y:
          drag.startViewBox.y -
          (deltaY / rect.height) * drag.startViewBox.height,
      }),
    );
  };

  const endDrag = (event: React.PointerEvent<SVGSVGElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    suppressClickRef.current = drag.moved;
    dragRef.current = null;
    setIsDragging(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    window.requestAnimationFrame(() => {
      suppressClickRef.current = false;
    });
  };

  const selectAsset = (asset: GeoAsset) => {
    if (!suppressClickRef.current) onSelect(asset);
  };

  const boundary = assets.find(
    (asset) => asset.properties.asset_type === "township_boundary",
  );
  const referenceCoordinates = boundary
    ? geometryCoordinates(boundary.geometry)
    : [...assets, ...terrainCells].flatMap((asset) =>
        geometryCoordinates(asset.geometry),
      );

  if (referenceCoordinates.length === 0) {
    return (
      <div className={styles.emptyMap}>
        <div className={styles.emptyOrb} />
        <p>{t("errors.noSpatialFeatures")}</p>
        <span>{t("errors.startBackend")}</span>
      </div>
    );
  }

  const longitudes = referenceCoordinates.map(([longitude]) => longitude);
  const latitudes = referenceCoordinates.map(([, latitude]) => latitude);
  const minLongitude = Math.min(...longitudes);
  const maxLongitude = Math.max(...longitudes);
  const minLatitude = Math.min(...latitudes);
  const maxLatitude = Math.max(...latitudes);
  const longitudeSpan = Math.max(maxLongitude - minLongitude, 0.0001);
  const latitudeSpan = Math.max(maxLatitude - minLatitude, 0.0001);
  const scale = Math.min(
    (MAP_WIDTH - MAP_PADDING * 2) / longitudeSpan,
    (MAP_HEIGHT - MAP_PADDING * 2) / latitudeSpan,
  );
  const xOffset = (MAP_WIDTH - longitudeSpan * scale) / 2;
  const yOffset = (MAP_HEIGHT - latitudeSpan * scale) / 2;

  const project = ([longitude, latitude]: Coordinate): Coordinate => [
    xOffset + (longitude - minLongitude) * scale,
    yOffset + (maxLatitude - latitude) * scale,
  ];
  const pathFor = (line: Coordinate[]) =>
    line
      .map((coordinate, index) => {
        const [x, y] = project(coordinate);
        return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");

  const boundaryLines = boundary ? geometryLines(boundary.geometry) : [];
  const waterways = assets.filter((asset) =>
    ["river_segment", "canal_segment"].includes(asset.properties.asset_type),
  );

  return (
    <>
      <svg
        ref={svgRef}
        className={`${styles.mapSvg} ${isDragging ? styles.mapDragging : ""}`}
        viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`}
        role="img"
        aria-label="Maubin Township terrain and waterway map"
        onPointerDown={startDrag}
        onPointerMove={moveDrag}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
      >
        <defs>
          <pattern
            id="grid"
            width="42"
            height="42"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M42 0H0V42"
              fill="none"
              stroke="#b5e5dd"
              strokeOpacity=".08"
            />
          </pattern>
          <filter id="glow">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <rect width={MAP_WIDTH} height={MAP_HEIGHT} fill="url(#grid)" />
        {boundaryLines.map((line, index) => (
          <path
            key={`boundary-${index}`}
            d={`${pathFor(line)} Z`}
            className={styles.boundaryShape}
          />
        ))}
        {layer !== "network"
          ? terrainCells.flatMap((asset) =>
              geometryLines(asset.geometry).map((line, index) => (
                <path
                  key={`${asset.id}-${index}`}
                  d={`${pathFor(line)} Z`}
                  className={[
                    styles.terrainCell,
                    asset.id === selectedId ? styles.selectedTerrain : "",
                  ].join(" ")}
                  style={{
                    fill:
                      layer === "screening"
                        ? screeningColor(
                            asNumber(
                              screeningById.get(asset.id)?.screening_score,
                            ),
                          )
                        : terrainColor(
                            asNumber(
                              asset.properties.metadata.elevation_percentile,
                            ),
                          ),
                  }}
                  onClick={() => selectAsset(asset)}
                  tabIndex={0}
                  role="button"
                  aria-label={
                    layer === "screening"
                      ? `Select terrain cell with ${formatNumber(
                          asNumber(
                            screeningById.get(asset.id)?.screening_score,
                          ),
                          1,
                        )} relative susceptibility score`
                      : `Select terrain cell at ${formatNumber(
                          asNumber(asset.properties.metadata.elevation_mean_m),
                          1,
                        )} metres mean elevation`
                  }
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      selectAsset(asset);
                    }
                  }}
                  vectorEffect="non-scaling-stroke"
                />
              )),
            )
          : null}
        {waterways.flatMap((asset) =>
          geometryLines(asset.geometry).map((line, index) => {
            const selected = asset.id === selectedId;
            const river = asset.properties.asset_type === "river_segment";
            return (
              <path
                key={`${asset.id}-${index}`}
                d={pathFor(line)}
                className={[
                  styles.waterway,
                  river ? styles.river : styles.canal,
                  selected ? styles.selectedWaterway : "",
                ].join(" ")}
                onClick={() => selectAsset(asset)}
                tabIndex={0}
                role="button"
                aria-label={`Select ${asset.properties.name}`}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    selectAsset(asset);
                  }
                }}
                vectorEffect="non-scaling-stroke"
                filter={selected ? "url(#glow)" : undefined}
              />
            );
          }),
        )}
        <g className={styles.northMarker} transform="translate(922 74)">
          <path d="M0 28 12 0l12 28-12-6-12 6Z" />
          <text x="12" y="-10" textAnchor="middle">
            N
          </text>
        </g>
      </svg>
      <div className={styles.mapZoomControls} aria-label="Map zoom controls">
        <button onClick={() => zoomAt(0.7)} aria-label="Zoom in">
          +
        </button>
        <span>{formatNumber(MAP_WIDTH / viewBox.width, 1)}×</span>
        <button onClick={() => zoomAt(1.4)} aria-label="Zoom out">
          −
        </button>
        <button
          onClick={() => setViewBox(INITIAL_VIEW_BOX)}
          aria-label="Reset map view"
          title="Reset map view"
        >
          ↺
        </button>
      </div>
    </>
  );
}

function WaterLevelChart({
  readings,
  station,
}: {
  readings: HydroObservation[];
  station: SensorStation | undefined;
}) {
  const { t, formatNumber, formatDateTime } = useTranslation();
  const points = readings
    .filter((reading) => reading.properties.water_level_m !== null)
    .sort(
      (left, right) =>
        Date.parse(left.properties.observed_at) -
        Date.parse(right.properties.observed_at),
    )
    .slice(-48);

  if (!points.length) {
    return (
      <div className={styles.chartEmpty}>
        <strong>{t("liveMonitor.noReadings")}</strong>
        <p>{t("liveMonitor.noReadingsHint")}</p>
      </div>
    );
  }

  const width = 900;
  const height = 250;
  const padding = { top: 20, right: 24, bottom: 38, left: 54 };
  const waterLevels = points.map(
    (reading) => (reading.properties.water_level_m ?? 0) * 100,
  );
  const thresholdValues = [
    station?.properties.warning_level_cm,
    station?.properties.danger_level_cm,
    station?.properties.critical_level_cm,
  ].filter((value): value is number => value !== null && value !== undefined);
  const allValues = [...waterLevels, ...thresholdValues];
  const rawMin = Math.min(...allValues);
  const rawMax = Math.max(...allValues);
  const paddingCm = Math.max((rawMax - rawMin) * 0.15, 10);
  const minY = Math.floor((rawMin - paddingCm) / 10) * 10;
  const maxY = Math.ceil((rawMax + paddingCm) / 10) * 10;
  const spanY = Math.max(maxY - minY, 1);
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const projectX = (index: number) =>
    padding.left +
    (points.length === 1
      ? plotWidth / 2
      : (index / (points.length - 1)) * plotWidth);
  const projectY = (value: number) =>
    padding.top + ((maxY - value) / spanY) * plotHeight;
  const linePath = waterLevels
    .map(
      (value, index) =>
        `${index ? "L" : "M"}${projectX(index).toFixed(1)},${projectY(value).toFixed(1)}`,
    )
    .join(" ");
  const thresholds = [
    [t("liveMonitor.warning"), station?.properties.warning_level_cm, styles.thresholdWarning],
    [t("liveMonitor.danger"), station?.properties.danger_level_cm, styles.thresholdDanger],
    [
      t("liveMonitor.critical"),
      station?.properties.critical_level_cm,
      styles.thresholdCritical,
    ],
  ] as const;

  return (
    <div className={styles.chartScroll}>
      <svg
        className={styles.levelChart}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={t("liveMonitor.waterLevelFor", {
          name: station?.properties.name ?? points[0].properties.station_name,
        })}
      >
        {Array.from({ length: 5 }, (_, index) => {
          const value = minY + (spanY * index) / 4;
          const y = projectY(value);
          return (
            <g key={value}>
              <line
                className={styles.chartGridLine}
                x1={padding.left}
                x2={width - padding.right}
                y1={y}
                y2={y}
              />
              <text
                className={styles.chartAxisLabel}
                x={padding.left - 10}
                y={y + 3}
                textAnchor="end"
              >
                {formatNumber(value)} cm
              </text>
            </g>
          );
        })}
        {thresholds.map(([label, value, className]) =>
          value === null || value === undefined ? null : (
            <g key={label}>
              <line
                className={`${styles.thresholdLine} ${className}`}
                x1={padding.left}
                x2={width - padding.right}
                y1={projectY(value)}
                y2={projectY(value)}
              />
              <text
                className={styles.thresholdLabel}
                x={width - padding.right - 4}
                y={projectY(value) - 5}
                textAnchor="end"
              >
                {label} {formatNumber(value)} cm
              </text>
            </g>
          ),
        )}
        <path
          className={styles.levelArea}
          d={`${linePath} L${projectX(points.length - 1)},${padding.top + plotHeight} L${projectX(0)},${padding.top + plotHeight} Z`}
        />
        <path className={styles.levelLine} d={linePath} />
        {waterLevels.map((value, index) => (
          <circle
            key={points[index].id}
            className={styles.levelPoint}
            cx={projectX(index)}
            cy={projectY(value)}
            r={points.length === 1 || index === points.length - 1 ? 4 : 2.5}
          >
            <title>
              {formatDateTime(points[index].properties.observed_at)} ·{" "}
              {formatNumber(value, 1)} cm
            </title>
          </circle>
        ))}
        <text
          className={styles.chartTimeLabel}
          x={padding.left}
          y={height - 12}
        >
          {formatDateTime(points[0].properties.observed_at)}
        </text>
        <text
          className={styles.chartTimeLabel}
          x={width - padding.right}
          y={height - 12}
          textAnchor="end"
        >
          {formatDateTime(points[points.length - 1].properties.observed_at)}
        </text>
      </svg>
    </div>
  );
}

type RainfallWindow = 30 | 90 | 366;

function RainfallHistoryChart({
  history,
}: {
  history: RainfallHistory | null;
}) {
  const { t, formatNumber, formatDate } = useTranslation();
  const [windowDays, setWindowDays] = useState<RainfallWindow>(90);
  const points = (history?.daily ?? []).slice(-windowDays);

  if (!history || history.status !== "available" || !points.length) {
    return (
      <section className={styles.rainfallHistory}>
        <div className={styles.rainfallHistoryHeader}>
          <div>
            <p className={styles.eyebrow}>{t("rainfall.eyebrow")}</p>
            <h3>{t("rainfall.title")}</h3>
          </div>
        </div>
        <div className={styles.rainfallHistoryEmpty}>
          <strong>{t("rainfall.notLoaded")}</strong>
          <p>{t("rainfall.notLoadedHint")}</p>
        </div>
      </section>
    );
  }

  const width = 900;
  const height = 280;
  const padding = { top: 24, right: 24, bottom: 42, left: 54 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const rawMax = Math.max(
    1,
    ...points.flatMap((point) => [
      point.mean_precipitation_mm,
      point.accumulation_7d_mm,
    ]),
  );
  const maxY = Math.max(5, Math.ceil(rawMax / 5) * 5);
  const projectX = (index: number) =>
    padding.left +
    (points.length === 1
      ? plotWidth / 2
      : (index / (points.length - 1)) * plotWidth);
  const projectY = (value: number) =>
    padding.top + ((maxY - value) / maxY) * plotHeight;
  const barSlot = plotWidth / Math.max(points.length, 1);
  const barWidth = Math.max(1.2, Math.min(12, barSlot * 0.7));
  const accumulationPath = points
    .map(
      (point, index) =>
        `${index ? "L" : "M"}${projectX(index).toFixed(1)},${projectY(
          point.accumulation_7d_mm,
        ).toFixed(1)}`,
    )
    .join(" ");
  const labelIndexes = new Set(
    Array.from({ length: 5 }, (_, index) =>
      Math.round((index * (points.length - 1)) / 4),
    ),
  );
  const periodTotal = points.reduce(
    (total, point) => total + point.mean_precipitation_mm,
    0,
  );
  const wetDays = points.filter(
    (point) => point.mean_precipitation_mm >= 1,
  ).length;
  const peakDaily = points.reduce((peak, point) =>
    point.mean_precipitation_mm > peak.mean_precipitation_mm ? point : peak,
  );
  const latest = points[points.length - 1];

  return (
    <section className={styles.rainfallHistory}>
      <div className={styles.rainfallHistoryHeader}>
        <div>
          <p className={styles.eyebrow}>{t("rainfall.eyebrow")}</p>
          <h3>{t("rainfall.title")}</h3>
          <p>{t("rainfall.intro")}</p>
        </div>
        <div
          className={styles.historyWindow}
          aria-label="Rainfall history window"
        >
          {(
            [
              [30, t("rainfall.window30")],
              [90, t("rainfall.window90")],
              [366, t("rainfall.window366")],
            ] as const
          ).map(([days, label]) => (
            <button
              key={days}
              type="button"
              className={windowDays === days ? styles.activeHistoryWindow : ""}
              aria-pressed={windowDays === days}
              onClick={() => setWindowDays(days as RainfallWindow)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className={styles.rainfallHistoryBody}>
        <div className={styles.rainfallChartPanel}>
          <div className={styles.rainfallLegend}>
            <span>
              <i className={styles.dailyRainSwatch} />
              {t("rainfall.dailyMean")}
            </span>
            <span>
              <i className={styles.accumulationSwatch} />
              {t("rainfall.rolling7day")}
            </span>
          </div>
          <div className={styles.chartScroll}>
            <svg
              className={styles.rainfallChart}
              viewBox={`0 0 ${width} ${height}`}
              role="img"
              aria-label={t("rainfall.chartAria", {
                start: formatDate(points[0].date),
                end: formatDate(latest.date),
              })}
            >
              {Array.from({ length: 5 }, (_, index) => {
                const value = (maxY * index) / 4;
                const y = projectY(value);
                return (
                  <g key={value}>
                    <line
                      className={styles.chartGridLine}
                      x1={padding.left}
                      x2={width - padding.right}
                      y1={y}
                      y2={y}
                    />
                    <text
                      className={styles.chartAxisLabel}
                      x={padding.left - 10}
                      y={y + 3}
                      textAnchor="end"
                    >
                      {formatNumber(value, value < 10 ? 1 : 0)} mm
                    </text>
                  </g>
                );
              })}
              {points.map((point, index) => {
                const y = projectY(point.mean_precipitation_mm);
                return (
                  <rect
                    key={point.date}
                    className={styles.rainfallBar}
                    x={projectX(index) - barWidth / 2}
                    y={y}
                    width={barWidth}
                    height={Math.max(0, padding.top + plotHeight - y)}
                    rx={Math.min(2, barWidth / 2)}
                  >
                    <title>
                      {`${formatDate(point.date)} · daily ${formatNumber(
                        point.mean_precipitation_mm,
                        1,
                      )} mm · 7-day ${formatNumber(
                        point.accumulation_7d_mm,
                        1,
                      )} mm`}
                    </title>
                  </rect>
                );
              })}
              <path
                className={styles.rainfallAccumulationLine}
                d={accumulationPath}
              />
              {points.map((point, index) =>
                labelIndexes.has(index) ? (
                  <text
                    key={point.date}
                    className={styles.chartTimeLabel}
                    x={projectX(index)}
                    y={height - 14}
                    textAnchor={
                      index === 0
                        ? "start"
                        : index === points.length - 1
                          ? "end"
                          : "middle"
                    }
                  >
                    {formatDate(point.date)}
                  </text>
                ) : null,
              )}
            </svg>
          </div>
          <p className={styles.rainfallMethodNote}>
            {history.attribution} · approximately{" "}
            {formatNumber(history.source_resolution_m / 1000)} km source grid ·{" "}
            {history.grid_cell_count} township-intersecting cells
          </p>
        </div>
        <aside className={styles.rainfallSummary}>
          <span>{t("rainfall.selectedPeriod")}</span>
          <strong>{formatNumber(periodTotal, 1)} mm</strong>
          <small>
            {formatDate(points[0].date)} – {formatDate(latest.date)}
          </small>
          <dl>
            <div>
              <dt>{t("rainfall.wetDays")}</dt>
              <dd>
                {wetDays} / {points.length}
              </dd>
            </div>
            <div>
              <dt>{t("rainfall.peakDaily")}</dt>
              <dd>{formatNumber(peakDaily.mean_precipitation_mm, 1)} mm</dd>
            </div>
            <div>
              <dt>{t("rainfall.latest7day")}</dt>
              <dd>{formatNumber(latest.accumulation_7d_mm, 1)} mm</dd>
            </div>
            <div>
              <dt>{t("rainfall.latest30day")}</dt>
              <dd>{formatNumber(latest.accumulation_30d_mm, 1)} mm</dd>
            </div>
          </dl>
          <p>
            Historical reanalysis only. This chart does not show current flood
            water, probability, depth, or arrival time.
          </p>
        </aside>
      </div>
    </section>
  );
}

export default function Dashboard({
  assets,
  terrainCells: initialTerrainCells,
  terrainScreening: initialTerrainScreening,
  dataLayers,
  health,
  rainfallForecast,
  rainfallHistory,
  floodExtents: initialFloodExtents,
  floodMlPredictions,
  floodEventMlPredictions: initialFloodEventMlPredictions,
  forecastPredictions: initialForecastPredictions,
  floodIntelligence,
  sensorStations,
  latestObservations,
  recentObservations,
  openAlerts,
  mqttStatus,
  liveUpdatesUrl,
  spatialApiUrl,
  error,
}: DashboardData) {
  const router = useRouter();
  const { t, formatNumber, formatDate, formatDateTime } = useTranslation();
  const [isRefreshing, startRefresh] = useTransition();
  const [filter, setFilter] = useState<AssetFilter>("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mapLayer, setMapLayer] = useState<MapLayer>(() =>
    initialForecastPredictions?.items.length
      ? "forecast"
      : floodMlPredictions?.items.length
        ? "ml_prediction"
        : "screening",
  );
  const [mapView, setMapView] = useState<"2d" | "3d" | "cesium">("cesium");
  const [terrainCells, setTerrainCells] =
    useState<GeoAsset[]>(initialTerrainCells);
  const [terrainScreening, setTerrainScreening] =
    useState<TerrainScreeningIndex | null>(initialTerrainScreening);
  const [landCoverSummary, setLandCoverSummary] =
    useState<LandCoverSummary | null>(null);
  const [floodExtents, setFloodExtents] = useState<GeoAsset[]>(
    initialFloodExtents,
  );
  const [floodExtentsLoading, setFloodExtentsLoading] = useState(
    initialFloodExtents.length === 0,
  );
  const [floodExtentsLoadError, setFloodExtentsLoadError] = useState<
    string | null
  >(null);
  const [floodEventMlPredictions, setFloodEventMlPredictions] =
    useState<FloodEventMlPredictionIndex | null>(
      initialFloodEventMlPredictions,
    );
  const [forecastPredictions, setForecastPredictions] =
    useState<ForecastPredictionIndex | null>(initialForecastPredictions);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [eventHindcastLoading, setEventHindcastLoading] = useState(false);
  const [eventThresholdMode, setEventThresholdMode] = useState<
    "screening" | "balanced" | "conservative"
  >(() => {
    const operatingMode = initialFloodEventMlPredictions?.model.operating_mode;
    if (
      operatingMode === "screening" ||
      operatingMode === "balanced" ||
      operatingMode === "conservative"
    ) {
      return operatingMode;
    }
    return "balanced";
  });
  const [showHindcastOutcomes, setShowHindcastOutcomes] = useState(false);
  const [eventEvaluation, setEventEvaluation] =
    useState<FloodEventMlEvaluationReport | null>(null);
  const [terrainLoading, setTerrainLoading] = useState(
    initialTerrainCells.length === 0,
  );
  const [terrainLoadError, setTerrainLoadError] = useState<string | null>(null);
  const [liveReadings, setLiveReadings] =
    useState<HydroObservation[]>(recentObservations);
  const [liveConnection, setLiveConnection] = useState<
    "connecting" | "connected" | "disconnected"
  >("connecting");
  const [selectedStationId, setSelectedStationId] = useState(
    latestObservations[0]?.properties.station_id ??
      sensorStations[0]?.properties.station_id ??
      "",
  );

  useEffect(() => {
    const controller = new AbortController();
    const bounds = "min_lon=95.35&min_lat=16.45&max_lon=95.95&max_lat=16.98";

    const getTerrainPage = async (page: number) => {
      const response = await fetch(
        `${spatialApiUrl}/geo-assets/within-bounds?${bounds}&asset_type=terrain_cell&page=${page}&page_size=1000`,
        { signal: controller.signal },
      );
      if (!response.ok) {
        throw new Error(`Terrain API returned HTTP ${response.status}`);
      }
      return (await response.json()) as {
        features: GeoAsset[];
        meta: { pages: number };
      };
    };

    const loadSpatialScreening = async () => {
      setTerrainLoading(true);
      setTerrainLoadError(null);
      try {
        const firstPagePromise = getTerrainPage(1);
        const screeningPromise = fetch(
          `${spatialApiUrl}/flood-screening/terrain/index`,
          { signal: controller.signal },
        );
        const landCoverPromise = fetch(
          `${spatialApiUrl}/flood-screening/land-cover/summary`,
          { signal: controller.signal },
        ).catch(() => null);
        const firstPage = await firstPagePromise;
        const remainingPages =
          firstPage.meta.pages > 1
            ? await Promise.all(
                Array.from({ length: firstPage.meta.pages - 1 }, (_, index) =>
                  getTerrainPage(index + 2),
                ),
              )
            : [];
        const screeningResponse = await screeningPromise;
        if (!screeningResponse.ok) {
          throw new Error(
            `Screening API returned HTTP ${screeningResponse.status}`,
          );
        }
        const screening =
          (await screeningResponse.json()) as TerrainScreeningIndex;
        const landCoverResponse = await landCoverPromise;
        if (landCoverResponse?.ok) {
          setLandCoverSummary(
            (await landCoverResponse.json()) as LandCoverSummary,
          );
        }
        setTerrainCells([
          ...firstPage.features,
          ...remainingPages.flatMap((page) => page.features),
        ]);
        setTerrainScreening(screening);
      } catch (loadError) {
        if (controller.signal.aborted) return;
        setTerrainLoadError(
          loadError instanceof Error
            ? loadError.message
            : "Terrain screening could not be loaded.",
        );
      } finally {
        if (!controller.signal.aborted) setTerrainLoading(false);
      }
    };

    void loadSpatialScreening();
    return () => controller.abort();
  }, [spatialApiUrl]);

  useEffect(() => {
    if (initialFloodExtents.length > 0) return;
    const controller = new AbortController();

    const loadFloodExtents = async () => {
      setFloodExtentsLoading(true);
      setFloodExtentsLoadError(null);
      try {
        setFloodExtents(
          await fetchFloodExtents(spatialApiUrl, controller.signal),
        );
      } catch (loadError) {
        if (controller.signal.aborted) return;
        setFloodExtentsLoadError(
          loadError instanceof Error
            ? loadError.message
            : "Historical flood labels could not be loaded.",
        );
      } finally {
        if (!controller.signal.aborted) setFloodExtentsLoading(false);
      }
    };

    void loadFloodExtents();
    return () => controller.abort();
  }, [initialFloodExtents.length, spatialApiUrl]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let refreshTimer: ReturnType<typeof setTimeout> | null = null;
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      setLiveConnection("connecting");
      socket = new WebSocket(liveUpdatesUrl);
      socket.onopen = () => setLiveConnection("connected");
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as {
            type?: string;
            data?: HydroObservation;
          };
          if (
            message.type !== "sensor_reading" ||
            !message.data?.id ||
            !message.data.properties?.station_id
          ) {
            return;
          }
          const reading = message.data;
          setLiveReadings((current) =>
            [
              reading,
              ...current.filter((item) => item.id !== reading.id),
            ].slice(0, 500),
          );
          setSelectedStationId(
            (current) => current || reading.properties.station_id,
          );
          if (refreshTimer) clearTimeout(refreshTimer);
          refreshTimer = setTimeout(() => router.refresh(), 500);
        } catch {
          // Ignore malformed third-party frames; API events remain validated.
        }
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        if (disposed) return;
        setLiveConnection("disconnected");
        retryTimer = setTimeout(connect, 3000);
      };
    };

    connect();
    return () => {
      disposed = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (refreshTimer) clearTimeout(refreshTimer);
      socket?.close();
    };
  }, [liveUpdatesUrl, router]);

  const segments = useMemo(
    () =>
      assets.filter((asset) =>
        ["river_segment", "canal_segment"].includes(
          asset.properties.asset_type,
        ),
      ),
    [assets],
  );
  const filteredSegments = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return segments.filter((asset) => {
      const matchesType =
        filter === "all" || asset.properties.asset_type === filter;
      const searchable = [
        asset.properties.name,
        String(asset.properties.metadata.osm_id ?? ""),
        String(asset.properties.metadata.waterway ?? ""),
      ]
        .join(" ")
        .toLowerCase();
      return matchesType && searchable.includes(normalizedQuery);
    });
  }, [filter, query, segments]);
  const terrainScreeningById = useMemo(
    () =>
      new Map((terrainScreening?.items ?? []).map((item) => [item.id, item])),
    [terrainScreening],
  );
  const floodMlPredictionById = useMemo(
    () =>
      new Map<string, FloodMlPredictionIndexItem>(
        (floodMlPredictions?.items ?? []).map((item) => [item.id, item]),
      ),
    [floodMlPredictions],
  );
  const floodEventMlPredictionById = useMemo(
    () =>
      new Map<string, FloodEventMlPredictionItem>(
        (floodEventMlPredictions?.items ?? []).map((item) => [item.id, item]),
      ),
    [floodEventMlPredictions],
  );
  const forecastPredictionById = useMemo(
    () =>
      new Map<string, ForecastPredictionItem>(
        (forecastPredictions?.items ?? []).map((item) => [item.id, item]),
      ),
    [forecastPredictions],
  );
  const activePredictionById = useMemo(
    () =>
      mapLayer === "event_hindcast" || mapLayer === "validation"
        ? new Map<
            string,
            FloodMlPredictionIndexItem | FloodEventMlPredictionItem | ForecastPredictionItem
          >(floodEventMlPredictionById)
        : mapLayer === "forecast"
          ? new Map<
              string,
              FloodMlPredictionIndexItem | FloodEventMlPredictionItem | ForecastPredictionItem
            >(forecastPredictionById)
          : new Map<
              string,
              FloodMlPredictionIndexItem | FloodEventMlPredictionItem | ForecastPredictionItem
            >(floodMlPredictionById),
    [floodEventMlPredictionById, forecastPredictionById, floodMlPredictionById, mapLayer],
  );
  const lowestTerrainCell = useMemo(
    () =>
      terrainCells.reduce<GeoAsset | null>((lowest, cell) => {
        if (!lowest) return cell;
        return asNumber(cell.properties.metadata.elevation_mean_m) <
          asNumber(lowest.properties.metadata.elevation_mean_m)
          ? cell
          : lowest;
      }, null),
    [terrainCells],
  );
  const highestScreeningCell =
    terrainCells.find((cell) => cell.id === terrainScreening?.items[0]?.id) ??
    null;
  const firstLandCoverCell =
    terrainCells.find(
      (cell) => cell.properties.metadata.land_cover_dataset_id !== undefined,
    ) ?? null;
  const highestMlCell =
    terrainCells.find((cell) => cell.id === floodMlPredictions?.items[0]?.id) ??
    null;
  const highestEventMlCell =
    terrainCells.find(
      (cell) => cell.id === floodEventMlPredictions?.items[0]?.id,
    ) ?? null;
  const highestForecastCell =
    terrainCells.find(
      (cell) => cell.id === forecastPredictions?.items[0]?.id,
    ) ?? null;
  const selected =
    terrainCells.find((asset) => asset.id === selectedId) ??
    assets.find((asset) => asset.id === selectedId) ??
    floodExtents.find((asset) => asset.id === selectedId) ??
    (mapLayer === "screening"
      ? highestScreeningCell
      : mapLayer === "ml_prediction"
        ? highestMlCell
        : mapLayer === "event_hindcast" || mapLayer === "validation"
          ? highestEventMlCell
        : mapLayer === "forecast"
          ? highestForecastCell
          : mapLayer === "landcover"
            ? firstLandCoverCell
            : mapLayer === "flood_history"
              ? floodExtents[0]
              : mapLayer === "terrain"
                ? lowestTerrainCell
                : filteredSegments[0]) ??
    null;
  const selectedScreening = selected
    ? terrainScreeningById.get(selected.id)
    : undefined;
  const selectedMlPrediction = selected
    ? floodMlPredictionById.get(selected.id)
    : undefined;
  const selectedEventMlPrediction = selected
    ? floodEventMlPredictionById.get(selected.id)
    : undefined;
  const selectedForecastPrediction = selected
    ? forecastPredictionById.get(selected.id)
    : undefined;
  const mlTestMetrics =
    floodMlPredictions?.model.metrics.test &&
    typeof floodMlPredictions.model.metrics.test === "object"
      ? (floodMlPredictions.model.metrics.test as Record<string, unknown>)
      : null;
  const eventMlTestMetrics =
    floodEventMlPredictions?.model.metrics.test &&
    typeof floodEventMlPredictions.model.metrics.test === "object"
      ? (floodEventMlPredictions.model.metrics.test as Record<string, unknown>)
      : null;
  const rollingConservative =
    eventEvaluation?.rolling_origin_summary.conservative &&
    typeof eventEvaluation.rolling_origin_summary.conservative === "object"
      ? (eventEvaluation.rolling_origin_summary.conservative as Record<
          string,
          unknown
        >)
      : null;

  useEffect(() => {
    if (!floodEventMlPredictions) return;
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch(
          `${spatialApiUrl}/flood-ml/event-models/evaluation`,
          { signal: controller.signal },
        );
        if (!response.ok) return;
        setEventEvaluation(
          (await response.json()) as FloodEventMlEvaluationReport,
        );
      } catch {
        // Evaluation is optional for the dashboard; keep hindcast usable.
      }
    })();
    return () => controller.abort();
  }, [floodEventMlPredictions?.model.id, spatialApiUrl]);

  const selectEventHindcast = async (
    eventId: string,
    thresholdMode: "screening" | "balanced" | "conservative" = eventThresholdMode,
  ) => {
    setEventHindcastLoading(true);
    try {
      const response = await fetch(
        `${spatialApiUrl}/flood-ml/event-predictions/index?event_id=${encodeURIComponent(eventId)}&threshold_mode=${thresholdMode}`,
      );
      if (!response.ok) return;
      const next = (await response.json()) as FloodEventMlPredictionIndex;
      setFloodEventMlPredictions(next);
      setEventThresholdMode(thresholdMode);
      setSelectedId(next.items[0]?.id ?? null);
    } finally {
      setEventHindcastLoading(false);
    }
  };

  const runForecast = async () => {
    setForecastLoading(true);
    try {
      const response = await fetch(`${spatialApiUrl}/flood-forecast/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          threshold_mode: "balanced",
          forecast_days: 7,
        }),
      });
      if (!response.ok) return;
      const indexResponse = await fetch(
        `${spatialApiUrl}/flood-forecast/predictions/index`,
      );
      if (!indexResponse.ok) return;
      setForecastPredictions(
        (await indexResponse.json()) as ForecastPredictionIndex,
      );
      setMapLayer("forecast");
    } finally {
      setForecastLoading(false);
    }
  };
  const selectedScreeningFactors =
    selected && selectedScreening
      ? [
          {
            key: "low_elevation",
            label: "Low relative elevation",
            normalizedScore: selectedScreening.low_elevation_score,
            weight: terrainScreening?.methodology.weights.low_elevation ?? 0.55,
            observedValue: asNumber(
              selected.properties.metadata.elevation_mean_m,
            ),
            unit: "m",
          },
          {
            key: "waterway_proximity",
            label: "Waterway proximity",
            normalizedScore: selectedScreening.waterway_proximity_score,
            weight:
              terrainScreening?.methodology.weights.waterway_proximity ?? 0.3,
            observedValue: asNumber(
              selected.properties.metadata.distance_to_waterway_m,
            ),
            unit: "m",
          },
          {
            key: "flatness",
            label: "Local flatness",
            normalizedScore: selectedScreening.flatness_score,
            weight: terrainScreening?.methodology.weights.flatness ?? 0.15,
            observedValue: asNumber(
              selected.properties.metadata.local_relief_m,
            ),
            unit: "m relief",
          },
        ]
      : [];
  const riverSegments = segments.filter(
    (asset) => asset.properties.asset_type === "river_segment",
  );
  const canalSegments = segments.filter(
    (asset) => asset.properties.asset_type === "canal_segment",
  );
  const totalLengthKm =
    segments.reduce(
      (total, asset) =>
        total + asNumber(asset.properties.metadata.segment_length_m),
      0,
    ) / 1000;
  const terrainMin = terrainCells.length
    ? Math.min(
        ...terrainCells.map((cell) =>
          asNumber(cell.properties.metadata.elevation_min_m),
        ),
      )
    : 0;
  const terrainMax = terrainCells.length
    ? Math.max(
        ...terrainCells.map((cell) =>
          asNumber(cell.properties.metadata.elevation_max_m),
        ),
      )
    : 0;
  const isTerrainSelected = selected?.properties.asset_type === "terrain_cell";
  const isFloodExtentSelected =
    selected?.properties.asset_type === "historical_flood_extent";
  const selectedLandCoverPercentages =
    isTerrainSelected &&
    selected?.properties.metadata.land_cover_percentages &&
    typeof selected.properties.metadata.land_cover_percentages === "object"
      ? Object.entries(
          selected.properties.metadata.land_cover_percentages as Record<
            string,
            unknown
          >,
        )
          .map(([rawCode, rawPercentage]) => {
            const code = Number(rawCode);
            return {
              code,
              percentage: asNumber(rawPercentage),
              ...(LAND_COVER_CLASSES[code] ?? {
                name: landCoverLabel(code, t),
                color: "#888888",
              }),
              name: landCoverLabel(code, t),
            };
          })
          .sort((left, right) => right.percentage - left.percentage)
      : [];
  const mappedAssets = [
    ...assets.filter(
      (asset) => asset.properties.asset_type === "township_boundary",
    ),
    ...filteredSegments,
    ...floodExtents,
  ];
  const upcomingForecastHours =
    rainfallForecast?.hourly.filter(
      (hour) =>
        Date.parse(`${hour.time}+06:30`) >=
        Date.parse(rainfallForecast.fetched_at),
    ) ?? [];
  const next24HourRainMm = rainfallForecast
    ? upcomingForecastHours
        .slice(0, 24)
        .reduce((total, hour) => total + hour.precipitation_mm, 0)
    : null;
  const sevenDayRainMm =
    rainfallForecast?.daily.reduce(
      (total, day) => total + day.precipitation_sum_mm,
      0,
    ) ?? null;
  const peakRainProbability = rainfallForecast
    ? Math.max(
        0,
        ...upcomingForecastHours
          .slice(0, 24)
          .map((hour) => hour.probability_percent ?? 0),
      )
    : null;
  const latestWaterLevel = [...liveReadings]
    .filter((observation) => observation.properties.water_level_m !== null)
    .sort(
      (left, right) =>
        Date.parse(right.properties.observed_at) -
        Date.parse(left.properties.observed_at),
    )[0];
  const stationOptions = useMemo(() => {
    const options = new Map<string, string>();
    sensorStations.forEach((station) =>
      options.set(station.properties.station_id, station.properties.name),
    );
    liveReadings.forEach((reading) => {
      if (!options.has(reading.properties.station_id)) {
        options.set(
          reading.properties.station_id,
          reading.properties.station_name,
        );
      }
    });
    return [...options.entries()].map(([id, name]) => ({ id, name }));
  }, [liveReadings, sensorStations]);
  const selectedStation = sensorStations.find(
    (station) => station.properties.station_id === selectedStationId,
  );
  const selectedStationReadings = liveReadings.filter(
    (reading) => reading.properties.station_id === selectedStationId,
  );
  const selectedLatestReading = [...selectedStationReadings].sort(
    (left, right) =>
      Date.parse(right.properties.observed_at) -
      Date.parse(left.properties.observed_at),
  )[0];
  const highestOpenAlert = [...openAlerts].sort(
    (left, right) =>
      ["MEDIUM", "HIGH", "CRITICAL"].indexOf(right.risk_level) -
      ["MEDIUM", "HIGH", "CRITICAL"].indexOf(left.risk_level),
  )[0];
  const refresh = () => startRefresh(() => router.refresh());

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <div className={styles.brandMark}>
            <span />
            <span />
            <span />
          </div>
          <div>
            <p>{t("header.tagline")}</p>
            <h1>{t("header.title")}</h1>
          </div>
        </div>
        <div className={styles.headerContext}>
          <span className={styles.locationDot} />
          <div>
            <strong>{t("header.location")}</strong>
            <small>{t("header.region")}</small>
          </div>
        </div>
        <div className={styles.headerActions}>
          <LanguageSwitcher />
          <div
            className={`${styles.healthBadge} ${
              health?.database.status === "healthy"
                ? styles.healthOnline
                : styles.healthOffline
            }`}
          >
            <span />
            {health?.database.status === "healthy"
              ? t("header.spatialDbOnline")
              : t("header.apiOffline")}
          </div>
          <button
            className={styles.refreshButton}
            onClick={refresh}
            disabled={isRefreshing}
          >
            <MiniIcon name="refresh" />
            {isRefreshing ? t("common.refreshing") : t("common.refresh")}
          </button>
        </div>
      </header>

      <main className={styles.main}>
        {error ? (
          <section className={styles.errorBanner}>
            <div>
              <strong>{t("errors.backendUnavailable")}</strong>
              <p>{t("errors.backendHint", { error })}</p>
            </div>
            <code>python -m uvicorn app.main:app --reload</code>
          </section>
        ) : null}

        {highestOpenAlert ? (
          <section
            className={`${styles.alertBanner} ${
              highestOpenAlert.risk_level === "CRITICAL"
                ? styles.alertCritical
                : ""
            }`}
          >
            <div>
              <span>
                {t("alerts.thresholdAlert", {
                  level: highestOpenAlert.risk_level,
                })}
              </span>
              <strong>{highestOpenAlert.station_id}</strong>
            </div>
            <p>{highestOpenAlert.message}</p>
            <small>
              {formatDateTime(highestOpenAlert.created_at)} ·{" "}
              {openAlerts.length}{" "}
              {openAlerts.length === 1
                ? t("common.openAlert")
                : t("common.openAlerts")}
            </small>
          </section>
        ) : null}

        {!error ? (
          <section className={styles.demoBanner} aria-label="Demo status">
            <div>
              <strong>{t("demo.title")}</strong>
              <small>
                {t("demo.eventModel")}{" "}
                {floodEventMlPredictions?.model.model_version ??
                  "maubin-flood-event-logistic-v5"}{" "}
                · {t("demo.threshold")} {eventThresholdMode} (
                {floodEventMlPredictions?.model.decision_threshold?.toFixed(2) ??
                  "—"}
                ) · {t("demo.sarValidation")}{" "}
                {floodIntelligence?.sar_validation.status === "complete"
                  ? t("demo.ready")
                  : t("demo.pending")}
              </small>
            </div>
            <div className={styles.demoBannerActions}>
              <button
                type="button"
                className={`${styles.refreshButton} ${styles.demoForecastButton}`}
                onClick={() => void runForecast()}
                disabled={forecastLoading}
              >
                {forecastLoading
                  ? t("demo.runningForecast")
                  : t("demo.runForecast")}
              </button>
            </div>
          </section>
        ) : null}

        {!error && !floodMlPredictions ? (
          <p className={styles.demoWarn}>{t("demo.mlUnavailable")}</p>
        ) : null}

        {!error && !forecastPredictions ? (
          <p className={styles.demoWarn}>{t("demo.noForecast")}</p>
        ) : null}

        {eventEvaluation?.recommendation ? (
          <p className={styles.validationNote} style={{ marginBottom: 12 }}>
            <strong>{t("demo.modelLimitation")}</strong>{" "}
            {eventEvaluation.recommendation}
          </p>
        ) : null}

        <SituationOverview
          terrainCells={terrainCells}
          terrainScreening={terrainScreening}
          rainfallForecast={rainfallForecast}
          rainfallHistory={rainfallHistory}
          forecastPredictions={forecastPredictions}
          floodMlPredictions={floodMlPredictions}
          floodIntelligence={floodIntelligence}
        />

        <section className={styles.heroRow}>
          <div className={styles.intro}>
            <p className={styles.eyebrow}>{t("hero.eyebrow")}</p>
            <h2>
              {t("hero.titleLine1")}
              <br />
              <span>{t("hero.titleLine2")}</span>
            </h2>
            <p className={styles.introCopy}>{t("hero.intro")}</p>
          </div>
          <div className={styles.metricGrid}>
            <article className={styles.metricCard}>
              <div className={styles.metricIcon}>
                <MiniIcon name="layers" />
              </div>
              <p>{t("hero.terrainCells")}</p>
              <strong>{formatNumber(terrainCells.length)}</strong>
              <span>{t("hero.gridNote")}</span>
            </article>
            <article className={styles.metricCard}>
              <div className={styles.metricIcon}>
                <MiniIcon name="route" />
              </div>
              <p>{t("hero.elevationRange")}</p>
              <strong>
                {formatNumber(terrainMin, 1)}
                <small>
                  {" "}
                  {t("common.to")} {formatNumber(terrainMax, 1)} {t("common.m")}
                </small>
              </strong>
              <span>{t("hero.demSource")}</span>
            </article>
            <article className={styles.metricCard}>
              <div className={styles.metricIcon}>
                <MiniIcon name="river" />
              </div>
              <p>{t("hero.mappedWaterways")}</p>
              <strong>
                {formatNumber(totalLengthKm, 1)} {t("common.km")}
              </strong>
              <span>
                {t("hero.segmentCounts", {
                  rivers: riverSegments.length,
                  canals: canalSegments.length,
                })}
              </span>
            </article>
            <article className={`${styles.metricCard} ${styles.metricAccent}`}>
              <div className={styles.metricIcon}>
                <MiniIcon name="pulse" />
              </div>
              <p>{t("hero.veryHighScreening")}</p>
              <strong className={styles.statusValue}>
                {terrainScreening
                  ? `${formatNumber(
                      terrainScreening.summary.band_counts.VERY_HIGH,
                    )} ${t("common.cells")}`
                  : t("common.unavailable")}
              </strong>
              <span>{t("hero.susceptibilityNote")}</span>
            </article>
          </div>
        </section>

        <section className={styles.workspace}>
          <div className={styles.mapPanel}>
            <div className={styles.panelHeader}>
              <div>
                <p className={styles.eyebrow}>{t("map.eyebrow")}</p>
                <h3>{t("map.title")}</h3>
                <p className={styles.mapHint}>{t("map.hint")}</p>
              </div>
              <div className={styles.mapTools}>
                <div
                  className={styles.dimensionToggle}
                  aria-label={t("map.dimension")}
                >
                  <button
                    type="button"
                    className={mapView === "2d" ? styles.activeDimension : ""}
                    onClick={() => setMapView("2d")}
                  >
                    2D
                  </button>
                  <button
                    type="button"
                    className={
                      mapView === "cesium" ? styles.activeDimension : ""
                    }
                    onClick={() => setMapView("cesium")}
                  >
                    Cesium
                  </button>
                </div>
                <div className={styles.layerToggle}>
                  {(
                    [
                      "terrain",
                      "screening",
                      "ml_prediction",
                      "event_hindcast",
                      "forecast",
                      "landcover",
                      "network",
                      "validation",
                      "flood_history",
                    ] as const
                  ).map((layerKey) => {
                    const disabled =
                      (layerKey === "ml_prediction" &&
                        !floodMlPredictions?.items.length) ||
                      ((layerKey === "event_hindcast" ||
                        layerKey === "validation") &&
                        !floodEventMlPredictions?.items.length) ||
                      (layerKey === "forecast" &&
                        !forecastPredictions?.items.length) ||
                      (layerKey === "flood_history" &&
                        !floodExtents.length &&
                        !floodExtentsLoading);
                    const title =
                      layerKey === "ml_prediction"
                        ? floodMlPredictions
                          ? t("map.layerTitles.mlShow")
                          : t("map.layerTitles.mlTrain")
                        : layerKey === "event_hindcast"
                          ? t("map.layerTitles.hindcast")
                          : layerKey === "forecast"
                            ? forecastPredictions
                              ? t("map.layerTitles.forecastLive", {
                                  date: forecastPredictions.run.target_date,
                                })
                              : t("map.layerTitles.forecastRun")
                            : layerKey === "landcover"
                              ? t("map.layerTitles.landcover")
                              : layerKey === "validation"
                                ? t("map.layerTitles.validation")
                                : layerKey === "flood_history"
                                  ? floodExtents.length
                                    ? t("map.layerTitles.floodHistory")
                                    : floodExtentsLoading
                                      ? t("map.layerTitles.floodHistoryLoading")
                                      : floodExtentsLoadError
                                        ? floodExtentsLoadError
                                        : t("map.layerTitles.floodHistoryImport")
                                  : undefined;
                    return (
                      <button
                        key={layerKey}
                        className={
                          mapLayer === layerKey ? styles.activeFilter : ""
                        }
                        onClick={() => {
                          setMapLayer(layerKey);
                          if (layerKey === "ml_prediction") {
                            setSelectedId(highestMlCell?.id ?? null);
                          } else if (
                            layerKey === "event_hindcast" ||
                            layerKey === "validation"
                          ) {
                            setSelectedId(highestEventMlCell?.id ?? null);
                          } else if (layerKey === "forecast") {
                            setSelectedId(highestForecastCell?.id ?? null);
                          } else if (layerKey === "flood_history") {
                            setSelectedId(floodExtents[0]?.id ?? null);
                          }
                        }}
                        disabled={disabled}
                        title={title}
                      >
                        {t(`map.layers.${layerKey}`)}
                      </button>
                    );
                  })}
                </div>
                <div className={styles.legend}>
                  {mapLayer === "terrain" ? (
                    <>
                      <span>
                        <i className={styles.lowSwatch} /> {t("common.lower")}
                      </span>
                      <span>
                        <i className={styles.highSwatch} /> {t("common.higher")}
                      </span>
                    </>
                  ) : null}
                  {mapLayer === "screening" ? (
                    <>
                      <span>
                        <i className={styles.lowerRiskSwatch} /> {t("common.lower")}
                      </span>
                      <span>
                        <i className={styles.moderateRiskSwatch} /> {t("common.moderate")}
                      </span>
                      <span>
                        <i className={styles.highScreeningSwatch} /> {t("common.high")}
                      </span>
                      <span>
                        <i className={styles.highRiskSwatch} /> {t("common.veryHigh")}
                      </span>
                    </>
                  ) : null}
                  {mapLayer === "ml_prediction" ? (
                    <>
                      <span>
                        <i className={styles.lowerRiskSwatch} /> 0–24%
                      </span>
                      <span>
                        <i className={styles.moderateRiskSwatch} /> 25–49%
                      </span>
                      <span>
                        <i className={styles.highScreeningSwatch} /> 50–74%
                      </span>
                      <span>
                        <i className={styles.highRiskSwatch} /> 75–100%
                      </span>
                    </>
                  ) : null}
                  {mapLayer === "event_hindcast" ? (
                    <>
                      <span>
                        <i className={styles.lowerRiskSwatch} /> 0–24%
                      </span>
                      <span>
                        <i className={styles.moderateRiskSwatch} /> 25–49%
                      </span>
                      <span>
                        <i className={styles.highScreeningSwatch} /> 50–74%
                      </span>
                      <span>
                        <i className={styles.highRiskSwatch} /> 75–100%
                      </span>
                      <label className={styles.eventSelector}>
                        {t("map.historicalEvent")}
                        <select
                          value={floodEventMlPredictions?.event.event_id ?? ""}
                          disabled={eventHindcastLoading}
                          onChange={(event) =>
                            void selectEventHindcast(event.target.value)
                          }
                        >
                          {(
                            floodEventMlPredictions?.available_events ?? []
                          ).map((event) => (
                            <option key={event.event_id} value={event.event_id}>
                              {formatDate(event.event_start_date)} ·{" "}
                              {event.split} · #{event.event_id}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className={styles.eventSelector}>
                        {t("map.alertPolicy")}
                        <select
                          value={eventThresholdMode}
                          disabled={eventHindcastLoading}
                          onChange={(event) =>
                            void selectEventHindcast(
                              floodEventMlPredictions?.event.event_id ?? "",
                              event.target.value as
                                | "screening"
                                | "balanced"
                                | "conservative",
                            )
                          }
                        >
                          <option value="screening">
                            {t("map.screeningRecall")}
                          </option>
                          <option value="conservative">
                            {t("map.conservativeAlarms")}
                          </option>
                          <option value="balanced">{t("map.balancedF1")}</option>
                        </select>
                      </label>
                      <label className={styles.eventSelector}>
                        <span>{t("map.errorMap")}</span>
                        <select
                          value={showHindcastOutcomes ? "outcomes" : "probability"}
                          onChange={(event) =>
                            setShowHindcastOutcomes(
                              event.target.value === "outcomes",
                            )
                          }
                        >
                          <option value="probability">{t("map.probabilityColors")}</option>
                          <option value="outcomes">
                            {t("map.tpFpFn")}
                          </option>
                        </select>
                      </label>
                      {showHindcastOutcomes ? (
                        <>
                          <span>
                            <i style={{ background: "#2f80ed" }} /> TP
                          </span>
                          <span>
                            <i style={{ background: "#d64545" }} /> FP
                          </span>
                          <span>
                            <i style={{ background: "#f0a202" }} /> FN
                          </span>
                          <span>
                            <i style={{ background: "#6f8f86" }} /> TN
                          </span>
                        </>
                      ) : null}
                    </>
                  ) : null}
                  {mapLayer === "forecast" ? (
                    <>
                      <span>
                        <i className={styles.lowerRiskSwatch} /> 0–24%
                      </span>
                      <span>
                        <i className={styles.moderateRiskSwatch} /> 25–49%
                      </span>
                      <span>
                        <i className={styles.highScreeningSwatch} /> 50–74%
                      </span>
                      <span>
                        <i className={styles.highRiskSwatch} /> 75–100%
                      </span>
                      <label className={styles.eventSelector}>
                        {t("map.targetDate")}
                        <span style={{ fontSize: "0.85em", opacity: 0.8 }}>
                          {forecastPredictions?.run.target_date
                            ? formatDate(forecastPredictions.run.target_date)
                            : "—"}
                        </span>
                      </label>
                    </>
                  ) : null}
                  {mapLayer === "landcover" ? (
                    <>
                      <span>
                        <i style={{ background: "#f096ff" }} /> {t("map.cropland")}
                      </span>
                      <span>
                        <i style={{ background: "#fa0000" }} /> {t("map.builtUp")}
                      </span>
                      <span>
                        <i style={{ background: "#0064c8" }} /> {t("map.water")}
                      </span>
                      <span>
                        <i style={{ background: "#0096a0" }} /> {t("map.wetland")}
                      </span>
                    </>
                  ) : null}
                  {mapLayer === "validation" ? (
                    <>
                      <span>
                        <i style={{ background: "#d64545" }} /> {t("map.aiPredicted")}
                      </span>
                      <span>
                        <i style={{ background: "#2f80ed" }} /> {t("map.satelliteObserved")}
                      </span>
                      <span>
                        <i style={{ background: "#9b59f5" }} /> {t("map.overlap")}
                      </span>
                      <label className={styles.eventSelector}>
                        {t("map.historicalEvent")}
                        <select
                          value={floodEventMlPredictions?.event.event_id ?? ""}
                          disabled={eventHindcastLoading}
                          onChange={(event) =>
                            void selectEventHindcast(event.target.value)
                          }
                        >
                          {(
                            floodEventMlPredictions?.available_events ?? []
                          ).map((event) => (
                            <option key={event.event_id} value={event.event_id}>
                              {formatDate(event.event_start_date)} ·{" "}
                              {event.split} · #{event.event_id}
                            </option>
                          ))}
                        </select>
                      </label>
                    </>
                  ) : null}
                  {mapLayer === "flood_history" ? (
                    <>
                      <span>
                        <i style={{ background: "#8be6ff" }} /> {t("map.events1to2")}
                      </span>
                      <span>
                        <i style={{ background: "#4298e8" }} /> {t("map.events3to4")}
                      </span>
                      <span>
                        <i style={{ background: "#6d45c7" }} /> {t("map.events5to7")}
                      </span>
                      <span>
                        <i style={{ background: "#d72f8a" }} /> {t("map.events8plus")}
                      </span>
                    </>
                  ) : null}
                  <span>
                    <i className={styles.riverSwatch} /> {t("common.river")}
                  </span>
                </div>
              </div>
            </div>
            <div className={styles.mapStage}>
              {terrainLoading ? (
                <div className={styles.mapDataStatus}>
                  <i />
                  {t("map.loadingDem")}
                </div>
              ) : terrainLoadError ? (
                <div
                  className={`${styles.mapDataStatus} ${styles.mapDataError}`}
                >
                  {terrainLoadError}
                </div>
              ) : floodExtentsLoading && mapLayer === "flood_history" ? (
                <div className={styles.mapDataStatus}>
                  <i />
                  Loading historical flood labels…
                </div>
              ) : floodExtentsLoadError && mapLayer === "flood_history" ? (
                <div
                  className={`${styles.mapDataStatus} ${styles.mapDataError}`}
                >
                  {floodExtentsLoadError}
                </div>
              ) : null}
              {mapView === "cesium" ? (
                <InteractiveMapCesium
                  key="map-view-cesium"
                  assets={mappedAssets}
                  terrainCells={terrainCells}
                  screeningById={terrainScreeningById}
                  predictionById={activePredictionById}
                  layer={mapLayer}
                  selectedId={selected?.id ?? null}
                  onSelect={(asset) => setSelectedId(asset.id)}
                  showHindcastOutcomes={showHindcastOutcomes}
                  sensorStations={sensorStations}
                />
              ) : mapView === "3d" ? (
                <InteractiveMap3D
                  key="map-view-3d"
                  assets={mappedAssets}
                  terrainCells={terrainCells}
                  screeningById={terrainScreeningById}
                  predictionById={activePredictionById}
                  layer={mapLayer}
                  selectedId={selected?.id ?? null}
                  onSelect={(asset) => setSelectedId(asset.id)}
                  showHindcastOutcomes={showHindcastOutcomes}
                />
              ) : (
                <InteractiveMap
                  key="map-view-2d"
                  assets={mappedAssets}
                  terrainCells={terrainCells}
                  screeningById={terrainScreeningById}
                  predictionById={activePredictionById}
                  layer={mapLayer}
                  selectedId={selected?.id ?? null}
                  onSelect={(asset) => setSelectedId(asset.id)}
                  showHindcastOutcomes={showHindcastOutcomes}
                />
              )}
              <div className={styles.mapCounter}>
                <strong>
                  {mapLayer !== "network"
                    ? mapLayer === "flood_history"
                      ? formatNumber(floodExtents.length)
                      : formatNumber(terrainCells.length)
                    : filteredSegments.length}
                </strong>
                <span>
                  {mapLayer === "screening"
                    ? "screened cells"
                    : mapLayer === "ml_prediction"
                      ? "ML-scored cells"
                      : mapLayer === "event_hindcast"
                        ? "hindcast cells"
                        : mapLayer === "validation"
                          ? "validation cells"
                        : mapLayer === "forecast"
                          ? "forecast cells"
                        : mapLayer === "landcover"
                          ? "land-cover cells"
                          : mapLayer === "terrain"
                            ? "terrain cells"
                            : mapLayer === "flood_history"
                              ? "historical extents"
                              : "visible segments"}
                </span>
                {mapView === "cesium" ? (
                  <small>Cesium globe · streamed terrain</small>
                ) : mapView === "3d" ? (
                  <small>3D terrain · exaggerated relief</small>
                ) : mapLayer === "screening" ? (
                  <small>Relative ranking · not arrival order</small>
                ) : mapLayer === "ml_prediction" ? (
                  <small>
                    Historical baseline · test ROC-AUC{" "}
                    {formatNumber(asNumber(mlTestMetrics?.roc_auc), 2)} · not a
                    live forecast
                  </small>
                ) : mapLayer === "event_hindcast" ? (
                  <small>
                    Event #{floodEventMlPredictions?.event.event_id ?? "—"} ·{" "}
                    {floodEventMlPredictions?.event.event_start_date
                      ? formatDate(
                          floodEventMlPredictions.event.event_start_date,
                        )
                      : "—"}{" "}
                    · historical test only
                  </small>
                ) : mapLayer === "forecast" ? (
                  <small>
                    {forecastPredictions?.run.target_date
                      ? formatDate(forecastPredictions.run.target_date)
                      : "—"}{" "}
                    · {forecastPredictions?.run.threshold_mode ?? "balanced"}{" "}
                    · {formatNumber(forecastPredictions?.run.flagged_cell_count ?? 0)} flagged
                    · experimental
                  </small>
                ) : mapLayer === "validation" ? (
                  <small>
                    AI vs MODIS GFD observed · event #
                    {floodEventMlPredictions?.event.event_id ?? "—"} · overlap
                    view
                  </small>
                ) : mapLayer === "landcover" ? (
                  <small>
                    {landCoverSummary?.status === "available"
                      ? "ESA WorldCover 2021 · 10 m source"
                      : "Land-cover import pending"}
                  </small>
                ) : mapLayer === "flood_history" ? (
                  <small>Satellite observation · training label</small>
                ) : null}
              </div>
            </div>
          </div>

          <aside className={styles.detailPanel}>
            <div className={styles.panelHeader}>
              <div>
                <p className={styles.eyebrow}>Spatial inspector</p>
                <h3>
                  {isTerrainSelected
                    ? "Selected terrain"
                    : isFloodExtentSelected
                      ? "Historical flood label"
                      : "Selected segment"}
                </h3>
              </div>
              <span className={styles.pendingPill}>
                {isTerrainSelected && selectedScreening
                  ? mapLayer === "ml_prediction" && selectedMlPrediction
                    ? `${selectedMlPrediction.risk_band} · historical ML`
                    : mapLayer === "event_hindcast" && selectedEventMlPrediction
                      ? `${selectedEventMlPrediction.predicted_label ? "FLAGGED" : "NOT FLAGGED"} · hindcast`
                      : mapLayer === "forecast" && selectedForecastPrediction
                        ? `${selectedForecastPrediction.risk_band.replaceAll("_", " ")} · forecast`
                        : `${selectedScreening.screening_band} relative`
                  : isTerrainSelected
                    ? "Screening unavailable"
                    : isFloodExtentSelected
                      ? "Observed · not predicted"
                      : "Unscored"}
              </span>
            </div>
            {selected ? (
              <div className={styles.detailBody}>
                <div className={styles.detailTitle}>
                  <span
                    className={
                      isTerrainSelected
                        ? styles.terrainDot
                        : isFloodExtentSelected
                          ? styles.floodDot
                          : selected.properties.asset_type === "river_segment"
                            ? styles.riverDot
                            : styles.canalDot
                    }
                  />
                  <div>
                    <h4>
                      {isTerrainSelected
                        ? "500 m terrain cell"
                        : selected.properties.name}
                    </h4>
                    <p>{localizedAssetLabel(selected.properties.asset_type, t)} asset</p>
                  </div>
                </div>
                {isTerrainSelected ? (
                  <dl className={styles.detailGrid}>
                    {mapLayer === "ml_prediction" && selectedMlPrediction ? (
                      <>
                        <div>
                          <dt>ML probability</dt>
                          <dd>
                            {formatNumber(
                              selectedMlPrediction.probability * 100,
                              1,
                            )}
                            %
                          </dd>
                        </div>
                        <div>
                          <dt>Risk band</dt>
                          <dd>
                            {selectedMlPrediction.risk_band.replaceAll(
                              "_",
                              " ",
                            )}
                          </dd>
                        </div>
                        <div>
                          <dt>Historical flooded</dt>
                          <dd>
                            {formatNumber(
                              selectedMlPrediction.flooded_fraction * 100,
                              1,
                            )}
                            %
                          </dd>
                        </div>
                        <div>
                          <dt>Observed events</dt>
                          <dd>
                            {formatNumber(
                              selectedMlPrediction.historical_event_count,
                            )}
                          </dd>
                        </div>
                        <div>
                          <dt>Model test F1</dt>
                          <dd>
                            {formatNumber(asNumber(mlTestMetrics?.f1), 3)}
                          </dd>
                        </div>
                        <div>
                          <dt>Model version</dt>
                          <dd>
                            {floodMlPredictions?.model.model_version ?? "—"}
                          </dd>
                        </div>
                      </>
                    ) : null}
                    {mapLayer === "event_hindcast" &&
                    selectedEventMlPrediction ? (
                      <>
                        <div>
                          <dt>Hindcast probability</dt>
                          <dd>
                            {formatNumber(
                              selectedEventMlPrediction.probability * 100,
                              1,
                            )}
                            %
                          </dd>
                        </div>
                        <div>
                          <dt>Decision threshold</dt>
                          <dd>
                            {formatNumber(
                              (floodEventMlPredictions?.model
                                .decision_threshold ?? 0) * 100,
                              0,
                            )}
                            %
                          </dd>
                        </div>
                        <div>
                          <dt>Outcome</dt>
                          <dd>
                            {selectedEventMlPrediction.outcome?.toUpperCase() ??
                              "—"}
                          </dd>
                        </div>
                        <div>
                          <dt>Observed flooded</dt>
                          <dd>
                            {formatNumber(
                              selectedEventMlPrediction.flooded_fraction * 100,
                              1,
                            )}
                            %
                          </dd>
                        </div>
                        <div>
                          <dt>Historical event</dt>
                          <dd>
                            #{floodEventMlPredictions?.event.event_id ?? "—"}
                          </dd>
                        </div>
                        <div>
                          <dt>Test ROC-AUC</dt>
                          <dd>
                            {formatNumber(
                              asNumber(eventMlTestMetrics?.roc_auc),
                              3,
                            )}
                          </dd>
                        </div>
                        <div>
                          <dt>Event precision / recall</dt>
                          <dd>
                            {formatNumber(
                              (floodEventMlPredictions?.summary.precision ?? 0) *
                                100,
                              1,
                            )}
                            % /{" "}
                            {formatNumber(
                              (floodEventMlPredictions?.summary.recall ?? 0) *
                                100,
                              1,
                            )}
                            %
                          </dd>
                        </div>
                        <div>
                          <dt>False alarms</dt>
                          <dd>
                            {formatNumber(
                              floodEventMlPredictions?.summary
                                .false_positive_cells ?? 0,
                            )}
                          </dd>
                        </div>
                        <div>
                          <dt>Rolling CV precision</dt>
                          <dd>
                            {typeof rollingConservative?.mean_precision ===
                            "number"
                              ? `${formatNumber(
                                  rollingConservative.mean_precision * 100,
                                  1,
                                )}%`
                              : "—"}
                          </dd>
                        </div>
                        <div>
                          <dt>Model version</dt>
                          <dd>
                            {floodEventMlPredictions?.model.model_version ??
                              "—"}
                          </dd>
                        </div>
                        {eventEvaluation?.recommendation ? (
                          <div>
                            <dt>Evaluation note</dt>
                            <dd>{eventEvaluation.recommendation}</dd>
                          </div>
                        ) : null}
                        <div>
                          <dt>Status</dt>
                          <dd>Experimental hindcast</dd>
                        </div>
                      </>
                    ) : null}
                    {mapLayer === "forecast" &&
                    selectedForecastPrediction ? (
                      <>
                        <div>
                          <dt>Forecast probability</dt>
                          <dd>
                            {formatNumber(
                              selectedForecastPrediction.probability * 100,
                              1,
                            )}
                            %
                          </dd>
                        </div>
                        <div>
                          <dt>Risk band</dt>
                          <dd>
                            {selectedForecastPrediction.risk_band.replaceAll(
                              "_",
                              " ",
                            )}
                          </dd>
                        </div>
                        <div>
                          <dt>Decision threshold</dt>
                          <dd>
                            {formatNumber(
                              (forecastPredictions?.run
                                .decision_threshold ?? 0) * 100,
                              0,
                            )}
                            %
                          </dd>
                        </div>
                        <div>
                          <dt>Target date</dt>
                          <dd>
                            {forecastPredictions?.run.target_date
                              ? formatDate(forecastPredictions.run.target_date)
                              : "—"}
                          </dd>
                        </div>
                        <div>
                          <dt>Flagged / total</dt>
                          <dd>
                            {formatNumber(
                              forecastPredictions?.run.flagged_cell_count ?? 0,
                            )}
                            {" / "}
                            {formatNumber(
                              forecastPredictions?.run.cell_count ?? 0,
                            )}
                          </dd>
                        </div>
                        <div>
                          <dt>Model version</dt>
                          <dd>
                            {forecastPredictions?.run.model_version ?? "—"}
                          </dd>
                        </div>
                        <div>
                          <dt>Rainfall source</dt>
                          <dd>
                            {forecastPredictions?.run.rainfall_source ?? "—"}
                          </dd>
                        </div>
                        <div>
                          <dt>Status</dt>
                          <dd>Experimental forecast</dd>
                        </div>
                      </>
                    ) : null}
                    <div>
                      <dt>Mean elevation</dt>
                      <dd>
                        {formatNumber(
                          asNumber(
                            selected.properties.metadata.elevation_mean_m,
                          ),
                          1,
                        )}{" "}
                        m
                      </dd>
                    </div>
                    <div>
                      <dt>Min / max</dt>
                      <dd>
                        {formatNumber(
                          asNumber(
                            selected.properties.metadata.elevation_min_m,
                          ),
                          1,
                        )}{" "}
                        /{" "}
                        {formatNumber(
                          asNumber(
                            selected.properties.metadata.elevation_max_m,
                          ),
                          1,
                        )}{" "}
                        m
                      </dd>
                    </div>
                    <div>
                      <dt>Elevation percentile</dt>
                      <dd>
                        {formatNumber(
                          asNumber(
                            selected.properties.metadata.elevation_percentile,
                          ),
                        )}
                        %
                      </dd>
                    </div>
                    <div>
                      <dt>Nearest waterway</dt>
                      <dd>
                        {formatNumber(
                          asNumber(
                            selected.properties.metadata.distance_to_waterway_m,
                          ),
                        )}{" "}
                        m
                      </dd>
                    </div>
                    <div>
                      <dt>Local relief</dt>
                      <dd>
                        {formatNumber(
                          asNumber(selected.properties.metadata.local_relief_m),
                          1,
                        )}{" "}
                        m
                      </dd>
                    </div>
                    <div>
                      <dt>DEM samples</dt>
                      <dd>
                        {formatNumber(
                          asNumber(selected.properties.metadata.sample_count),
                        )}
                      </dd>
                    </div>
                  </dl>
                ) : isFloodExtentSelected ? (
                  <dl className={styles.detailGrid}>
                    <div>
                      <dt>Observed events</dt>
                      <dd>
                        {formatNumber(
                          asNumber(selected.properties.metadata.event_count),
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt>Dataset through</dt>
                      <dd>
                        {formatDate(
                          String(selected.properties.metadata.observed_date),
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt>Mapped area</dt>
                      <dd>
                        {formatNumber(
                          asNumber(selected.properties.metadata.area_km2),
                          2,
                        )}{" "}
                        km²
                      </dd>
                    </div>
                    <div>
                      <dt>Satellite sensor</dt>
                      <dd>
                        {String(selected.properties.metadata.sensor ?? "—")}
                      </dd>
                    </div>
                    <div>
                      <dt>Confidence</dt>
                      <dd>
                        {String(
                          selected.properties.metadata.confidence ?? "unknown",
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt>Source</dt>
                      <dd>
                        {String(
                          selected.properties.metadata.source_name ?? "—",
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt>Field validated</dt>
                      <dd>
                        {selected.properties.metadata.field_validated
                          ? "Yes"
                          : "No"}
                      </dd>
                    </div>
                  </dl>
                ) : (
                  <dl className={styles.detailGrid}>
                    <div>
                      <dt>Segment length</dt>
                      <dd>
                        {formatNumber(
                          asNumber(
                            selected.properties.metadata.segment_length_m,
                          ),
                        )}{" "}
                        m
                      </dd>
                    </div>
                    <div>
                      <dt>OSM source</dt>
                      <dd>
                        {String(selected.properties.metadata.osm_id ?? "—")}
                      </dd>
                    </div>
                    <div>
                      <dt>Sequence</dt>
                      <dd>
                        #
                        {String(
                          selected.properties.metadata.segment_index ?? "—",
                        ).padStart(3, "0")}
                      </dd>
                    </div>
                    <div>
                      <dt>Human review</dt>
                      <dd>Not started</dd>
                    </div>
                  </dl>
                )}
                {isTerrainSelected &&
                selectedLandCoverPercentages.length > 0 ? (
                  <div className={styles.landCoverCard}>
                    <div className={styles.landCoverHeader}>
                      <div>
                        <span>ESA WorldCover 2021</span>
                        <strong>
                          {String(
                            selected.properties.metadata
                              .land_cover_dominant_name ?? "Land cover",
                          )}
                        </strong>
                      </div>
                      <small>10 m source → 500 m cell</small>
                    </div>
                    <div className={styles.landCoverBreakdown}>
                      {selectedLandCoverPercentages.slice(0, 5).map((item) => (
                        <div key={item.code}>
                          <span>
                            <i style={{ backgroundColor: item.color }} />
                            {item.name}
                          </span>
                          <strong>{formatNumber(item.percentage, 1)}%</strong>
                          <b>
                            <i
                              style={{
                                width: `${Math.min(100, item.percentage)}%`,
                                backgroundColor: item.color,
                              }}
                            />
                          </b>
                        </div>
                      ))}
                    </div>
                    <p>
                      Descriptive 2021 land cover. It is not live flood water
                      and is not yet weighted in the susceptibility score.
                    </p>
                  </div>
                ) : null}
                {isTerrainSelected ? (
                  <FloodExplainability
                    cell={selected}
                    mapLayer={mapLayer}
                    screening={selectedScreening}
                    mlPrediction={selectedMlPrediction}
                    forecastPrediction={selectedForecastPrediction}
                    rainfallHistory={rainfallHistory}
                    probabilityOverride={
                      mapLayer === "event_hindcast" || mapLayer === "validation"
                        ? selectedEventMlPrediction?.probability
                        : undefined
                    }
                  />
                ) : null}
                {isTerrainSelected && selectedScreening ? (
                  <div className={styles.screeningCard}>
                    <div className={styles.screeningScore}>
                      <div>
                        <span>Relative susceptibility</span>
                        <small>
                          {selectedScreening.screening_band.replaceAll(
                            "_",
                            " ",
                          )}
                        </small>
                      </div>
                      <strong>
                        {formatNumber(selectedScreening.screening_score, 1)}
                        <small>/100</small>
                      </strong>
                    </div>
                    <div className={styles.factorList}>
                      {selectedScreeningFactors.map((factor) => (
                        <div key={factor.key}>
                          <span>
                            {factor.label}
                            <small>{Math.round(factor.weight * 100)}%</small>
                          </span>
                          <i>
                            <b
                              style={{
                                width: `${factor.normalizedScore}%`,
                              }}
                            />
                          </i>
                          <p>
                            {formatNumber(factor.observedValue, 1)}{" "}
                            {factor.unit} · +
                            {formatNumber(
                              factor.normalizedScore * factor.weight,
                              1,
                            )}
                          </p>
                        </div>
                      ))}
                    </div>
                    <p className={styles.screeningLimit}>
                      Relative terrain screening only—not flood probability,
                      depth, or arrival time. Field verification, rainfall,
                      drainage, levees, tides, and river stage are still
                      required.
                    </p>
                  </div>
                ) : (
                  <div className={styles.modelPlaceholder}>
                    <div>
                      <span>Flood prediction</span>
                      <strong>—</strong>
                    </div>
                    <p>
                      Terrain alone cannot determine flood depth or arrival
                      time. Rainfall, river levels, connectivity, and
                      calibration are still required.
                    </p>
                  </div>
                )}
                <div className={styles.assetId}>
                  <span>{t("map.geoAssetUuid")}</span>
                  <code>{selected.id}</code>
                </div>
              </div>
            ) : (
              <div className={styles.noSelection}>
                {t("map.noSelection")}
              </div>
            )}
          </aside>
        </section>

        <ValidationPanel
          predictions={floodEventMlPredictions}
          floodIntelligence={floodIntelligence}
          loading={eventHindcastLoading}
        />

        <section className={styles.hydromet}>
          <div className={styles.hydrometIntro}>
            <p className={styles.eyebrow}>{t("hydromet.eyebrow")}</p>
            <h3>{t("hydromet.title")}</h3>
            <p>{t("hydromet.intro")}</p>
          </div>
          <div className={styles.hydrometGrid}>
            <article>
              <span>{t("hydromet.next24h")}</span>
              <strong>
                {next24HourRainMm === null
                  ? t("common.unavailable")
                  : `${formatNumber(next24HourRainMm, 1)} ${t("common.mm")}`}
              </strong>
              <small>{t("hydromet.forecastPrecip")}</small>
            </article>
            <article>
              <span>{t("hydromet.sevenDayOutlook")}</span>
              <strong>
                {sevenDayRainMm === null
                  ? t("common.unavailable")
                  : `${formatNumber(sevenDayRainMm, 1)} ${t("common.mm")}`}
              </strong>
              <small>
                {peakRainProbability === null
                  ? t("hydromet.providerUnavailable")
                  : t("hydromet.peakProbability", {
                      value: peakRainProbability,
                    })}
              </small>
            </article>
            <article>
              <span>{t("hydromet.gaugeStations")}</span>
              <strong>
                {sensorStations.length
                  ? t("hydromet.registered", {
                      count: formatNumber(sensorStations.length),
                    })
                  : t("hydromet.awaitingRegistration")}
              </strong>
              <small>
                {latestWaterLevel
                  ? t("hydromet.stationReading", {
                      name: latestWaterLevel.properties.station_name,
                      level: formatNumber(
                        latestWaterLevel.properties.water_level_m ?? 0,
                        2,
                      ),
                      time: formatDateTime(
                        latestWaterLevel.properties.observed_at,
                      ),
                      quality: latestWaterLevel.properties.quality_status,
                    })
                  : sensorStations.length
                    ? t("hydromet.noReadingYet")
                    : t("hydromet.registerGauge")}
              </small>
            </article>
            <article className={styles.hydrometSource}>
              <span>{t("hydromet.dataIntegrity")}</span>
              <strong>
                {rainfallForecast
                  ? t("hydromet.forecastConnected")
                  : t("hydromet.forecastOffline")}
              </strong>
              <small>
                {rainfallForecast
                  ? t("hydromet.cachedFresh", {
                      source: rainfallForecast.source,
                      status: rainfallForecast.cached
                        ? t("hydromet.cached")
                        : t("hydromet.fresh"),
                    })
                  : t("hydromet.refreshProvider")}
              </small>
            </article>
            <article>
              <span>{t("hydromet.thresholdAlerts")}</span>
              <strong>
                {openAlerts.length
                  ? t("hydromet.openCount", { count: openAlerts.length })
                  : t("hydromet.noAlertRecords")}
              </strong>
              <small>
                {highestOpenAlert
                  ? `${highestOpenAlert.risk_level} · ${highestOpenAlert.station_id}`
                  : sensorStations.length
                    ? t("hydromet.noThresholdCrossing")
                    : t("hydromet.needStation")}
              </small>
            </article>
          </div>
        </section>

        <RainfallHistoryChart history={rainfallHistory} />

        <section className={styles.liveMonitor}>
          <div className={styles.liveMonitorHeader}>
            <div>
              <p className={styles.eyebrow}>{t("liveMonitor.eyebrow")}</p>
              <h3>{t("liveMonitor.title")}</h3>
            </div>
            <div className={styles.liveControls}>
              <span
                className={`${styles.liveStatus} ${
                  mqttStatus?.status === "connected"
                    ? styles.liveConnected
                    : styles.liveDisconnected
                }`}
                title={mqttStatus?.last_error ?? mqttStatus?.topic}
              >
                <i />
                {!mqttStatus
                  ? t("liveMonitor.mqttUnavailable")
                  : mqttStatus.status === "disabled"
                    ? t("liveMonitor.mqttDisabled")
                    : mqttStatus.status === "connected"
                      ? t("liveMonitor.mqttConnected", {
                          count: mqttStatus.messages_received,
                        })
                      : `MQTT ${mqttStatus.status}`}
              </span>
              <span
                className={`${styles.liveStatus} ${
                  liveConnection === "connected"
                    ? styles.liveConnected
                    : styles.liveDisconnected
                }`}
              >
                <i />
                {liveConnection === "connected"
                  ? t("liveMonitor.liveConnected")
                  : liveConnection === "connecting"
                    ? t("liveMonitor.connecting")
                    : t("liveMonitor.reconnecting")}
              </span>
              <label>
                <span>{t("liveMonitor.station")}</span>
                <select
                  value={selectedStationId}
                  onChange={(event) => setSelectedStationId(event.target.value)}
                  disabled={!stationOptions.length}
                >
                  {!stationOptions.length ? (
                    <option value="">{t("liveMonitor.noRegisteredStation")}</option>
                  ) : null}
                  {stationOptions.map((station) => (
                    <option key={station.id} value={station.id}>
                      {station.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>
          <div className={styles.liveChartBody}>
            <WaterLevelChart
              readings={selectedStationReadings}
              station={selectedStation}
            />
            <aside className={styles.liveReadingSummary}>
              <span>{t("liveMonitor.latestInput")}</span>
              <strong>
                {selectedLatestReading?.properties.water_level_m === null ||
                selectedLatestReading?.properties.water_level_m === undefined
                  ? "—"
                  : `${formatNumber(
                      selectedLatestReading.properties.water_level_m * 100,
                      1,
                    )} ${t("common.cm")}`}
              </strong>
              <dl>
                <div>
                  <dt>{t("liveMonitor.observed")}</dt>
                  <dd>
                    {selectedLatestReading
                      ? formatDateTime(
                          selectedLatestReading.properties.observed_at,
                        )
                      : t("common.noReading")}
                  </dd>
                </div>
                <div>
                  <dt>{t("liveMonitor.quality")}</dt>
                  <dd>
                    {selectedLatestReading?.properties.quality_status ??
                      t("common.unavailable")}
                  </dd>
                </div>
                <div>
                  <dt>{t("liveMonitor.source")}</dt>
                  <dd>{selectedLatestReading?.properties.source ?? "—"}</dd>
                </div>
                <div>
                  <dt>{t("liveMonitor.battery")}</dt>
                  <dd>
                    {selectedLatestReading?.properties.battery_percent ===
                      null ||
                    selectedLatestReading?.properties.battery_percent ===
                      undefined
                      ? "—"
                      : `${formatNumber(
                          selectedLatestReading.properties.battery_percent,
                        )}%`}
                  </dd>
                </div>
              </dl>
              <p>{t("liveMonitor.chartNote")}</p>
            </aside>
          </div>
        </section>

        <section className={styles.dataCatalog}>
          <div className={styles.dataCatalogHeader}>
            <div>
              <p className={styles.eyebrow}>{t("dataCatalog.eyebrow")}</p>
              <h3>{t("dataCatalog.title")}</h3>
              <p>{t("dataCatalog.intro")}</p>
            </div>
            <div className={styles.catalogSummary}>
              <strong>{dataLayers.length}</strong>
              <span>{t("dataCatalog.activeLayers")}</span>
              <small>
                {
                  dataLayers.filter(
                    (layer) => layer.properties.quality_status === "verified",
                  ).length
                }{" "}
                {t("common.verified")} ·{" "}
                {
                  dataLayers.filter(
                    (layer) => layer.properties.quality_status === "limited",
                  ).length
                }{" "}
                {t("common.limited")}
              </small>
            </div>
          </div>
          <div className={styles.dataLayerGrid}>
            {dataLayers.map((layer) => (
              <article key={layer.id}>
                <div className={styles.dataLayerTop}>
                  <span>{layer.properties.category.replaceAll("_", " ")}</span>
                  <i
                    className={
                      layer.properties.quality_status === "verified"
                        ? styles.qualityVerified
                        : styles.qualityLimited
                    }
                  >
                    {layer.properties.quality_status}
                  </i>
                </div>
                <h4>{layer.properties.name}</h4>
                <p className={styles.dataProvider}>
                  {layer.properties.provider} · {layer.properties.data_kind}
                  {layer.properties.spatial_resolution_m
                    ? ` · ${formatNumber(
                        layer.properties.spatial_resolution_m,
                      )} m`
                    : ""}
                </p>
                <p className={styles.dataQualityNotes}>
                  {layer.properties.quality_notes}
                </p>
                {layer.properties.usage_constraints ? (
                  <p className={styles.usageConstraint}>
                    <strong>{t("dataCatalog.usageConstraint")}</strong>
                    {layer.properties.usage_constraints}
                  </p>
                ) : null}
                <div className={styles.dataLayerLinks}>
                  <a
                    href={layer.properties.source_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t("common.source")}
                  </a>
                  {layer.properties.license_url ? (
                    <a
                      href={layer.properties.license_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {t("common.licence")}
                    </a>
                  ) : null}
                  <code>{layer.properties.layer_key}</code>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.inventory}>
          <div className={styles.inventoryTop}>
            <div>
              <p className={styles.eyebrow}>{t("inventory.eyebrow")}</p>
              <h3>{t("inventory.title")}</h3>
            </div>
            <div className={styles.controls}>
              <div className={styles.filterGroup}>
                {(
                  [
                    ["all", t("common.all")],
                    ["river_segment", t("common.rivers")],
                    ["canal_segment", t("common.canals")],
                  ] as const
                ).map(([value, label]) => (
                  <button
                    key={value}
                    className={filter === value ? styles.activeFilter : ""}
                    onClick={() => setFilter(value)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <label className={styles.searchBox}>
                <MiniIcon name="search" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={t("inventory.searchPlaceholder")}
                />
              </label>
            </div>
          </div>
          <div className={styles.segmentList}>
            {filteredSegments.slice(0, 12).map((asset) => (
              <button
                key={asset.id}
                className={
                  selected?.id === asset.id ? styles.activeListItem : ""
                }
                onClick={() => setSelectedId(asset.id)}
              >
                <span
                  className={
                    asset.properties.asset_type === "river_segment"
                      ? styles.riverBar
                      : styles.canalBar
                  }
                />
                <div>
                  <strong>{asset.properties.name}</strong>
                  <small>
                    {String(asset.properties.metadata.osm_id ?? "OSM source")}
                  </small>
                </div>
                <span className={styles.listLength}>
                  {formatNumber(
                    asNumber(asset.properties.metadata.segment_length_m),
                  )}{" "}
                  m
                </span>
              </button>
            ))}
          </div>
          {filteredSegments.length > 12 ? (
            <p className={styles.listNote}>
              {t("inventory.showingSegments", {
                total: filteredSegments.length,
              })}
            </p>
          ) : null}
        </section>

        <section className={styles.readiness}>
          <div>
            <p className={styles.eyebrow}>{t("readiness.eyebrow")}</p>
            <h3>{t("readiness.title")}</h3>
          </div>
          <div className={styles.readinessSteps}>
            <article className={styles.stepComplete}>
              <span>01</span>
              <div>
                <strong>{t("readiness.terrainBaseline")}</strong>
                <p>{t("readiness.terrainComplete")}</p>
              </div>
            </article>
            <article
              className={
                rainfallForecast && latestObservations.length
                  ? styles.stepComplete
                  : ""
              }
            >
              <span>02</span>
              <div>
                <strong>{t("readiness.hydrometeorology")}</strong>
                <p>
                  {rainfallForecast
                    ? t("readiness.hydrometConnected")
                    : t("readiness.hydrometRequired")}
                </p>
              </div>
            </article>
            <article>
              <span>03</span>
              <div>
                <strong>{t("readiness.calibratedModel")}</strong>
                <p>{t("readiness.calibratedRequired")}</p>
              </div>
            </article>
          </div>
        </section>
      </main>

      <footer className={styles.footer}>
        <span>{t("footer.attribution")}</span>
        <span>{t("footer.disclaimer")}</span>
      </footer>
    </div>
  );
}
