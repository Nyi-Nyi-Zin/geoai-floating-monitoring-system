"use client";

import type {
  FloodIntelligenceSummary,
  FloodMlPredictionIndex,
  ForecastPredictionIndex,
  GeoAsset,
  RainfallForecast,
  RainfallHistory,
  TerrainScreeningIndex,
} from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import styles from "./dashboard.module.css";

type RiskLevel = "LOW" | "MODERATE" | "HIGH";

const CELL_AREA_KM2 = 0.25;
const BUILT_UP_DENSITY_PER_KM2 = 450;

function computeRiskLevel(
  forecast: ForecastPredictionIndex | null,
  mlPredictions: FloodMlPredictionIndex | null,
  terrainScreening: TerrainScreeningIndex | null,
): RiskLevel {
  if (forecast?.summary) {
    const high =
      (forecast.summary.band_counts.HIGH ?? 0) +
      (forecast.summary.band_counts.VERY_HIGH ?? 0);
    const ratio = high / Math.max(forecast.summary.total_cells, 1);
    if (ratio >= 0.12 || forecast.summary.flagged_cells >= 400) return "HIGH";
    if (ratio >= 0.04 || forecast.summary.flagged_cells >= 80) return "MODERATE";
    return "LOW";
  }
  if (mlPredictions?.summary) {
    const high =
      (mlPredictions.summary.band_counts.HIGH ?? 0) +
      (mlPredictions.summary.band_counts.VERY_HIGH ?? 0);
    const ratio = high / Math.max(mlPredictions.summary.total_cells, 1);
    if (ratio >= 0.15) return "HIGH";
    if (ratio >= 0.06) return "MODERATE";
    return "LOW";
  }
  if (terrainScreening?.summary) {
    const veryHigh = terrainScreening.summary.band_counts.VERY_HIGH ?? 0;
    const ratio = veryHigh / Math.max(terrainScreening.summary.total_cells, 1);
    if (ratio >= 0.08) return "HIGH";
    if (ratio >= 0.03) return "MODERATE";
    return "LOW";
  }
  return "LOW";
}

function riskBadgeClass(level: RiskLevel) {
  if (level === "HIGH") return styles.riskHigh;
  if (level === "MODERATE") return styles.riskModerate;
  return styles.riskLow;
}

function riskEmoji(level: RiskLevel) {
  if (level === "HIGH") return "🔴";
  if (level === "MODERATE") return "🟡";
  return "🟢";
}

function estimateHighRiskPopulation(
  terrainCells: GeoAsset[],
  forecast: ForecastPredictionIndex | null,
  mlPredictions: FloodMlPredictionIndex | null,
): number {
  const highRiskIds = new Set<string>();
  if (forecast?.items.length) {
    for (const item of forecast.items) {
      if (
        item.risk_band === "HIGH" ||
        item.risk_band === "VERY_HIGH" ||
        item.predicted_label
      ) {
        highRiskIds.add(item.id);
      }
    }
  } else if (mlPredictions?.items.length) {
    for (const item of mlPredictions.items) {
      if (item.risk_band === "HIGH" || item.risk_band === "VERY_HIGH") {
        highRiskIds.add(item.id);
      }
    }
  }
  if (!highRiskIds.size) return 0;

  let builtUpKm2 = 0;
  for (const cell of terrainCells) {
    if (!highRiskIds.has(cell.id)) continue;
    const builtPct =
      typeof cell.properties.metadata.landcover_built_pct === "number"
        ? cell.properties.metadata.landcover_built_pct
        : typeof cell.properties.metadata.land_cover_percentages === "object" &&
            cell.properties.metadata.land_cover_percentages !== null
          ? Number(
              (
                cell.properties.metadata.land_cover_percentages as Record<
                  string,
                  unknown
                >
              )["50"] ?? 0,
            )
          : 0;
    builtUpKm2 += (builtPct / 100) * CELL_AREA_KM2;
  }
  return Math.round(builtUpKm2 * BUILT_UP_DENSITY_PER_KM2);
}

export type SituationOverviewProps = {
  terrainCells: GeoAsset[];
  terrainScreening: TerrainScreeningIndex | null;
  rainfallForecast: RainfallForecast | null;
  rainfallHistory: RainfallHistory | null;
  forecastPredictions: ForecastPredictionIndex | null;
  floodMlPredictions: FloodMlPredictionIndex | null;
  floodIntelligence: FloodIntelligenceSummary | null;
};

