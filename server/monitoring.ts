import { and, desc, eq } from "drizzle-orm";
import { prospectiveForecastSnapshots, rainfallHistory, scheduleConfigs } from "../drizzle/schema";
import { getDb } from "./db";
import { storageGetSignedUrl } from "./storage";

const MAUBIN = { latitude: 16.7247, longitude: 95.6687 };
const OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast";
const OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive";
const OPEN_METEO_FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood";
const PROSPECTIVE_SOURCE_KEY = "open-meteo-glofas-maubin-six-hour";
const PROSPECTIVE_MODEL_VERSION = "maubin-flood-event-hgb-v7";
const PROSPECTIVE_STATIC_SEED_KEY = "maubin_v7_static_feature_seed_5b153949.json";

export type WeatherPoint = { date: string; precipitationMm: number };
export type ProspectiveMonitoringSummary = {
  mode: "monitoring_only";
  label: "Prospective input monitoring";
  readiness: "pending_prospective_validation";
  latestIssueTime: string | null;
  targetDate: string | null;
  horizonDays: number | null;
  projectionStatus: string;
  qualityFlags: string[];
  reason: string;
};

type OpenMeteoDaily = { time?: string[]; precipitation_sum?: Array<number | null> };
type OpenMeteoResponse = { daily?: OpenMeteoDaily };
type ForecastHourly = { time?: string[]; precipitation?: Array<number | null>; soil_moisture_27_to_81cm?: Array<number | null> };
type ForecastResponse = { hourly?: ForecastHourly };
type FloodDaily = { time?: string[]; river_discharge?: Array<number | null>; river_discharge_p25?: Array<number | null>; river_discharge_p75?: Array<number | null> };
type FloodResponse = { daily?: FloodDaily };
export type V7StaticFeatureCell = {
  cell_id: string;
  elevation_mean_m: number;
  elevation_percentile: number;
  local_relief_m: number;
  distance_to_waterway_m: number;
  land_cover_dominant_code: number;
  osm_drainage_distance_m: number;
  osm_levee_distance_m: number;
};
export type StaticSeed = { schema: string; model_version: string; cell_count: number; cells: V7StaticFeatureCell[] };
export type V7DynamicProjectionFeatures = {
  rainfall_lag_1d_mm: number; rainfall_lag_3d_mm: number; rainfall_lag_7d_mm: number; rainfall_lag_14d_mm: number; rainfall_lag_30d_mm: number;
  discharge_lag_1d_m3s: number; discharge_lag_3d_m3s: number; discharge_lag_7d_m3s: number; discharge_lag_14d_m3s: number; discharge_lag_30d_m3s: number;
};
let staticSeedCache: StaticSeed | null = null;

function isoDate(date: Date) { return date.toISOString().slice(0, 10); }
function dayBefore(date: Date) { const value = new Date(date); value.setUTCDate(value.getUTCDate() - 1); return value; }
function addDays(date: Date, days: number) { const value = new Date(date); value.setUTCDate(value.getUTCDate() + days); return value; }
function dateAtMidnight(date: string) { return new Date(`${date}T00:00:00.000Z`); }
function numberValue(value: number | null | undefined) { return Math.max(0, Number(value ?? 0)); }

function sixHourIssue(now = new Date()) {
  const issueTime = new Date(now);
  issueTime.setUTCMinutes(0, 0, 0);
  issueTime.setUTCHours(Math.floor(issueTime.getUTCHours() / 6) * 6);
  return { issueTime, issueKey: `${issueTime.toISOString().slice(0, 13).replace(/[-:T]/g, "")}Z` };
}

function dailyRainfall(hourly: ForecastHourly) {
  const totals = new Map<string, number>();
  for (let index = 0; index < (hourly.time ?? []).length; index++) {
    const date = String(hourly.time?.[index] ?? "").slice(0, 10);
    if (!date) continue;
    totals.set(date, (totals.get(date) ?? 0) + numberValue(hourly.precipitation?.[index]));
  }
  return totals;
}

function dailyValues(times: string[] | undefined, values: Array<number | null> | undefined) {
  const output = new Map<string, number>();
  for (let index = 0; index < (times ?? []).length; index++) output.set(String(times?.[index] ?? ""), numberValue(values?.[index]));
  return output;
}

