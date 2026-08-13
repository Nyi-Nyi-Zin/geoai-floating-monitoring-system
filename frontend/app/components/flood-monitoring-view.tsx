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
  ForecastPredictionIndex,
  GeoAsset,
  TerrainScreeningIndex,
  TerrainScreeningIndexItem,
} from "@/lib/api";
import { fetchFloodExtents } from "@/lib/flood-extents";
import LanguageSwitcher from "./language-switcher";
import CellDetailModal from "./cell-detail-modal";
import type {
  BasemapMode,
  FloodMonitoringMapHandle,
  LayerVisibility,
} from "./flood-monitoring-map.types";
import { MapLoading2D } from "./map-loading-fallbacks";
import styles from "./flood-monitoring-view.module.css";
import { useTranslation } from "@/lib/i18n";
import { PROBABILITY_GRADIENT_CSS } from "@/lib/probability-surface";

type MapLayer = "screening" | "forecast" | "ml_prediction";

const FloodMonitoringMap = dynamic(() => import("./flood-monitoring-map"), {
  ssr: false,
  loading: MapLoading2D,
});

const LAND_COVER_LEGEND = [
  { color: "#fa0000", label: "Built-up" },
  { color: "#f096ff", label: "Cropland" },
  { color: "#ffff4c", label: "Grassland" },
  { color: "#006400", label: "Tree cover" },
  { color: "#0064c8", label: "Water" },
  { color: "#0096a0", label: "Wetland" },
] as const;

function asNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function isRoadAsset(asset: GeoAsset) {
  return (
    asset.properties.asset_type === "road_segment" ||
    asset.properties.asset_type.includes("road")
  );
}

function Icon({
  name,
}: {
  name: "bell" | "menu" | "plus" | "minus" | "layers" | "locate" | "refresh";
}) {
  if (name === "bell") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M18 8a6 6 0 10-12 0c0 7-3 7-3 7h18s-3 0-3-7" />
        <path d="M13.7 21a2 2 0 01-3.4 0" />
      </svg>
    );
  }
  if (name === "menu") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M4 7h16M4 12h16M4 17h16" />
      </svg>
    );
  }
  if (name === "plus") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 5v14M5 12h14" />
      </svg>
    );
  }
  if (name === "minus") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M5 12h14" />
      </svg>
    );
  }
  if (name === "layers") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M12 2l9 5-9 5-9-5 9-5z" />
        <path d="M3 12l9 5 9-5" />
        <path d="M3 17l9 5 9-5" />
      </svg>
    );
  }
  if (name === "refresh") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M21 12a9 9 0 10-2.64 6.36" />
        <path d="M21 3v6h-6" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
    </svg>
  );
}

