import { desc, eq, sql } from "drizzle-orm";
import { rainfallHistory, scheduleConfigs } from "../drizzle/schema";
import { getDb } from "./db";

const MAUBIN = { latitude: 16.7247, longitude: 95.6687 };
const OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast";
const OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive";

export type WeatherPoint = { date: string; precipitationMm: number };

type OpenMeteoDaily = {
  time?: string[];
  precipitation_sum?: Array<number | null>;
};

type OpenMeteoResponse = { daily?: OpenMeteoDaily };

function isoDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function dayBefore(date: Date) {
  const value = new Date(date);
  value.setUTCDate(value.getUTCDate() - 1);
  return value;
}

export function buildRainfallRecords(daily: OpenMeteoDaily, sourceKey: string) {
  const values = daily.precipitation_sum ?? [];
  const dates = daily.time ?? [];
  return dates.map((observedDate, index) => {
    const precipitationMm = Math.max(0, Number(values[index] ?? 0));
    const prior = values
      .slice(Math.max(0, index - 6), index + 1)
      .reduce<number>((total, value) => total + Math.max(0, Number(value ?? 0)), 0);
    return { sourceKey, observedDate, precipitationMm, accumulation7dMm: prior };
  });
}

export async function getWeatherSnapshot() {
  const url = new URL(OPEN_METEO_FORECAST_URL);
  url.searchParams.set("latitude", String(MAUBIN.latitude));
  url.searchParams.set("longitude", String(MAUBIN.longitude));
  url.searchParams.set("daily", "precipitation_sum");
  url.searchParams.set("forecast_days", "7");
  url.searchParams.set("timezone", "Asia/Yangon");

  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Open-Meteo forecast request failed (${response.status})`);
  const payload = (await response.json()) as OpenMeteoResponse;
  return buildRainfallRecords(payload.daily ?? {}, "open-meteo-forecast-maubin").map(row => ({
    date: row.observedDate,
    precipitationMm: row.precipitationMm,
  }));
}

export async function refreshCurrentMonthRainfall() {
  const now = new Date();
  const start = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  const end = dayBefore(now);
  if (end < start) return { inserted: 0, skipped: "No completed days in the current month" };

  const url = new URL(OPEN_METEO_ARCHIVE_URL);
  url.searchParams.set("latitude", String(MAUBIN.latitude));
  url.searchParams.set("longitude", String(MAUBIN.longitude));
  url.searchParams.set("start_date", isoDate(start));
  url.searchParams.set("end_date", isoDate(end));
  url.searchParams.set("daily", "precipitation_sum");
  url.searchParams.set("timezone", "Asia/Yangon");

  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Open-Meteo ERA5 request failed (${response.status})`);
  const payload = (await response.json()) as OpenMeteoResponse;
  const records = buildRainfallRecords(payload.daily ?? {}, "open-meteo-era5-maubin");
  const db = await getDb();
  if (!db) throw new Error("Database unavailable for rainfall_history upsert");

  for (const record of records) {
    await db
      .insert(rainfallHistory)
      .values({
        sourceKey: record.sourceKey,
        observedDate: record.observedDate,
        precipitationMm: record.precipitationMm.toFixed(2),
        accumulation7dMm: record.accumulation7dMm.toFixed(2),
      })
      .onDuplicateKeyUpdate({
        set: {
          precipitationMm: record.precipitationMm.toFixed(2),
          accumulation7dMm: record.accumulation7dMm.toFixed(2),
          updatedAt: new Date(),
        },
      });
  }

  return { inserted: records.length, startDate: isoDate(start), endDate: isoDate(end) };
}

export async function listStoredRainfall() {
  const db = await getDb();
  if (!db) return [];
  const rows = await db.select().from(rainfallHistory).orderBy(desc(rainfallHistory.observedDate)).limit(30);
  return rows.reverse().map(row => ({ date: row.observedDate, precipitationMm: Number(row.precipitationMm) }));
}

export async function getScheduleConfig(key: string) {
  const db = await getDb();
  if (!db) return null;
  const rows = await db.select().from(scheduleConfigs).where(eq(scheduleConfigs.key, key)).limit(1);
  return rows[0] ?? null;
}

export async function recordScheduleResult(key: string, taskUid: string, result: unknown) {
  const db = await getDb();
  if (!db) throw new Error("Database unavailable for schedule state");
  await db
    .insert(scheduleConfigs)
    .values({ key, scheduleCronTaskUid: taskUid, lastRunAt: new Date(), lastResult: JSON.stringify(result) })
    .onDuplicateKeyUpdate({
      set: { scheduleCronTaskUid: taskUid, lastRunAt: new Date(), lastResult: JSON.stringify(result) },
    });
}

export const monitoringStatus = {
  spatialDb: "online",
  openAlerts: 0,
  riskBasis: "terrain_screening",
  modelVersion: "maubin-flood-event-logistic-v6",
  modelStatus: "experimental",
  alertReadiness: {
    mode: "disabled",
    label: "Monitoring only",
    delivery: "dashboard_only",
    reason: "No validated local river-stage or calibrated Maubin coastal-water record is available.",
  },
} as const;
