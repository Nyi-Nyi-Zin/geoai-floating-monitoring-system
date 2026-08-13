"use client";

import Link from "next/link";
import { useCallback, useMemo, useState, useTransition } from "react";
import LanguageSwitcher from "./language-switcher";
import styles from "./weather-forecast-page.module.css";
import { useTranslation } from "@/lib/i18n";
import type { RainfallForecast, RainfallHistory } from "@/lib/api";
import {
  fetchWeatherPageData,
  type WeatherPageData,
} from "@/lib/weather-api";

type RainfallWindow = 30 | 90 | 366;

type Props = {
  initialData: WeatherPageData;
};

function next24HourTotal(forecast: RainfallForecast | null): number | null {
  if (!forecast) return null;
  const start = Date.parse(forecast.fetched_at);
  return forecast.hourly
    .filter((row) => {
      const hour = Date.parse(row.time);
      return hour >= start && hour < start + 24 * 60 * 60 * 1000;
    })
    .reduce((sum, row) => sum + row.precipitation_mm, 0);
}

function DailyForecastChart({
  daily,
  formatDate,
  formatNumber,
  heavyThreshold,
}: {
  daily: RainfallForecast["daily"];
  formatDate: (value: string) => string;
  formatNumber: (value: number, digits?: number) => string;
  heavyThreshold: number;
}) {
  const width = 760;
  const height = 220;
  const padding = { top: 20, right: 16, bottom: 36, left: 44 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const maxY = Math.max(
    5,
    Math.ceil(Math.max(...daily.map((d) => d.precipitation_sum_mm), 1) / 5) * 5,
  );
  const slot = plotWidth / Math.max(daily.length, 1);
  const barWidth = Math.min(48, slot * 0.65);

  const projectY = (value: number) =>
    padding.top + ((maxY - value) / maxY) * plotHeight;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={styles.chart}
      role="img"
      aria-hidden="true"
    >
      {[0, 0.25, 0.5, 0.75, 1].map((tick) => {
        const y = padding.top + tick * plotHeight;
        const value = maxY * (1 - tick);
        return (
          <g key={tick}>
            <line
              x1={padding.left}
              x2={width - padding.right}
              y1={y}
              y2={y}
              stroke="rgba(255,255,255,0.08)"
            />
            <text
              x={padding.left - 8}
              y={y + 4}
              textAnchor="end"
              fill="rgba(232,244,242,0.45)"
              fontSize="10"
            >
              {formatNumber(value, 0)}
            </text>
          </g>
        );
      })}
      {daily.map((day, index) => {
        const x = padding.left + index * slot + (slot - barWidth) / 2;
        const barHeight = (day.precipitation_sum_mm / maxY) * plotHeight;
        const y = padding.top + plotHeight - barHeight;
        const heavy = day.precipitation_sum_mm >= heavyThreshold;
        return (
          <g key={day.date}>
            <rect
              x={x}
              y={y}
              width={barWidth}
              height={Math.max(barHeight, day.precipitation_sum_mm > 0 ? 2 : 0)}
              rx={4}
              fill={heavy ? "#e3b54d" : "#42b8cc"}
            />
            <text
              x={x + barWidth / 2}
              y={height - 12}
              textAnchor="middle"
              fill="rgba(232,244,242,0.62)"
              fontSize="10"
            >
              {formatDate(day.date).replace(/,\s*\d{4}$/, "")}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function HourlyForecastChart({
  hourly,
  fetchedAt,
  formatNumber,
}: {
  hourly: RainfallForecast["hourly"];
  fetchedAt: string;
  formatNumber: (value: number, digits?: number) => string;
}) {
  const start = Date.parse(fetchedAt);
  const points = hourly.filter((row) => {
    const hour = Date.parse(row.time);
    return hour >= start && hour < start + 48 * 60 * 60 * 1000;
  });
  if (!points.length) return null;

  const width = 900;
  const height = 200;
  const padding = { top: 16, right: 16, bottom: 30, left: 44 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const maxY = Math.max(
    2,
    Math.ceil(Math.max(...points.map((p) => p.precipitation_mm), 0.1) * 2) / 2,
  );
  const projectX = (index: number) =>
    padding.left +
    (points.length === 1 ? plotWidth / 2 : (index / (points.length - 1)) * plotWidth);
  const projectY = (value: number) =>
    padding.top + ((maxY - value) / maxY) * plotHeight;

  const linePath = points
    .map(
      (point, index) =>
        `${index ? "L" : "M"}${projectX(index).toFixed(1)},${projectY(point.precipitation_mm).toFixed(1)}`,
    )
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={styles.chart}
      role="img"
      aria-hidden="true"
    >
      <path
        d={linePath}
        fill="none"
        stroke="#7dd3fc"
        strokeWidth="2"
      />
      {points.map((point, index) => (
        <circle
          key={point.time}
          cx={projectX(index)}
          cy={projectY(point.precipitation_mm)}
          r={3}
          fill="#42b8cc"
        />
      ))}
      <text x={padding.left} y={height - 8} fill="rgba(232,244,242,0.45)" fontSize="10">
        0h
      </text>
      <text
        x={width - padding.right}
        y={height - 8}
        textAnchor="end"
        fill="rgba(232,244,242,0.45)"
        fontSize="10"
      >
        48h · max {formatNumber(maxY, 1)} mm
      </text>
    </svg>
  );
}

function HistoryChart({
  points,
  formatNumber,
  formatDate,
}: {
  points: RainfallHistory["daily"];
  formatNumber: (value: number, digits?: number) => string;
  formatDate: (value: string) => string;
}) {
  const width = 900;
  const height = 240;
  const padding = { top: 20, right: 16, bottom: 34, left: 48 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const rawMax = Math.max(
    1,
    ...points.flatMap((p) => [p.mean_precipitation_mm, p.accumulation_7d_mm]),
  );
  const maxY = Math.max(5, Math.ceil(rawMax / 5) * 5);
  const projectX = (index: number) =>
    padding.left +
    (points.length === 1 ? plotWidth / 2 : (index / (points.length - 1)) * plotWidth);
  const projectY = (value: number) =>
    padding.top + ((maxY - value) / maxY) * plotHeight;
  const barSlot = plotWidth / Math.max(points.length, 1);
  const barWidth = Math.max(1.2, Math.min(10, barSlot * 0.65));
  const accumulationPath = points
    .map(
      (point, index) =>
        `${index ? "L" : "M"}${projectX(index).toFixed(1)},${projectY(point.accumulation_7d_mm).toFixed(1)}`,
    )
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={styles.chart}
      role="img"
      aria-hidden="true"
    >
      {points.map((point, index) => {
        const x = projectX(index) - barWidth / 2;
        const barHeight = (point.mean_precipitation_mm / maxY) * plotHeight;
        return (
          <rect
            key={point.date}
            x={x}
            y={padding.top + plotHeight - barHeight}
            width={barWidth}
            height={Math.max(barHeight, point.mean_precipitation_mm > 0 ? 1 : 0)}
            fill="#6f8f86"
            opacity={0.85}
          />
        );
      })}
      <path
        d={accumulationPath}
        fill="none"
        stroke="#caff5b"
        strokeWidth="2"
      />
      <text x={padding.left} y={height - 10} fill="rgba(232,244,242,0.45)" fontSize="10">
        {formatDate(points[0]?.date ?? "")}
      </text>
      <text
        x={width - padding.right}
        y={height - 10}
        textAnchor="end"
        fill="rgba(232,244,242,0.45)"
        fontSize="10"
      >
        {formatDate(points[points.length - 1]?.date ?? "")}
      </text>
    </svg>
  );
}

export default function WeatherForecastPage({ initialData }: Props) {
  const { t, formatNumber, formatDate, formatDateTime } = useTranslation();
  const [data, setData] = useState(initialData);
  const [historyWindow, setHistoryWindow] = useState<RainfallWindow>(90);
  const [isPending, startTransition] = useTransition();

  const { forecast, history, apiBaseUrl, error } = data;

  const refresh = useCallback(() => {
    startTransition(async () => {
      const next = await fetchWeatherPageData(apiBaseUrl);
      setData(next);
    });
  }, [apiBaseUrl]);

  const rain24h = useMemo(() => next24HourTotal(forecast), [forecast]);
  const rain7d = useMemo(
    () =>
      forecast?.daily.reduce(
        (sum, day) => sum + day.precipitation_sum_mm,
        0,
      ) ?? null,
    [forecast],
  );
  const peakProbability = useMemo(() => {
    if (!forecast) return null;
    const values = forecast.daily
      .map((d) => d.probability_max_percent)
      .filter((v): v is number => v !== null);
    return values.length ? Math.max(...values) : null;
  }, [forecast]);

  const historyPoints = useMemo(
    () => (history?.daily ?? []).slice(-historyWindow),
    [history, historyWindow],
  );

  const heavyThreshold = 20;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerBrand}>
          <h1>{t("header.title")}</h1>
          <p>{t("weatherPage.nav.subtitle")}</p>
        </div>
        <div className={styles.headerActions}>
          <Link href="/" className={styles.navLink}>
            ← {t("weatherPage.nav.backToMap")}
          </Link>
          <Link href="/features" className={styles.navLink}>
            {t("monitoring.featuresGuide")}
          </Link>
          <button
            type="button"
            className={styles.refreshButton}
            onClick={refresh}
            disabled={isPending}
          >
            {isPending ? t("common.refreshing") : t("common.refresh")}
          </button>
          <LanguageSwitcher />
        </div>
      </header>

      <main className={styles.main}>
        <section className={styles.hero}>
          <p className={styles.eyebrow}>{t("weatherPage.hero.eyebrow")}</p>
          <h2>{t("weatherPage.hero.title")}</h2>
          <p className={styles.lead}>{t("weatherPage.hero.lead")}</p>
        </section>

        {error ? <div className={styles.errorBanner}>{error}</div> : null}

        <div className={styles.statsGrid}>
          <div className={styles.stat}>
            <strong>
              {rain24h !== null
                ? `${formatNumber(rain24h, 1)} ${t("common.mm")}`
                : "—"}
            </strong>
            <span>{t("weatherPage.stats.next24h")}</span>
          </div>
          <div className={styles.stat}>
            <strong>
              {rain7d !== null
                ? `${formatNumber(rain7d, 1)} ${t("common.mm")}`
                : "—"}
            </strong>
            <span>{t("weatherPage.stats.next7d")}</span>
          </div>
          <div className={styles.stat}>
            <strong>
              {peakProbability !== null ? `${peakProbability}%` : "—"}
            </strong>
            <span>{t("weatherPage.stats.peakProbability")}</span>
          </div>
          <div className={styles.stat}>
            <strong>
              {history?.summary.wet_days !== undefined
                ? formatNumber(history.summary.wet_days)
                : "—"}
            </strong>
            <span>{t("weatherPage.stats.era5WetDays")}</span>
          </div>
        </div>

        <section className={styles.section} id="forecast">
          <div className={styles.sectionHeader}>
            <div>
              <h3>{t("weatherPage.forecast.title")}</h3>
              <p className={styles.sectionIntro}>
                {t("weatherPage.forecast.intro")}
              </p>
            </div>
          </div>

          {forecast ? (
            <>
              <div className={styles.metaRow}>
                <span className={styles.badge}>{forecast.source}</span>
                <span className={styles.badge}>
                  {forecast.location.name} · {formatNumber(forecast.location.latitude, 4)}°N
                </span>
                <span className={`${styles.badge} ${styles.badgeMuted}`}>
                  {t("weatherPage.forecast.fetched")}:{" "}
                  {formatDateTime(forecast.fetched_at)}
                </span>
                {forecast.cached ? (
                  <span className={`${styles.badge} ${styles.badgeMuted}`}>
                    {t("weatherPage.forecast.cached")}
                  </span>
                ) : null}
              </div>

              <div className={styles.legend}>
                <span className={styles.legendItem}>
                  <i className={`${styles.swatch} ${styles.swatchForecast}`} />
                  {t("weatherPage.forecast.dailyPrecip")}
                </span>
                <span className={styles.legendItem}>
                  <i className={`${styles.swatch} ${styles.swatchProbability}`} />
                  {t("weatherPage.forecast.hourlyLine")}
                </span>
              </div>

              <div className={styles.chartWrap}>
                <DailyForecastChart
                  daily={forecast.daily}
                  formatDate={formatDate}
                  formatNumber={formatNumber}
                  heavyThreshold={heavyThreshold}
                />
              </div>

              <div className={styles.chartWrap}>
                <HourlyForecastChart
                  hourly={forecast.hourly}
                  fetchedAt={forecast.fetched_at}
                  formatNumber={formatNumber}
                />
              </div>

              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>{t("weatherPage.table.date")}</th>
                      <th>{t("weatherPage.table.precipSum")}</th>
                      <th>{t("weatherPage.table.probability")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {forecast.daily.map((day) => (
                      <tr key={day.date}>
                        <td>{formatDate(day.date)}</td>
                        <td
                          className={`${styles.num} ${
                            day.precipitation_sum_mm >= heavyThreshold
                              ? styles.heavyDay
                              : ""
                          }`}
                        >
                          {formatNumber(day.precipitation_sum_mm, 1)} {t("common.mm")}
                        </td>
                        <td className={styles.num}>
                          {day.probability_max_percent !== null
                            ? `${day.probability_max_percent}%`
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className={styles.callout}>{t("weatherPage.forecast.disclaimer")}</div>
            </>
          ) : (
            <p className={styles.sectionIntro}>{t("weatherPage.forecast.unavailable")}</p>
          )}
        </section>

        <section className={styles.section} id="history">
          <div className={styles.sectionHeader}>
            <div>
              <h3>{t("weatherPage.history.title")}</h3>
              <p className={styles.sectionIntro}>{t("weatherPage.history.intro")}</p>
            </div>
            {history?.status === "available" ? (
              <div className={styles.windowToggle} aria-label="History window">
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
                    className={historyWindow === days ? styles.activeWindow : ""}
                    aria-pressed={historyWindow === days}
                    onClick={() => setHistoryWindow(days as RainfallWindow)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            ) : null}
          </div>

          {history?.status === "available" && historyPoints.length ? (
            <>
              <div className={styles.metaRow}>
                <span className={styles.badge}>{history.source_name}</span>
                <span className={styles.badge}>
                  {history.model} · ~{history.source_resolution_m / 1000} km
                </span>
                <span className={`${styles.badge} ${styles.badgeMuted}`}>
                  {formatNumber(history.grid_cell_count)} {t("common.cells")}
                </span>
              </div>

              <div className={styles.legend}>
                <span className={styles.legendItem}>
                  <i className={`${styles.swatch} ${styles.swatchHistory}`} />
                  {t("rainfall.dailyMean")}
                </span>
                <span className={styles.legendItem}>
                  <i className={`${styles.swatch} ${styles.swatchAccumulation}`} />
                  {t("rainfall.rolling7day")}
                </span>
              </div>

              <div className={styles.chartWrap}>
                <HistoryChart
                  points={historyPoints}
                  formatNumber={formatNumber}
                  formatDate={formatDate}
                />
              </div>

              <div className={styles.statsGrid}>
                <div className={styles.stat}>
                  <strong>
                    {formatNumber(
                      historyPoints.reduce(
                        (sum, p) => sum + p.mean_precipitation_mm,
                        0,
                      ),
                      1,
                    )}{" "}
                    {t("common.mm")}
                  </strong>
                  <span>{t("rainfall.selectedPeriod")}</span>
                </div>
                <div className={styles.stat}>
                  <strong>{formatNumber(history.summary.peak_7d_mm, 1)} {t("common.mm")}</strong>
                  <span>{t("rainfall.peakDaily")}</span>
                </div>
                <div className={styles.stat}>
                  <strong>
                    {formatNumber(latest30Accum(historyPoints), 1)} {t("common.mm")}
                  </strong>
                  <span>{t("rainfall.latest30day")}</span>
                </div>
              </div>
            </>
          ) : (
            <p className={styles.sectionIntro}>{t("rainfall.notLoadedHint")}</p>
          )}
        </section>

        <section className={styles.section} id="api">
          <h3>{t("weatherPage.api.title")}</h3>
          <p className={styles.sectionIntro}>{t("weatherPage.api.intro")}</p>

          <div className={styles.apiSection}>
            <strong>GET /weather/rainfall-forecast</strong>
            <code>{`${apiBaseUrl}/weather/rainfall-forecast?forecast_days=7`}</code>
          </div>
          <div className={styles.apiSection}>
            <strong>GET /weather/rainfall-history</strong>
            <code>{`${apiBaseUrl}/weather/rainfall-history?limit=366`}</code>
          </div>

          <div className={styles.callout}>{t("weatherPage.api.note")}</div>
        </section>

        <footer className={styles.footer}>{t("weatherPage.footer")}</footer>
      </main>
    </div>
  );
}

function latest30Accum(points: RainfallHistory["daily"]): number {
  const slice = points.slice(-30);
  return slice.reduce((sum, p) => sum + p.mean_precipitation_mm, 0);
}
