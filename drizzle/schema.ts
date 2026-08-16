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

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;
