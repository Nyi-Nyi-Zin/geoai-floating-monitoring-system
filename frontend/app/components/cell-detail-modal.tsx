"use client";

import { useEffect } from "react";
import type {
  FloodMlPredictionIndexItem,
  ForecastPredictionItem,
  GeoAsset,
  RainfallHistory,
  TerrainScreeningIndexItem,
} from "@/lib/api";
import FloodExplainability from "./flood-explainability";
import { useTranslation } from "@/lib/i18n";
import styles from "./cell-detail-modal.module.css";

type MapLayer = "terrain" | "screening" | "ml_prediction" | "forecast";

export type CellDetailModalProps = {
  cell: GeoAsset;
  mapLayer: MapLayer;
  screening?: TerrainScreeningIndexItem;
  mlPrediction?: FloodMlPredictionIndexItem;
  forecastPrediction?: ForecastPredictionItem;
  rainfallHistory: RainfallHistory | null;
  onClose: () => void;
};

function asNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

export default function CellDetailModal({
  cell,
  mapLayer,
  screening,
  mlPrediction,
  forecastPrediction,
  rainfallHistory,
  onClose,
}: CellDetailModalProps) {
  const { t, formatNumber } = useTranslation();

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const elevation = asNumber(cell.properties.metadata.elevation_mean_m);
  const elevationPct = asNumber(cell.properties.metadata.elevation_percentile);
  const waterwayDistance = asNumber(cell.properties.metadata.distance_to_waterway_m);
  const probability =
    forecastPrediction?.probability ??
    mlPrediction?.probability ??
    (screening ? screening.screening_score / 100 : null);
  const riskBand =
    forecastPrediction?.risk_band ??
    mlPrediction?.risk_band ??
    screening?.screening_band ??
    null;
  const riskLabel = riskBand ? riskBand.replaceAll("_", " ") : "—";
  const isHighRisk =
    (probability ?? 0) >= 0.5 ||
    (screening?.screening_score ?? 0) >= 60;

  return (
    <div
      className={styles.backdrop}
      role="presentation"
      onClick={onClose}
    >
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="cell-detail-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className={styles.header}>
          <div>
            <h2 id="cell-detail-title">{t("monitoring.cellDetailTitle")}</h2>
            <p>{cell.properties.name || t("monitoring.cellDetailSubtitle")}</p>
            {riskBand ? (
              <span
                className={`${styles.badge} ${isHighRisk ? styles.badgeHigh : ""}`}
              >
                {riskLabel}
              </span>
            ) : null}
          </div>
          <button
            type="button"
            className={styles.closeButton}
            aria-label={t("monitoring.close")}
            onClick={onClose}
          >
            ×
          </button>
        </div>
        <div className={styles.body}>
          <dl className={styles.grid}>
            <div>
              <dt>{t("monitoring.elevationMean")}</dt>
              <dd>
                {formatNumber(elevation, 1)} {t("common.m")}
              </dd>
            </div>
            <div>
              <dt>{t("monitoring.elevationPercentile")}</dt>
              <dd>{formatNumber(elevationPct, 0)}%</dd>
            </div>
            <div>
              <dt>{t("monitoring.waterwayDistance")}</dt>
              <dd>
                {formatNumber(waterwayDistance, 0)} {t("common.m")}
              </dd>
            </div>
            <div>
              <dt>{t("monitoring.floodRiskMax")}</dt>
              <dd>
                {probability !== null
                  ? `${formatNumber(probability * 100, 1)}%`
                  : t("common.unavailable")}
              </dd>
            </div>
            {mapLayer === "forecast" && forecastPrediction ? (
              <div>
                <dt>{t("monitoring.forecastBand")}</dt>
                <dd>{forecastPrediction.risk_band.replaceAll("_", " ")}</dd>
              </div>
            ) : null}
            {mapLayer === "ml_prediction" && mlPrediction ? (
              <div>
                <dt>{t("monitoring.historicalEvents")}</dt>
                <dd>{formatNumber(mlPrediction.historical_event_count)}</dd>
              </div>
            ) : null}
            {screening ? (
              <div>
                <dt>{t("monitoring.screeningScore")}</dt>
                <dd>{formatNumber(screening.screening_score, 1)}/100</dd>
              </div>
            ) : null}
          </dl>
          <div className={styles.explainWrap}>
            <FloodExplainability
              cell={cell}
              mapLayer={mapLayer === "forecast" ? "forecast" : mapLayer}
              screening={screening}
              mlPrediction={mlPrediction}
              forecastPrediction={forecastPrediction}
              rainfallHistory={rainfallHistory}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