function priorTotal(values: Map<string, number>, targetDate: string, days: number) {
  let total = 0; let coverage = 0;
  const target = dateAtMidnight(targetDate);
  for (let offset = 1; offset <= days; offset++) {
    const value = values.get(isoDate(addDays(target, -offset)));
    if (value !== undefined) { total += value; coverage++; }
  }
  return { total, coverage };
}

function hourlyValueAtOrAfter(hourly: ForecastHourly, targetDate: string) {
  const target = `${targetDate}T00:00`;
  const index = (hourly.time ?? []).findIndex(time => time >= target);
  return index < 0 ? null : Number(hourly.soil_moisture_27_to_81cm?.[index] ?? null);
}

function jsonValue(value: unknown) {
  if (typeof value === "string") {
    try { return JSON.parse(value); } catch { return value; }
  }
  return value;
}

async function loadProspectiveStaticSeed() {
  if (staticSeedCache) return staticSeedCache;
  const signedUrl = await storageGetSignedUrl(PROSPECTIVE_STATIC_SEED_KEY);
  const response = await fetch(signedUrl, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Prospective static feature seed request failed (${response.status})`);
  const seed = (await response.json()) as StaticSeed;
  if (seed.schema !== "maubin-v7-static-cell-features-v1" || seed.model_version !== PROSPECTIVE_MODEL_VERSION || seed.cell_count !== seed.cells?.length || seed.cell_count !== 5549) throw new Error("Prospective static feature seed failed validation");
  staticSeedCache = seed;
  return seed;
}

export function projectV7FeaturesForCells(cells: V7StaticFeatureCell[], dynamic: V7DynamicProjectionFeatures) {
  return cells.map(cell => ({ ...cell, ...dynamic }));
}

type StoredProjectionInputs = Pick<typeof prospectiveForecastSnapshots.$inferSelect,
  "sourceKey" | "issueKey" | "issueTime" | "targetDate" | "horizonDays" | "rainfallLag1dMm" | "rainfallLag3dMm" | "rainfallLag7dMm" | "rainfallLag14dMm" | "rainfallLag30dMm" | "dischargeLag1dM3s" | "dischargeLag3dM3s" | "dischargeLag7dM3s" | "dischargeLag14dM3s" | "dischargeLag30dM3s" | "projectionStatus" | "modelVersion" | "qualityFlags"
>;

export function buildProjectionFromStoredInputs(snapshot: StoredProjectionInputs, staticSeed: StaticSeed) {
  const dynamic: V7DynamicProjectionFeatures = {
    rainfall_lag_1d_mm: Number(snapshot.rainfallLag1dMm), rainfall_lag_3d_mm: Number(snapshot.rainfallLag3dMm), rainfall_lag_7d_mm: Number(snapshot.rainfallLag7dMm), rainfall_lag_14d_mm: Number(snapshot.rainfallLag14dMm), rainfall_lag_30d_mm: Number(snapshot.rainfallLag30dMm),
    discharge_lag_1d_m3s: Number(snapshot.dischargeLag1dM3s), discharge_lag_3d_m3s: Number(snapshot.dischargeLag3dM3s), discharge_lag_7d_m3s: Number(snapshot.dischargeLag7dM3s), discharge_lag_14d_m3s: Number(snapshot.dischargeLag14dM3s), discharge_lag_30d_m3s: Number(snapshot.dischargeLag30dM3s),
  };
  return {
    issueKey: snapshot.issueKey,
    issueTime: snapshot.issueTime.toISOString(),
    targetDate: snapshot.targetDate,
    horizonDays: snapshot.horizonDays,
    modelVersion: snapshot.modelVersion,
    projectionStatus: snapshot.projectionStatus,
    staticFeatureCellCount: staticSeed.cell_count,
    qualityFlags: Array.isArray(jsonValue(snapshot.qualityFlags)) ? (jsonValue(snapshot.qualityFlags) as unknown[]).map(String) : ["invalid_quality_flags"],
    cells: projectV7FeaturesForCells(staticSeed.cells, dynamic),
  };
}

export function buildRainfallRecords(daily: OpenMeteoDaily, sourceKey: string) {
  const values = daily.precipitation_sum ?? [];
  const dates = daily.time ?? [];
  return dates.map((observedDate, index) => {
    const precipitationMm = Math.max(0, Number(values[index] ?? 0));
    const prior = values.slice(Math.max(0, index - 6), index + 1).reduce<number>((total, value) => total + Math.max(0, Number(value ?? 0)), 0);
    return { sourceKey, observedDate, precipitationMm, accumulation7dMm: prior };
  });
}

export async function getWeatherSnapshot() {
  const url = new URL(OPEN_METEO_FORECAST_URL);
  url.searchParams.set("latitude", String(MAUBIN.latitude)); url.searchParams.set("longitude", String(MAUBIN.longitude));
  url.searchParams.set("daily", "precipitation_sum"); url.searchParams.set("forecast_days", "7"); url.searchParams.set("timezone", "Asia/Yangon");
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Open-Meteo forecast request failed (${response.status})`);
  const payload = (await response.json()) as OpenMeteoResponse;
  return buildRainfallRecords(payload.daily ?? {}, "open-meteo-forecast-maubin").map(row => ({ date: row.observedDate, precipitationMm: row.precipitationMm }));
}