export default function FloodMonitoringView({
  assets,
  terrainCells: initialTerrainCells,
  terrainScreening: initialTerrainScreening,
  health,
  rainfallForecast,
  rainfallHistory,
  floodExtents: initialFloodExtents,
  floodMlPredictions,
  forecastPredictions: initialForecastPredictions,
  floodIntelligence,
  sensorStations,
  latestObservations,
  openAlerts,
  spatialApiUrl,
  error,
}: DashboardData) {
  const router = useRouter();
  const { t, formatNumber, formatDateTime } = useTranslation();
  const [isRefreshing, startRefresh] = useTransition();
  const mapRef = useRef<FloodMonitoringMapHandle>(null);
  const [basemapMode, setBasemapMode] = useState<BasemapMode>("satellite");
  const [showDetails, setShowDetails] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [terrainCells, setTerrainCells] =
    useState<GeoAsset[]>(initialTerrainCells);
  const [terrainScreening, setTerrainScreening] =
    useState<TerrainScreeningIndex | null>(initialTerrainScreening);
  const [forecastPredictions, setForecastPredictions] =
    useState<ForecastPredictionIndex | null>(initialForecastPredictions);
  const [floodExtents, setFloodExtents] = useState<GeoAsset[]>(
    initialFloodExtents,
  );
  const [terrainLoading, setTerrainLoading] = useState(
    initialTerrainCells.length === 0,
  );
  const [visibility, setVisibility] = useState<LayerVisibility>({
    floodRisk: true,
    gridCells: false,
    buildings: false,
    historicalFlood: false,
    hand: false,
    rivers: true,
    canals: true,
    roads: false,
    boundary: true,
    sensors: false,
    labels: false,
  });

  const mapLayer: MapLayer = forecastPredictions?.items.length
    ? "forecast"
    : floodMlPredictions?.items.length
      ? "ml_prediction"
      : "screening";

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
      try {
        const firstPage = await getTerrainPage(1);
        const remainingPages =
          firstPage.meta.pages > 1
            ? await Promise.all(
                Array.from({ length: firstPage.meta.pages - 1 }, (_, index) =>
                  getTerrainPage(index + 2),
                ),
              )
            : [];
        const screeningResponse = await fetch(
          `${spatialApiUrl}/flood-screening/terrain/index`,
          { signal: controller.signal },
        );
        if (!screeningResponse.ok) {
          throw new Error(
            `Screening API returned HTTP ${screeningResponse.status}`,
          );
        }
        const screening =
          (await screeningResponse.json()) as TerrainScreeningIndex;
        setTerrainCells([
          ...firstPage.features,
          ...remainingPages.flatMap((page) => page.features),
        ]);
        setTerrainScreening(screening);
      } catch {
        if (!controller.signal.aborted) {
          /* keep SSR fallback data */
        }
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
    void fetchFloodExtents(spatialApiUrl, controller.signal)
      .then(setFloodExtents)
      .catch(() => undefined);
    return () => controller.abort();
  }, [initialFloodExtents.length, spatialApiUrl]);

  const terrainScreeningById = useMemo(() => {
    const map = new Map<string, TerrainScreeningIndexItem>();
    terrainScreening?.items.forEach((item) => map.set(item.id, item));
    return map;
  }, [terrainScreening]);

  const activePredictionById = useMemo(() => {
    const map = new Map<
      string,
      NonNullable<typeof forecastPredictions>["items"][number]
    >();
    if (mapLayer === "forecast") {
      forecastPredictions?.items.forEach((item) => map.set(item.id, item));
    } else if (mapLayer === "ml_prediction") {
      floodMlPredictions?.items.forEach((item) => map.set(item.id, item));
    }
    return map;
  }, [forecastPredictions, floodMlPredictions, mapLayer]);

  const filteredSegments = useMemo(
    () =>
      assets.filter((asset) =>
        ["river_segment", "canal_segment"].includes(
          asset.properties.asset_type,
        ),
      ),
    [assets],
  );

  const roadSegments = useMemo(
    () => assets.filter(isRoadAsset),
    [assets],
  );
  const hasRiverData = useMemo(
    () =>
      assets.some((asset) => asset.properties.asset_type === "river_segment"),
    [assets],
  );
  const hasCanalData = useMemo(
    () =>
      assets.some((asset) => asset.properties.asset_type === "canal_segment"),
    [assets],
  );
  const hasLandcoverData = useMemo(
    () =>
      terrainCells.some((cell) => {
        const metadata = cell.properties.metadata;
        return (
          metadata.land_cover_dominant_code !== undefined ||
          metadata.land_cover_dataset_id !== undefined ||
          (typeof metadata.land_cover_percentages === "object" &&
            metadata.land_cover_percentages !== null)
        );
      }),
    [terrainCells],
  );
  const hasHandData = useMemo(
    () =>
      terrainCells.some((cell) => cell.properties.metadata.hand_mean_m !== undefined),
    [terrainCells],
  );
  const hasHistoricalFloodData = floodExtents.length > 0;

  const mappedAssets = useMemo(
    () => [
      ...assets.filter(
        (asset) => asset.properties.asset_type === "township_boundary",
      ),
      ...filteredSegments,
      ...roadSegments,
      ...floodExtents,
    ],
    [assets, filteredSegments, roadSegments, floodExtents],
  );

  const assetById = useMemo(() => {
    const map = new Map<string, GeoAsset>();
    for (const asset of [...terrainCells, ...mappedAssets]) {
      map.set(asset.id, asset);
    }
    return map;
  }, [mappedAssets, terrainCells]);

  const selectedAsset = selectedId ? assetById.get(selectedId) ?? null : null;
  const selectedCell =
    selectedAsset?.properties.asset_type === "terrain_cell"
      ? selectedAsset
      : null;
  const selectedScreening = selectedCell
    ? terrainScreeningById.get(selectedCell.id)
    : undefined;
  const selectedMlPrediction = selectedCell
    ? floodMlPredictions?.items.find((item) => item.id === selectedCell.id)
    : undefined;
  const selectedForecastPrediction = selectedCell
    ? forecastPredictions?.items.find((item) => item.id === selectedCell.id)
    : undefined;

  const explainabilityLayer =
    basemapMode === "terrain"
      ? "terrain"
      : mapLayer === "forecast"
        ? "forecast"
        : mapLayer === "ml_prediction"
          ? "ml_prediction"
          : "screening";

  const layerToggleOptions = useMemo(() => {
    const options: Array<
      [keyof LayerVisibility, string, boolean, string | undefined]
    > = [
      ["floodRisk", t("monitoring.layerFloodRisk"), true, undefined],
      ["gridCells", t("monitoring.layerGridCells"), true, undefined],
      [
        "buildings",
        t("monitoring.layerBuildings"),
        hasLandcoverData,
        t("map.layerTitles.landcover"),
      ],
      [
        "historicalFlood",
        t("monitoring.layerHistoricalFlood"),
        hasHistoricalFloodData,
        hasHistoricalFloodData
          ? t("map.layerTitles.floodHistory")
          : t("map.layerTitles.floodHistoryImport"),
      ],
      [
        "hand",
        t("monitoring.layerHand"),
        hasHandData,
        "Height Above Nearest Drainage (HAND)",
      ],
      [
        "rivers",
        t("monitoring.layerRivers"),
        hasRiverData,
        undefined,
      ],
      [
        "canals",
        t("monitoring.layerCanals"),
        hasCanalData,
        undefined,
      ],
      ["boundary", t("monitoring.layerBoundary"), true, undefined],
      ["labels", t("monitoring.layerLabels"), true, undefined],
    ];
    return options;
  }, [
    hasCanalData,
    hasHandData,
    hasHistoricalFloodData,
    hasLandcoverData,
    hasRiverData,
    t,
  ]);

  const handleSelectAsset = useCallback((asset: GeoAsset) => {
    setSelectedId(asset.id);
  }, []);

  const closeCellModal = useCallback(() => {
    setSelectedId(null);
  }, []);

  const next24HourRainMm = useMemo(() => {
    if (!rainfallForecast) return null;
    const start = Date.parse(rainfallForecast.fetched_at);
    return rainfallForecast.hourly
      .filter((hour) => Date.parse(`${hour.time}+06:30`) >= start)
      .slice(0, 24)
      .reduce((total, hour) => total + hour.precipitation_mm, 0);
  }, [rainfallForecast]);

  const peakRainProbability = useMemo(() => {
    if (!rainfallForecast) return null;
    const start = Date.parse(rainfallForecast.fetched_at);
    return Math.max(
      0,
      ...rainfallForecast.hourly
        .filter((hour) => Date.parse(`${hour.time}+06:30`) >= start)
        .slice(0, 24)
        .map((hour) => hour.probability_percent ?? 0),
    );
  }, [rainfallForecast]);

  const [liveClock, setLiveClock] = useState("");

  useEffect(() => {
    const tick = () => {
      setLiveClock(formatDateTime(new Date().toISOString()));
    };
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [formatDateTime]);

  const toggleLayer = useCallback(
    (key: keyof LayerVisibility) => {
      setVisibility((current) => ({ ...current, [key]: !current[key] }));
    },
    [],
  );

  const refresh = () => startRefresh(() => router.refresh());

  const isBackendOnline =
    !error && health?.database.status === "healthy";

  return (
    <div className={styles.shell}>
      <div className={styles.mapStage}>
        {terrainLoading ? (
          <div className={styles.loadingOverlay}>{t("map.loadingDem")}</div>
        ) : null}
        <FloodMonitoringMap
          ref={mapRef}
          assets={mappedAssets}
          terrainCells={terrainCells}
          screeningById={terrainScreeningById}
          predictionById={activePredictionById}
          layer={mapLayer}
          basemapMode={basemapMode}
          selectedId={selectedId}
          onSelect={handleSelectAsset}
          sensorStations={[]}
          latestObservations={[]}
          visibility={visibility}
        />
      </div>

      {selectedCell ? (
        <CellDetailModal
          cell={selectedCell}
          mapLayer={explainabilityLayer}
          screening={selectedScreening}
          mlPrediction={selectedMlPrediction}
          forecastPrediction={selectedForecastPrediction}
          rainfallHistory={rainfallHistory}
          onClose={closeCellModal}
        />
      ) : null}

      <div className={styles.topBarShell}>
        <div className={styles.topBarHotzone} aria-hidden="true" />
        <header className={styles.topBar}>
        <div className={styles.brand}>
          <h1>{t("monitoring.title")}</h1>
          <p>Maubin Township</p>
        </div>

        <div className={styles.centerControls}>
          <div className={styles.datePicker} suppressHydrationWarning>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <rect x="3" y="5" width="18" height="16" rx="2" />
              <path d="M16 3v4M8 3v4M3 10h18" />
            </svg>
            {liveClock || "\u00a0"}
          </div>
        </div>

        <div className={styles.topActions}>
          <div
            className={styles.viewToggle}
            aria-label={t("monitoring.basemapToggle")}
          >
            <button
              type="button"
              className={basemapMode === "satellite" ? styles.active : ""}
              onClick={() => setBasemapMode("satellite")}
            >
              {t("monitoring.basemapSatellite")}
            </button>
            <button
              type="button"
              className={basemapMode === "terrain" ? styles.active : ""}
              onClick={() => setBasemapMode("terrain")}
            >
              {t("monitoring.basemapTerrain")}
            </button>
          </div>
          {rainfallForecast ? (
            <div className={styles.weatherWidget}>
              <span className={styles.weatherIcon}>🌧️</span>
              <div>
                <strong>{t("monitoring.heavyRainForecast")}</strong>
                <span>
                  {formatNumber(next24HourRainMm ?? 0, 1)} {t("common.mm")} / 24h
                  {peakRainProbability !== null
                    ? ` · ${formatNumber(peakRainProbability, 0)}%`
                    : ""}
                </span>
              </div>
            </div>
          ) : null}
          {!isBackendOnline ? (
            <div className={styles.offlineActions}>
              <div
                className={`${styles.healthBadge} ${styles.healthOffline}`}
                title={
                  error ?? health?.database.detail ?? t("header.apiOffline")
                }
              >
                <span aria-hidden="true" />
                {t("header.apiOffline")}
              </div>
              <button
                type="button"
                className={styles.refreshButton}
                onClick={refresh}
                disabled={isRefreshing}
                aria-label={t("common.refresh")}
              >
                <Icon name="refresh" />
                {isRefreshing ? t("common.refreshing") : t("common.refresh")}
              </button>
            </div>
          ) : (
            <div
              className={`${styles.healthBadge} ${styles.healthOnline}`}
              title={health?.database.detail ?? t("header.spatialDbOnline")}
            >
              <span aria-hidden="true" />
              {t("header.spatialDbOnline")}
            </div>
          )}
          <LanguageSwitcher />
          <button
            type="button"
            className={styles.iconButton}
            aria-label={t("monitoring.notifications")}
            onClick={() => setShowDetails(true)}
          >
            <Icon name="bell" />
            {openAlerts.length ? (
              <span className={styles.badge}>{openAlerts.length}</span>
            ) : null}
          </button>
          <button
            type="button"
            className={styles.iconButton}
            aria-label={t("monitoring.menu")}
            onClick={() => setShowDetails(true)}
          >
            <Icon name="menu" />
          </button>
        </div>
      </header>
      </div>

      <aside className={styles.leftPanels}>
        <section className={styles.panel}>
          <h3>
            {visibility.buildings
              ? t("map.layerTitles.landcover")
              : basemapMode === "terrain"
                ? t("monitoring.terrainLegend")
                : t("monitoring.floodRiskLegend")}
          </h3>
          {visibility.buildings ? (
            <div className={styles.legendList}>
              {LAND_COVER_LEGEND.map((entry) => (
                <div key={entry.label} className={styles.legendItem}>
                  <i
                    className={styles.legendSwatch}
                    style={{ background: entry.color }}
                  />
                  {entry.label}
                </div>
              ))}
            </div>
          ) : basemapMode === "terrain" ? (
            <div className={styles.legendList}>
              <div className={styles.legendItem}>
                <i className={styles.legendSwatch} style={{ background: "#42b8cc" }} />
                {t("common.lower")}
              </div>
              <div className={styles.legendItem}>
                <i className={styles.legendSwatch} style={{ background: "#a7c85f" }} />
                {t("monitoring.elevationMid")}
              </div>
              <div className={styles.legendItem}>
                <i className={styles.legendSwatch} style={{ background: "#e3b54d" }} />
                {t("common.higher")}
              </div>
              <div className={styles.legendItem}>
                <i className={styles.legendSwatch} style={{ background: "#dc794d" }} />
                {t("monitoring.elevationHigh")}
              </div>
            </div>
          ) : (
            <>
          <div
            className={styles.probabilityGradient}
            style={{ background: PROBABILITY_GRADIENT_CSS }}
            aria-hidden="true"
          />
          <div className={styles.probabilityScale}>
            <span>0.0</span>
            <span>0.5</span>
            <span>1.0</span>
          </div>
          <p>{t("monitoring.floodRiskHint")}</p>
          <a className={styles.learnMore} href="#details">
            {t("monitoring.learnMore")}
          </a>
            </>
          )}
          {visibility.buildings ? (
            <p>{t("map.layerTitles.landcover")}</p>
          ) : basemapMode === "terrain" ? (
            <p>{t("monitoring.terrainHint")}</p>
          ) : null}
        </section>

        <section className={styles.panel}>
          <h3>{t("monitoring.layerControl")}</h3>
          <div className={styles.layerList}>
            {layerToggleOptions.map(([key, label, enabled, title]) => (
              <div key={key} className={styles.layerRow}>
                <span
                  className={enabled ? "" : styles.disabled}
                  title={title}
                >
                  {label}
                </span>
                <button
                  type="button"
                  className={`${styles.toggle} ${
                    visibility[key] && enabled ? styles.on : ""
                  }`}
                  aria-pressed={visibility[key] && enabled}
                  disabled={!enabled}
                  title={title}
                  onClick={() => enabled && toggleLayer(key)}
                />
              </div>
            ))}
          </div>
        </section>
      </aside>

      <div className={styles.mapControls}>
        <button
          type="button"
          aria-label="Zoom in"
          onClick={() => mapRef.current?.zoomIn()}
        >
          <Icon name="plus" />
        </button>
        <button
          type="button"
          aria-label="Zoom out"
          onClick={() => mapRef.current?.zoomOut()}
        >
          <Icon name="minus" />
        </button>
        <button
          type="button"
          aria-label={t("monitoring.layerControl")}
          onClick={() => toggleLayer("floodRisk")}
        >
          <Icon name="layers" />
        </button>
        <button
          type="button"
          aria-label="Locate Maubin"
          onClick={() => mapRef.current?.locate()}
        >
          <Icon name="locate" />
        </button>
      </div>

      <aside
        id="details"
        className={`${styles.detailsDrawer} ${showDetails ? styles.open : ""}`}
        aria-hidden={!showDetails}
      >
        <div className={styles.drawerHeader}>
          <h2>{t("monitoring.detailsTitle")}</h2>
          <button
            type="button"
            aria-label={t("monitoring.close")}
            onClick={() => setShowDetails(false)}
          >
            ×
          </button>
        </div>
        <div className={styles.drawerBody}>
          {error ? (
            <section className={styles.drawerSection}>
              <p>{t("errors.backendHint", { error })}</p>
            </section>
          ) : null}
          <section className={styles.drawerSection}>
            <h4>{t("monitoring.systemStatus")}</h4>
            <dl className={styles.detailGrid}>
              <div>
                <dt>{t("header.spatialDbOnline")}</dt>
                <dd>
                  {health?.database.status === "healthy"
                    ? t("common.verified")
                    : t("header.apiOffline")}
                </dd>
              </div>
              <div>
                <dt>{t("monitoring.openAlerts")}</dt>
                <dd>{formatNumber(openAlerts.length)}</dd>
              </div>
              <div>
                <dt>{t("monitoring.riskBasis")}</dt>
                <dd>
                  {floodIntelligence?.exposure?.risk_basis ??
                    t("monitoring.terrainBaseline")}
                </dd>
              </div>
            </dl>
          </section>
          {openAlerts.length ? (
            <section className={styles.drawerSection}>
              <h4>{t("monitoring.openAlerts")}</h4>
              {openAlerts.map((alert) => (
                <p key={alert.id}>
                  <strong>{alert.station_id}</strong> · {alert.message}
                </p>
              ))}
            </section>
          ) : null}
          <section className={styles.drawerSection}>
            <button
              type="button"
              className={styles.detailsButton}
              onClick={refresh}
              disabled={isRefreshing}
            >
              {isRefreshing ? t("common.refreshing") : t("common.refresh")}
            </button>
          </section>
        </div>
      </aside>
    </div>
  );
}
