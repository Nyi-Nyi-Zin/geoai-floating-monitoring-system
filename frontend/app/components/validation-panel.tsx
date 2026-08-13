"use client";

import type {
  FloodEventMlPredictionIndex,
  FloodIntelligenceSummary,
} from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import styles from "./dashboard.module.css";

const CELL_AREA_KM2 = 0.25;

function formatPct(value: number | undefined, formatNumber: (v: number, d?: number) => string) {
  if (value === undefined || Number.isNaN(value)) return "—";
  return `${formatNumber(value * 100, 1)}%`;
}

export type ValidationPanelProps = {
  predictions: FloodEventMlPredictionIndex | null;
  floodIntelligence: FloodIntelligenceSummary | null;
  loading?: boolean;
};

export default function ValidationPanel({
  predictions,
  floodIntelligence,
  loading = false,
}: ValidationPanelProps) {
  const { t, formatNumber, formatDate } = useTranslation();
  const sarStatus = floodIntelligence?.sar_validation;
  const sarReady = sarStatus?.status === "complete";
  const overallSar = sarStatus?.overall_model_vs_sar as
    | Record<string, number>
    | undefined;
  const pairedEvents = (
    sarStatus as { paired_events?: Array<Record<string, unknown>> } | undefined
  )?.paired_events;

  if (!predictions && !sarReady) {
    return (
      <section className={styles.validationPanel}>
        <div className={styles.validationHeader}>
          <p className={styles.eyebrow}>{t("validation.eyebrow")}</p>
          <h3>{t("validation.unavailable")}</h3>
        </div>
        <p className={styles.validationEmpty}>{t("validation.unavailableHint")}</p>
      </section>
    );
  }

  const hindcastSection = predictions ? (
    <>
      <div className={styles.validationHeader}>
        <div>
          <p className={styles.eyebrow}>{t("validation.hindcastEyebrow")}</p>
          <h3>{t("validation.hindcastTitle")}</h3>
          <small>
            {t("validation.eventMeta", {
              id: predictions.event.event_id,
              date: formatDate(predictions.event.event_start_date),
              algorithm: predictions.model.algorithm,
              version: predictions.model.model_version,
              mode: predictions.model.operating_mode,
              threshold: formatNumber(predictions.model.decision_threshold, 2),
            })}
          </small>
        </div>
      </div>
      <div className={styles.validationGrid}>
        <article className={styles.validationPredicted}>
          <span>{t("validation.aiPredicted")}</span>
          <strong>
            {formatNumber(
              predictions.summary.predicted_positive_cells * CELL_AREA_KM2,
              1,
            )}{" "}
            {t("common.km2")}
          </strong>
          <small>
            {t("validation.cellsFlagged", {
              count: formatNumber(predictions.summary.predicted_positive_cells),
            })}
          </small>
        </article>
        <article className={styles.validationObserved}>
          <span>{t("validation.gfdObserved")}</span>
          <strong>
            {formatNumber(
              predictions.summary.observed_positive_cells * CELL_AREA_KM2,
              1,
            )}{" "}
            {t("common.km2")}
          </strong>
          <small>
            {t("validation.cellsFlooded", {
              count: formatNumber(predictions.summary.observed_positive_cells),
            })}
          </small>
        </article>
        <article className={styles.validationOverlap}>
          <span>{t("validation.hindcastAgreement")}</span>
          <strong>
            {formatNumber(
              predictions.summary.true_positive_cells * CELL_AREA_KM2,
              1,
            )}{" "}
            {t("common.km2")}
          </strong>
          <small>
            {t("validation.precisionRecall", {
              precision: formatPct(predictions.summary.precision, formatNumber),
              recall: formatPct(predictions.summary.recall, formatNumber),
              tp: formatNumber(predictions.summary.true_positive_cells),
              fp: formatNumber(predictions.summary.false_positive_cells),
              fn: formatNumber(predictions.summary.false_negative_cells),
            })}
          </small>
        </article>
      </div>
      <div className={styles.validationLegend}>
        <span>
          <i style={{ background: "#d64545" }} /> {t("validation.predictedOnly")}
        </span>
        <span>
          <i style={{ background: "#2f80ed" }} /> {t("validation.observedOnly")}
        </span>
        <span>
          <i style={{ background: "#9b59f5" }} /> {t("validation.overlapTp")}
        </span>
      </div>
    </>
  ) : null;

  const sarSection = sarReady ? (
    <>
      <div className={styles.validationHeader} style={{ marginTop: "1.5rem" }}>
        <div>
          <p className={styles.eyebrow}>{t("validation.independentEyebrow")}</p>
          <h3>{t("validation.sarTitle")}</h3>
          <small>
            {t("validation.sarMeta", {
              version: sarStatus?.model_version ?? "—",
              gfd: sarStatus?.gfd_event_count ?? 0,
              sar: sarStatus?.sar_event_count ?? 0,
              paired: sarStatus?.paired_event_count ?? 0,
            })}
          </small>
        </div>
      </div>
      {overallSar ? (
        <div className={styles.validationGrid}>
          <article className={styles.validationPredicted}>
            <span>{t("validation.precisionVsSar")}</span>
            <strong>{formatPct(overallSar.precision, formatNumber)}</strong>
            <small>{t("validation.balancedThreshold")}</small>
          </article>
          <article className={styles.validationObserved}>
            <span>{t("validation.recallVsSar")}</span>
            <strong>{formatPct(overallSar.recall, formatNumber)}</strong>
            <small>
              F1 {formatPct(overallSar.f1, formatNumber)}
            </small>
          </article>
          <article className={styles.validationOverlap}>
            <span>{t("validation.discrimination")}</span>
            <strong>{formatPct(overallSar.roc_auc, formatNumber)}</strong>
            <small>
              {t("validation.rocAuc", {
                prAuc: formatPct(overallSar.pr_auc, formatNumber),
              })}
            </small>
          </article>
        </div>
      ) : null}
      {pairedEvents && pairedEvents.length > 0 ? (
        <div className={styles.sarValidationTableWrap}>
          <table className={styles.sarValidationTable}>
            <thead>
              <tr>
                <th>{t("validation.gfdEvent")}</th>
                <th>{t("validation.sarEvent")}</th>
                <th>{t("validation.date")}</th>
                <th>{t("validation.labelAgreement")}</th>
                <th>{t("validation.sarPrecision")}</th>
                <th>{t("validation.sarRecall")}</th>
              </tr>
            </thead>
            <tbody>
              {pairedEvents.map((row) => {
                const agreement = row.label_agreement as
                  | Record<string, number>
                  | undefined;
                const modelVsSar = row.model_vs_sar as
                  | Record<string, number>
                  | undefined;
                return (
                  <tr key={String(row.sar_event_id)}>
                    <td>{String(row.reference_gfd_event_id)}</td>
                    <td>{String(row.sar_event_id)}</td>
                    <td>{String(row.event_start_date)}</td>
                    <td>
                      {agreement?.label_agreement_rate !== undefined
                        ? formatPct(agreement.label_agreement_rate, formatNumber)
                        : "—"}
                    </td>
                    <td>{formatPct(modelVsSar?.precision, formatNumber)}</td>
                    <td>{formatPct(modelVsSar?.recall, formatNumber)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </>
  ) : (
    <p className={styles.validationNote}>{t("validation.sarPending")}</p>
  );

  return (
    <section className={styles.validationPanel} aria-label={t("validation.ariaLabel")}>
      {hindcastSection}
      {loading ? (
        <p className={styles.validationLoading}>{t("validation.loadingComparison")}</p>
      ) : null}
      {sarSection}
      <p className={styles.validationNote}>{t("validation.disclaimer")}</p>
    </section>
  );
}