export async function refreshCurrentMonthRainfall() {
  const now = new Date(); const start = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1)); const end = dayBefore(now);
  if (end < start) return { inserted: 0, skipped: "No completed days in the current month" };
  const url = new URL(OPEN_METEO_ARCHIVE_URL);
  url.searchParams.set("latitude", String(MAUBIN.latitude)); url.searchParams.set("longitude", String(MAUBIN.longitude));
  url.searchParams.set("start_date", isoDate(start)); url.searchParams.set("end_date", isoDate(end)); url.searchParams.set("daily", "precipitation_sum"); url.searchParams.set("timezone", "Asia/Yangon");
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Open-Meteo ERA5 request failed (${response.status})`);
  const payload = (await response.json()) as OpenMeteoResponse; const records = buildRainfallRecords(payload.daily ?? {}, "open-meteo-era5-maubin");
  const db = await getDb(); if (!db) throw new Error("Database unavailable for rainfall_history upsert");
  for (const record of records) await db.insert(rainfallHistory).values({ sourceKey: record.sourceKey, observedDate: record.observedDate, precipitationMm: record.precipitationMm.toFixed(2), accumulation7dMm: record.accumulation7dMm.toFixed(2) }).onDuplicateKeyUpdate({ set: { precipitationMm: record.precipitationMm.toFixed(2), accumulation7dMm: record.accumulation7dMm.toFixed(2), updatedAt: new Date() } });
  return { inserted: records.length, startDate: isoDate(start), endDate: isoDate(end) };
}

export async function refreshProspectiveMonitoring(now = new Date()) {
  const { issueTime, issueKey } = sixHourIssue(now);
  const [weatherResponse, floodResponse] = await Promise.all([
    fetch(`${OPEN_METEO_FORECAST_URL}?latitude=${MAUBIN.latitude}&longitude=${MAUBIN.longitude}&hourly=precipitation,soil_moisture_27_to_81cm&past_days=35&forecast_days=16&timezone=UTC`, { headers: { Accept: "application/json" } }),
    fetch(`${OPEN_METEO_FLOOD_URL}?latitude=${MAUBIN.latitude}&longitude=${MAUBIN.longitude}&daily=river_discharge,river_discharge_p25,river_discharge_p75&past_days=35&forecast_days=30&timezone=UTC`, { headers: { Accept: "application/json" } }),
  ]);
  if (!weatherResponse.ok) throw new Error(`Open-Meteo prospective weather request failed (${weatherResponse.status})`);
  if (!floodResponse.ok) throw new Error(`Open-Meteo prospective discharge request failed (${floodResponse.status})`);
  const weather = (await weatherResponse.json()) as ForecastResponse;
  const flood = (await floodResponse.json()) as FloodResponse;
  const staticSeed = await loadProspectiveStaticSeed();
  const rainfall = dailyRainfall(weather.hourly ?? {});
  const discharge = dailyValues(flood.daily?.time, flood.daily?.river_discharge);
  const p25 = dailyValues(flood.daily?.time, flood.daily?.river_discharge_p25);
  const p75 = dailyValues(flood.daily?.time, flood.daily?.river_discharge_p75);
  const issueDate = isoDate(issueTime);
  const targetDates = (flood.daily?.time ?? []).filter(date => date >= issueDate && date <= isoDate(addDays(issueTime, 7)));
  const db = await getDb(); if (!db) throw new Error("Database unavailable for prospective forecast snapshots");
  let inserted = 0; let skipped = 0;
  for (const targetDate of targetDates) {
    const rainfallWindows = [1, 3, 7, 14, 30].map(days => priorTotal(rainfall, targetDate, days));
    const dischargeWindows = [1, 3, 7, 14, 30].map(days => priorTotal(discharge, targetDate, days));
    const weatherCoverage = Math.min(...rainfallWindows.map(window => window.coverage));
    const dischargeCoverage = Math.min(...dischargeWindows.map(window => window.coverage));
    const dynamicFeatures: V7DynamicProjectionFeatures = {
      rainfall_lag_1d_mm: rainfallWindows[0].total, rainfall_lag_3d_mm: rainfallWindows[1].total, rainfall_lag_7d_mm: rainfallWindows[2].total, rainfall_lag_14d_mm: rainfallWindows[3].total, rainfall_lag_30d_mm: rainfallWindows[4].total,
      discharge_lag_1d_m3s: dischargeWindows[0].total, discharge_lag_3d_m3s: dischargeWindows[1].total, discharge_lag_7d_m3s: dischargeWindows[2].total, discharge_lag_14d_m3s: dischargeWindows[3].total, discharge_lag_30d_m3s: dischargeWindows[4].total,
    };
    const modelReadyCellFeatures = projectV7FeaturesForCells(staticSeed.cells, dynamicFeatures);
    if (modelReadyCellFeatures.length !== staticSeed.cell_count) throw new Error("Prospective per-cell feature projection count mismatch");
    const qualityFlags = [
      "monitoring_only_no_flood_probability",
      "no_validated_local_stage_or_tide",
      "glofas_discharge_proxy_5km",
      "per_cell_v7_features_projected_no_probability",
      "prospective_validation_pending",
      ...(weatherCoverage < 1 ? ["missing_rainfall_antecedent_coverage"] : []),
      ...(dischargeCoverage < 1 ? ["missing_discharge_antecedent_coverage"] : []),
    ];
    const existing = await db.select({ id: prospectiveForecastSnapshots.id }).from(prospectiveForecastSnapshots).where(and(eq(prospectiveForecastSnapshots.sourceKey, PROSPECTIVE_SOURCE_KEY), eq(prospectiveForecastSnapshots.issueKey, issueKey), eq(prospectiveForecastSnapshots.targetDate, targetDate))).limit(1);
    if (existing.length) { skipped++; continue; }
    const horizonDays = Math.round((dateAtMidnight(targetDate).getTime() - dateAtMidnight(issueDate).getTime()) / 86_400_000);
    await db.insert(prospectiveForecastSnapshots).values({
      sourceKey: PROSPECTIVE_SOURCE_KEY, issueKey, issueTime, targetDate, horizonDays,
      rainfallLag1dMm: dynamicFeatures.rainfall_lag_1d_mm.toFixed(2), rainfallLag3dMm: dynamicFeatures.rainfall_lag_3d_mm.toFixed(2), rainfallLag7dMm: dynamicFeatures.rainfall_lag_7d_mm.toFixed(2), rainfallLag14dMm: dynamicFeatures.rainfall_lag_14d_mm.toFixed(2), rainfallLag30dMm: dynamicFeatures.rainfall_lag_30d_mm.toFixed(2),
      dischargeLag1dM3s: dynamicFeatures.discharge_lag_1d_m3s.toFixed(2), dischargeLag3dM3s: dynamicFeatures.discharge_lag_3d_m3s.toFixed(2), dischargeLag7dM3s: dynamicFeatures.discharge_lag_7d_m3s.toFixed(2), dischargeLag14dM3s: dynamicFeatures.discharge_lag_14d_m3s.toFixed(2), dischargeLag30dM3s: dynamicFeatures.discharge_lag_30d_m3s.toFixed(2),
      dischargeP25M3s: p25.get(targetDate)?.toFixed(2) ?? null, dischargeP75M3s: p75.get(targetDate)?.toFixed(2) ?? null, deepSoilMoisture: hourlyValueAtOrAfter(weather.hourly ?? {}, targetDate)?.toFixed(5) ?? null,
      projectionStatus: "per_cell_v7_features_no_probability", modelVersion: PROSPECTIVE_MODEL_VERSION,
      inputCoverage: { weatherHourCount: weather.hourly?.time?.length ?? 0, rainfallDayCount: rainfall.size, dischargeDayCount: discharge.size, weatherAntecedentCoverageDays: weatherCoverage, dischargeAntecedentCoverageDays: dischargeCoverage, forecastCoordinates: MAUBIN, staticFeatureSeed: `/manus-storage/${PROSPECTIVE_STATIC_SEED_KEY}`, staticFeatureCellCount: staticSeed.cell_count, projectedFeatureCount: modelReadyCellFeatures.length },
      qualityFlags,
    });
    inserted++;
  }
  return { issueKey, issueTime: issueTime.toISOString(), inserted, skipped, targetCount: targetDates.length, monitoringOnly: true };
}

export async function listStoredRainfall() {
  const db = await getDb(); if (!db) return [];
  const rows = await db.select().from(rainfallHistory).orderBy(desc(rainfallHistory.observedDate)).limit(30);
  return rows.reverse().map(row => ({ date: row.observedDate, precipitationMm: Number(row.precipitationMm) }));
}

export async function getLatestProspectiveMonitoring(): Promise<ProspectiveMonitoringSummary> {
  const db = await getDb();
  const base = { mode: "monitoring_only" as const, label: "Prospective input monitoring" as const, readiness: "pending_prospective_validation" as const, reason: "Forecast rainfall and GloFAS proxy inputs are logged for prospective validation; no flood probability or alert is emitted." };
  if (!db) return { ...base, latestIssueTime: null, targetDate: null, horizonDays: null, projectionStatus: "database_unavailable", qualityFlags: ["database_unavailable"] };
  const rows = await db.select().from(prospectiveForecastSnapshots).orderBy(desc(prospectiveForecastSnapshots.issueTime), desc(prospectiveForecastSnapshots.targetDate)).limit(1);
  const row = rows[0];
  if (!row) return { ...base, latestIssueTime: null, targetDate: null, horizonDays: null, projectionStatus: "awaiting_first_six_hour_refresh", qualityFlags: ["awaiting_first_six_hour_refresh"] };
  const flags = jsonValue(row.qualityFlags);
  return { ...base, latestIssueTime: row.issueTime.toISOString(), targetDate: row.targetDate, horizonDays: row.horizonDays, projectionStatus: row.projectionStatus, qualityFlags: Array.isArray(flags) ? flags.map(String) : ["invalid_quality_flags"] };
}

export async function getProspectiveFeatureProjection(issueKey: string, targetDate: string) {
  const db = await getDb();
  if (!db) throw new Error("Database unavailable for prospective feature projection");
  const rows = await db.select().from(prospectiveForecastSnapshots).where(and(
    eq(prospectiveForecastSnapshots.sourceKey, PROSPECTIVE_SOURCE_KEY),
    eq(prospectiveForecastSnapshots.issueKey, issueKey),
    eq(prospectiveForecastSnapshots.targetDate, targetDate),
  )).limit(1);
  if (!rows[0]) return null;
  return buildProjectionFromStoredInputs(rows[0], await loadProspectiveStaticSeed());
}

export async function getScheduleConfig(key: string) { const db = await getDb(); if (!db) return null; const rows = await db.select().from(scheduleConfigs).where(eq(scheduleConfigs.key, key)).limit(1); return rows[0] ?? null; }
export async function recordScheduleResult(key: string, taskUid: string, result: unknown) { const db = await getDb(); if (!db) throw new Error("Database unavailable for schedule state"); await db.insert(scheduleConfigs).values({ key, scheduleCronTaskUid: taskUid, lastRunAt: new Date(), lastResult: JSON.stringify(result) }).onDuplicateKeyUpdate({ set: { scheduleCronTaskUid: taskUid, lastRunAt: new Date(), lastResult: JSON.stringify(result) } }); }

export const monitoringStatus = {
  spatialDb: "online",
  openAlerts: 0,
  riskBasis: "terrain_screening",
  modelVersion: PROSPECTIVE_MODEL_VERSION,
  modelStatus: "experimental",
  alertReadiness: { mode: "disabled", label: "Monitoring only", delivery: "dashboard_only", reason: "No validated local river-stage or calibrated Maubin coastal-water record is available." },
  prospectiveReadiness: { mode: "inputs_only", label: "Prospective monitoring", delivery: "dashboard_only", reason: "Forecast inputs are logged every six hours for validation; no live flood probability or public alert is produced." },
} as const;