export default function SituationOverview({
  terrainCells,
  terrainScreening,
  rainfallForecast,
  rainfallHistory,
  forecastPredictions,
  floodMlPredictions,
  floodIntelligence,
}: SituationOverviewProps) {
  const { t, formatNumber } = useTranslation();
  const riskLevel = computeRiskLevel(
    forecastPredictions,
    floodMlPredictions,
    terrainScreening,
  );

  const sevenDayRainMm =
    rainfallForecast?.daily.reduce(
      (total, day) => total + day.precipitation_sum_mm,
      0,
    ) ??
    rainfallHistory?.daily.at(-1)?.accumulation_7d_mm ??
    null;

  const flaggedCells =
    floodIntelligence?.exposure?.flagged_cells ??
    forecastPredictions?.summary.flagged_cells ??
    forecastPredictions?.run.flagged_cell_count ??
    floodMlPredictions?.summary.predicted_positive_cells ??
    0;
  const affectedAreaKm2 =
    floodIntelligence?.exposure?.affected_area_km2 ?? flaggedCells * CELL_AREA_KM2;

  const buildingsAtRisk = floodIntelligence?.exposure?.buildings_at_risk ?? 0;
  const highRiskPopulation =
    buildingsAtRisk > 0
      ? buildingsAtRisk
      : estimateHighRiskPopulation(
          terrainCells,
          forecastPredictions,
          floodMlPredictions,
        );

  const riskSource = floodIntelligence?.scenario?.headline
    ? t("situation.floodIntelligence", {
        headline: floodIntelligence.scenario.headline,
      })
    : forecastPredictions
      ? t("situation.experimentalForecast")
      : floodMlPredictions
        ? t("situation.historicalMl")
        : t("situation.terrainBaseline");

  const earlyWarning = floodIntelligence?.early_warning;
  const displayRiskLevel = earlyWarning?.level ?? t(`risk.${riskLevel}`);

  return (
    <section className={styles.situationOverview} aria-label={t("situation.ariaLabel")}>
      <div className={styles.situationHeader}>
        <div>
          <p className={styles.eyebrow}>{t("situation.eyebrow")}</p>
          <h2>{t("header.location")}</h2>
          <small>{t("header.region")}</small>
        </div>
        <div className={`${styles.riskBadge} ${riskBadgeClass(riskLevel)}`}>
          <span>{riskEmoji(riskLevel)}</span>
          <div>
            <small>
              {earlyWarning
                ? `${t("risk.earlyWarning")} · ${earlyWarning.level}`
                : t("risk.currentRisk")}
            </small>
            <strong>{displayRiskLevel}</strong>
          </div>
        </div>
      </div>
      <div className={styles.situationGrid}>
        <article>
          <span>{t("situation.rainfall")}</span>
          <strong>
            {sevenDayRainMm === null
              ? "—"
              : `${formatNumber(sevenDayRainMm, 0)} ${t("common.mm")}`}
          </strong>
          <small>
            {t("situation.last7Days", {
              source: rainfallForecast
                ? t("situation.forecast")
                : t("situation.era5"),
            })}
          </small>
        </article>
        <article>
          <span>{t("situation.affectedArea")}</span>
          <strong>
            {formatNumber(affectedAreaKm2, 1)} {t("common.km2")}
          </strong>
          <small>
            {t("situation.flaggedCells", {
              count: formatNumber(flaggedCells),
            })}
          </small>
        </article>
        <article>
          <span>{t("situation.buildingsAtRisk")}</span>
          <strong>
            {highRiskPopulation > 0
              ? formatNumber(highRiskPopulation)
              : "—"}
          </strong>
          <small>
            {floodIntelligence?.exposure
              ? t("situation.builtUpInCells", {
                  area: formatNumber(
                    floodIntelligence.exposure.built_up_area_km2,
                    1,
                  ),
                })
              : t("situation.estimatedPopulation")}
          </small>
        </article>
        <article className={styles.situationSource}>
          <span>{t("situation.riskBasis")}</span>
          <strong>{riskSource}</strong>
          <small>
            {floodIntelligence?.scenario?.detail ??
              (forecastPredictions?.run.target_date
                ? t("situation.targetDate", {
                    date: forecastPredictions.run.target_date,
                  })
                : t("situation.clickForExplainability"))}
          </small>
        </article>
      </div>
    </section>
  );
}
