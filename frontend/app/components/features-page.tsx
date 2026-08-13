"use client";

import Link from "next/link";
import LanguageSwitcher from "./language-switcher";
import styles from "./features-page.module.css";
import { useTranslation } from "@/lib/i18n";

const FEATURE_STATUS_ROWS = [
  { area: "postgis", status: "ready" },
  { area: "dashboard", status: "ready" },
  { area: "map2d", status: "ready" },
  { area: "map3d", status: "ready" },
  { area: "cesium", status: "ready" },
  { area: "terrainScreening", status: "ready" },
  { area: "rainfallForecast", status: "ready" },
  { area: "rainfallHistory", status: "ready" },
  { area: "historicalFlood", status: "ready" },
  { area: "mlSusceptibility", status: "ready" },
  { area: "eventHindcast", status: "ready" },
  { area: "floodForecast", status: "partial" },
  { area: "floodIntelligence", status: "ready" },
  { area: "sensorIngestion", status: "partial" },
  { area: "liveChart", status: "partial" },
  { area: "thresholdAlerts", status: "partial" },
  { area: "floodPrediction", status: "missing" },
] as const;

const FLOOD_PRODUCTS = ["terrain", "susceptibility", "event"] as const;

const DASHBOARD_FEATURES = [
  "overview",
  "map2d",
  "layers",
  "cellInspect",
  "rainfall",
  "detailsDrawer",
  "i18n",
] as const;

const MAP_LAYERS = [
  "floodRisk",
  "gridCells",
  "landCover",
  "historicalFlood",
  "hand",
  "rivers",
  "canals",
  "roads",
  "boundary",
  "elevation",
] as const;

const DATA_SOURCES = [
  "boundary",
  "dem",
  "osm",
  "worldcover",
  "gfd",
  "sar",
  "era5",
  "openMeteo",
] as const;

const INVENTORY_STATS = [
  { key: "terrainCells", value: "5,549" },
  { key: "riverSegments", value: "282" },
  { key: "canalSegments", value: "21" },
  { key: "era5Rows", value: "9,497" },
  { key: "gfdEvents", value: "17" },
  { key: "gfdGroups", value: "8" },
  { key: "gfdArea", value: "473.488 km²" },
] as const;

const TERRAIN_FACTORS = [
  { factor: "elevation", weight: "55%" },
  { factor: "waterway", weight: "30%" },
  { factor: "flatness", weight: "15%" },
] as const;

const SCORE_BANDS = ["lower", "moderate", "high", "veryHigh"] as const;

const API_GROUPS = [
  "health",
  "spatial",
  "screening",
  "weather",
  "sensors",
  "alerts",
  "catalog",
  "floodMl",
  "forecast",
  "intelligence",
] as const;

const NOT_AVAILABLE = [
  "depth",
  "arrival",
  "hydraulic",
  "sentinelRealtime",
  "productionAlerts",
  "physicalSensors",
] as const;

const INTERPRETATION = [
  "veryHigh",
  "notPrediction",
  "visual3d",
  "worldCover",
  "operational",
] as const;

function statusClass(status: "ready" | "partial" | "missing") {
  if (status === "ready") return styles.statusReady;
  if (status === "partial") return styles.statusPartial;
  return styles.statusMissing;
}

