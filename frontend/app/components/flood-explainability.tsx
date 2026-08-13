"use client";

import type {
  FloodMlPredictionIndexItem,
  ForecastPredictionItem,
  GeoAsset,
  RainfallHistory,
  TerrainScreeningIndexItem,
} from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import styles from "./dashboard.module.css";

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

function asNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function computeRainfallAnomaly(history: RainfallHistory | null): number | null {
  if (!history || history.status !== "available" || history.daily.length < 14) {
    return null;
  }
  const latest = history.daily.at(-1);
  if (!latest) return null;
  const recent7d = latest.accumulation_7d_mm;
  const baselineSamples = history.daily
    .slice(-366, -7)
    .map((day) => day.accumulation_7d_mm)
    .filter((value) => value > 0);
  if (!baselineSamples.length) return null;
  const baseline =
    baselineSamples.reduce((sum, value) => sum + value, 0) /
    baselineSamples.length;
  if (baseline <= 0) return null;
  return ((recent7d - baseline) / baseline) * 100;
}

type LinearContribution = {
  feature: string;
  standardized_value: number;
  contribution: number;
};

function parseMlContributions(
  explanation: Record<string, unknown>,
): LinearContribution[] {
  const raw = explanation.top_linear_contributions;
  if (!Array.isArray(raw)) return [];
  return raw
    .filter(
      (item): item is LinearContribution =>
        typeof item === "object" &&
        item !== null &&
        typeof (item as LinearContribution).feature === "string",
    )
    .slice(0, 4);
}

export type FloodExplainabilityProps = {
  cell: GeoAsset;
  mapLayer: MapLayer;
  screening?: TerrainScreeningIndexItem;
  mlPrediction?: FloodMlPredictionIndexItem;
  forecastPrediction?: ForecastPredictionItem;
  rainfallHistory: RainfallHistory | null;
  probabilityOverride?: number;
};

export default function FloodExplainability({
  cell,
  mapLayer,
  screening,
  mlPrediction,
  forecastPrediction,
  rainfallHistory,
  probabilityOverride,
}: FloodExplainabilityProps) {
  const { t, formatNumber } = useTranslation();
  const elevation = asNumber(cell.properties.metadata.elevation_mean_m);
  const waterwayDistance = asNumber(
    cell.properties.metadata.distance_to_waterway_m,
  );
  const floodedFraction = asNumber(
    mlPrediction?.flooded_fraction ??
      cell.properties.metadata.flooded_fraction ??
      0,
  );
  const historicalEvents = asNumber(
    mlPrediction?.historical_event_count ??
      cell.properties.metadata.historical_event_count ??
      0,
  );
  const rainfallAnomaly = computeRainfallAnomaly(rainfallHistory);

  const probability =
    probabilityOverride ??
    forecastPrediction?.probability ??
    mlPrediction?.probability ??
    (screening ? screening.screening_score / 100 : null);

  const mlContributions = mlPrediction
    ? parseMlContributions(mlPrediction.explanation)
    : [];

  const featureLabel = (feature: string) => {
    const key = `explainability.features.${feature}`;
    const translated = t(key);
    return translated === key ? feature.replaceAll("_", " ") : translated;
  };

  const reasons: { label: string; detail: string; active: boolean }[] = [
    {
      label: t("explainability.lowElevation", {
        value: formatNumber(elevation),
      }),
      detail: t("explainability.lowElevationDetail"),
      active:
        elevation <= 3 ||
        asNumber(cell.properties.metadata.elevation_percentile) <= 35,
    },
    {
      label: t("explainability.nearRiver", {
        value: formatNumber(waterwayDistance, 0),
      }),
      detail: t("explainability.nearRiverDetail"),
      active: waterwayDistance <= 600,
    },
    {
      label:
        rainfallAnomaly === null
          ? t("explainability.rainfallUnavailable")
          : t("explainability.heavyRainfall", {
              value: `${rainfallAnomaly >= 0 ? "+" : ""}${formatNumber(rainfallAnomaly, 0)}`,
            }),
      detail: t("explainability.rainfallDetail"),
      active: rainfallAnomaly !== null && rainfallAnomaly >= 20,
    },
    {
      label:
        historicalEvents > 0 || floodedFraction > 0
          ? t("explainability.historicalFloodArea")
          : t("explainability.noHistoricalFlooding"),
      detail:
        historicalEvents > 0
          ? t("explainability.historicalDetail", {
              events: formatNumber(historicalEvents, 0),
              fraction: formatNumber(floodedFraction * 100, 0),
            })
          : t("explainability.noGfdLabel"),
      active: historicalEvents > 0 || floodedFraction >= 0.05,
    },
  ];

  if (screening && mapLayer === "screening") {
    reasons.unshift({
      label: t("explainability.susceptibilityScore", {
        band: screening.screening_band.replaceAll("_", " "),
      }),
      detail: t("explainability.terrainRanking", {
        score: formatNumber(screening.screening_score, 1),
      }),
      active: screening.screening_score >= 50,
    });
  }

  return (
    <div className={styles.explainabilityCard}>
      <div className={styles.explainabilityHeader}>
        <div>
          <span>{t("explainability.why")}</span>
          <small>{t("explainability.subtitle")}</small>
        </div>
        {probability !== null ? (
          <strong>
            {formatNumber(probability * 100, 0)}%
            <small>{t("explainability.floodRisk")}</small>
          </strong>
        ) : null}
      </div>
      <ul className={styles.explainabilityList}>
        {reasons.map((reason) => (
          <li
            key={reason.label}
            className={reason.active ? styles.explainActive : styles.explainInactive}
          >
            <span aria-hidden="true">{reason.active ? "✓" : "○"}</span>
            <div>
              <strong>{reason.label}</strong>
              <p>{reason.detail}</p>
            </div>
          </li>
        ))}
      </ul>
      {mlContributions.length > 0 && mapLayer === "ml_prediction" ? (
        <div className={styles.mlContributions}>
          <span>{t("explainability.topFeatures")}</span>
          {mlContributions.map((item) => (
            <div key={item.feature}>
              <strong>{featureLabel(item.feature)}</strong>
              <small>
                {t("explainability.contribution", {
                  value: formatNumber(item.contribution, 3),
                  z: formatNumber(item.standardized_value, 2),
                })}
              </small>
            </div>
          ))}
        </div>
      ) : null}
      <p className={styles.explainabilityNote}>{t("explainability.disclaimer")}</p>
    </div>
  );
}
