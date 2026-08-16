import { decimal, int, json, mysqlEnum, mysqlTable, text, timestamp, uniqueIndex, varchar } from "drizzle-orm/mysql-core";

export const users = mysqlTable("users", {
  id: int("id").autoincrement().primaryKey(),
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["admin", "user"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export const rainfallHistory = mysqlTable("rainfall_history", {
  id: int("id").autoincrement().primaryKey(),
  sourceKey: varchar("source_key", { length: 120 }).notNull(),
  observedDate: varchar("observed_date", { length: 10 }).notNull(),
  precipitationMm: decimal("precipitation_mm", { precision: 8, scale: 2 }).notNull(),
  accumulation7dMm: decimal("accumulation_7d_mm", { precision: 9, scale: 2 }).notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().onUpdateNow().notNull(),
}, table => [uniqueIndex("rainfall_history_source_date").on(table.sourceKey, table.observedDate)]);

export const scheduleConfigs = mysqlTable("schedule_configs", {
  id: int("id").autoincrement().primaryKey(),
  key: varchar("key", { length: 80 }).notNull().unique(),
  scheduleCronTaskUid: varchar("schedule_cron_task_uid", { length: 65 }),
  lastRunAt: timestamp("last_run_at"),
  lastResult: json("last_result"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().onUpdateNow().notNull(),
});

export const prospectiveForecastSnapshots = mysqlTable("prospective_forecast_snapshots", {
  id: int("id").autoincrement().primaryKey(),
  sourceKey: varchar("source_key", { length: 120 }).notNull(),
  issueKey: varchar("issue_key", { length: 32 }).notNull(),
  issueTime: timestamp("issue_time").notNull(),
  targetDate: varchar("target_date", { length: 10 }).notNull(),
  horizonDays: int("horizon_days").notNull(),
  rainfallLag1dMm: decimal("rainfall_lag_1d_mm", { precision: 9, scale: 2 }).notNull(),
  rainfallLag3dMm: decimal("rainfall_lag_3d_mm", { precision: 9, scale: 2 }).notNull(),
  rainfallLag7dMm: decimal("rainfall_lag_7d_mm", { precision: 9, scale: 2 }).notNull(),
  rainfallLag14dMm: decimal("rainfall_lag_14d_mm", { precision: 9, scale: 2 }).notNull(),
  rainfallLag30dMm: decimal("rainfall_lag_30d_mm", { precision: 9, scale: 2 }).notNull(),
  dischargeLag1dM3s: decimal("discharge_lag_1d_m3s", { precision: 12, scale: 2 }).notNull(),
  dischargeLag3dM3s: decimal("discharge_lag_3d_m3s", { precision: 12, scale: 2 }).notNull(),
  dischargeLag7dM3s: decimal("discharge_lag_7d_m3s", { precision: 12, scale: 2 }).notNull(),
  dischargeLag14dM3s: decimal("discharge_lag_14d_m3s", { precision: 12, scale: 2 }).notNull(),
  dischargeLag30dM3s: decimal("discharge_lag_30d_m3s", { precision: 12, scale: 2 }).notNull(),
  dischargeP25M3s: decimal("discharge_p25_m3s", { precision: 12, scale: 2 }),
  dischargeP75M3s: decimal("discharge_p75_m3s", { precision: 12, scale: 2 }),
  deepSoilMoisture: decimal("deep_soil_moisture", { precision: 9, scale: 5 }),
  projectionStatus: varchar("projection_status", { length: 64 }).notNull(),
  modelVersion: varchar("model_version", { length: 120 }).notNull(),
  inputCoverage: json("input_coverage").notNull(),
  qualityFlags: json("quality_flags").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().onUpdateNow().notNull(),
}, table => [uniqueIndex("prospective_forecast_issue_target").on(table.sourceKey, table.issueKey, table.targetDate)]);

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;