export default function FeaturesPage() {
  const { t } = useTranslation();

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerBrand}>
          <h1>{t("header.title")}</h1>
          <p>{t("featuresPage.nav.subtitle")}</p>
        </div>
        <div className={styles.headerActions}>
          <Link href="/" className={styles.backLink}>
            ← {t("featuresPage.nav.backToMap")}
          </Link>
          <Link href="/weather" className={styles.backLink}>
            {t("monitoring.weatherGuide")}
          </Link>
          <LanguageSwitcher />
        </div>
      </header>

      <main className={styles.main}>
        <section className={styles.hero}>
          <p className={styles.eyebrow}>{t("featuresPage.hero.eyebrow")}</p>
          <h2>{t("featuresPage.hero.title")}</h2>
          <p className={styles.lead}>{t("featuresPage.hero.lead")}</p>
        </section>

        <section className={styles.section} id="overview">
          <h3>{t("featuresPage.overview.title")}</h3>
          <p className={styles.sectionIntro}>{t("featuresPage.overview.intro")}</p>
          <ul className={styles.list}>
            {[1, 2, 3, 4, 5, 6].map((index) => (
              <li key={index}>{t(`featuresPage.overview.item${index}`)}</li>
            ))}
          </ul>
          <div className={styles.callout}>{t("featuresPage.overview.disclaimer")}</div>
        </section>

        <section className={styles.section} id="status">
          <h3>{t("featuresPage.status.title")}</h3>
          <p className={styles.sectionIntro}>{t("featuresPage.status.intro")}</p>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>{t("featuresPage.status.colArea")}</th>
                  <th>{t("featuresPage.status.colStatus")}</th>
                  <th>{t("featuresPage.status.colDetail")}</th>
                </tr>
              </thead>
              <tbody>
                {FEATURE_STATUS_ROWS.map(({ area, status }) => (
                  <tr key={area}>
                    <td>{t(`featuresPage.status.areas.${area}`)}</td>
                    <td className={statusClass(status)}>
                      {t(`featuresPage.status.labels.${status}`)}
                    </td>
                    <td>{t(`featuresPage.status.details.${area}`)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className={styles.section} id="flood-products">
          <h3>{t("featuresPage.floodProducts.title")}</h3>
          <p className={styles.sectionIntro}>{t("featuresPage.floodProducts.intro")}</p>
          <div className={styles.cardGrid}>
            {FLOOD_PRODUCTS.map((product) => (
              <article key={product} className={styles.card}>
                <h4>{t(`featuresPage.floodProducts.${product}.title`)}</h4>
                <p>{t(`featuresPage.floodProducts.${product}.description`)}</p>
                <div className={styles.cardMeta}>
                  <span className={styles.badge}>
                    {t(`featuresPage.floodProducts.${product}.use`)}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.section} id="dashboard">
          <h3>{t("featuresPage.dashboard.title")}</h3>
          <p className={styles.sectionIntro}>{t("featuresPage.dashboard.intro")}</p>
          <div className={styles.cardGrid}>
            {DASHBOARD_FEATURES.map((feature) => (
              <article key={feature} className={styles.card}>
                <h4>{t(`featuresPage.dashboard.items.${feature}.title`)}</h4>
                <p>{t(`featuresPage.dashboard.items.${feature}.description`)}</p>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.section} id="map-layers">
          <h3>{t("featuresPage.mapLayers.title")}</h3>
          <p className={styles.sectionIntro}>{t("featuresPage.mapLayers.intro")}</p>
          <div className={styles.cardGrid}>
            {MAP_LAYERS.map((layer) => (
              <article key={layer} className={styles.card}>
                <h4>{t(`featuresPage.mapLayers.items.${layer}.title`)}</h4>
                <p>{t(`featuresPage.mapLayers.items.${layer}.description`)}</p>
              </article>
            ))}
          </div>

          <div className={styles.subsection}>
            <h4>{t("featuresPage.mapLayers.terrainFormula.title")}</h4>
            <p className={styles.sectionIntro}>
              {t("featuresPage.mapLayers.terrainFormula.intro")}
            </p>
            <div className={styles.tableWrap}>
              <table className={`${styles.table} ${styles.factorTable}`}>
                <thead>
                  <tr>
                    <th>{t("featuresPage.mapLayers.terrainFormula.colFactor")}</th>
                    <th>{t("featuresPage.mapLayers.terrainFormula.colWeight")}</th>
                    <th>{t("featuresPage.mapLayers.terrainFormula.colMeaning")}</th>
                  </tr>
                </thead>
                <tbody>
                  {TERRAIN_FACTORS.map(({ factor, weight }) => (
                    <tr key={factor}>
                      <td>{t(`featuresPage.mapLayers.terrainFormula.factors.${factor}.name`)}</td>
                      <td>{weight}</td>
                      <td>{t(`featuresPage.mapLayers.terrainFormula.factors.${factor}.meaning`)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={styles.subsection}>
            <h4>{t("featuresPage.mapLayers.scoreBands.title")}</h4>
            <ul className={styles.list}>
              {SCORE_BANDS.map((band) => (
                <li key={band}>{t(`featuresPage.mapLayers.scoreBands.${band}`)}</li>
              ))}
            </ul>
          </div>
        </section>

        <section className={styles.section} id="data-sources">
          <h3>{t("featuresPage.dataSources.title")}</h3>
          <p className={styles.sectionIntro}>{t("featuresPage.dataSources.intro")}</p>
          <div className={styles.cardGrid}>
            {DATA_SOURCES.map((source) => (
              <article key={source} className={styles.card}>
                <h4>{t(`featuresPage.dataSources.items.${source}.title`)}</h4>
                <p>{t(`featuresPage.dataSources.items.${source}.description`)}</p>
                <div className={styles.cardMeta}>
                  <span className={styles.badge}>
                    {t(`featuresPage.dataSources.items.${source}.resolution`)}
                  </span>
                  <span className={styles.badge}>
                    {t(`featuresPage.dataSources.items.${source}.licence`)}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.section} id="inventory">
          <h3>{t("featuresPage.inventory.title")}</h3>
          <p className={styles.sectionIntro}>{t("featuresPage.inventory.intro")}</p>
          <div className={styles.inventoryGrid}>
            {INVENTORY_STATS.map(({ key, value }) => (
              <div key={key} className={styles.stat}>
                <strong>{value}</strong>
                <span>{t(`featuresPage.inventory.stats.${key}`)}</span>
              </div>
            ))}
          </div>

          <div className={styles.subsection}>
            <h4>{t("featuresPage.inventory.terrainFields.title")}</h4>
            <ul className={styles.list}>
              {[1, 2, 3, 4, 5, 6].map((index) => (
                <li key={index}>
                  {t(`featuresPage.inventory.terrainFields.item${index}`)}
                </li>
              ))}
            </ul>
          </div>

          <div className={styles.subsection}>
            <h4>{t("featuresPage.inventory.landCoverFields.title")}</h4>
            <ul className={styles.list}>
              {[1, 2, 3, 4].map((index) => (
                <li key={index}>
                  {t(`featuresPage.inventory.landCoverFields.item${index}`)}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className={styles.section} id="api">
          <h3>{t("featuresPage.api.title")}</h3>
          <p className={styles.sectionIntro}>{t("featuresPage.api.intro")}</p>
          {API_GROUPS.map((group) => (
            <div key={group} className={styles.apiGroup}>
              <h4>{t(`featuresPage.api.groups.${group}.title`)}</h4>
              <p>{t(`featuresPage.api.groups.${group}.description`)}</p>
              <p className={styles.code}>{t(`featuresPage.api.groups.${group}.endpoints`)}</p>
            </div>
          ))}
        </section>

        <section className={styles.section} id="not-available">
          <h3>{t("featuresPage.notAvailable.title")}</h3>
          <p className={styles.sectionIntro}>{t("featuresPage.notAvailable.intro")}</p>
          <ul className={styles.list}>
            {NOT_AVAILABLE.map((item) => (
              <li key={item}>{t(`featuresPage.notAvailable.items.${item}`)}</li>
            ))}
          </ul>
        </section>

        <section className={styles.section} id="interpretation">
          <h3>{t("featuresPage.interpretation.title")}</h3>
          <p className={styles.sectionIntro}>{t("featuresPage.interpretation.intro")}</p>
          <ul className={styles.list}>
            {INTERPRETATION.map((item) => (
              <li key={item}>{t(`featuresPage.interpretation.items.${item}`)}</li>
            ))}
          </ul>
        </section>

        <section className={styles.section} id="run">
          <h3>{t("featuresPage.run.title")}</h3>
          <p className={styles.sectionIntro}>{t("featuresPage.run.intro")}</p>
          <ul className={styles.list}>
            <li>{t("featuresPage.run.dashboard")}</li>
            <li>{t("featuresPage.run.swagger")}</li>
            <li>{t("featuresPage.run.health")}</li>
            <li>{t("featuresPage.run.features")}</li>
            <li>{t("featuresPage.run.weather")}</li>
          </ul>
        </section>

        <footer className={styles.footer}>{t("featuresPage.footer")}</footer>
      </main>
    </div>
  );
}
