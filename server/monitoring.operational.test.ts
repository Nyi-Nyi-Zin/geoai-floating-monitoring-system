import { describe, expect, it } from "vitest";
import { desc } from "drizzle-orm";
import { rainfallHistory } from "../drizzle/schema";
import type { TrpcContext } from "./_core/context";
import { getDb } from "./db";
import { summarizeScheduleHealth } from "./monitoring";
import { appRouter } from "./routers";

describe("monitoring operational health disclosure", () => {
  it("returns sanitized job and freshness status without exposing scheduler task identifiers", async () => {
    const caller = appRouter.createCaller({ user: null, req: {} as TrpcContext["req"], res: {} as TrpcContext["res"] });
    const health = await caller.monitoring.operationalStatus();
    expect(health.jobs).toEqual(expect.arrayContaining([
      expect.objectContaining({ key: "nightly-rainfall-refresh", label: "ERA5 rainfall refresh", expectedIntervalHours: 24 }),
      expect.objectContaining({ key: "six-hour-prospective-monitoring-refresh", label: "Prospective input refresh", expectedIntervalHours: 6 }),
    ]));
    expect(health.jobs.every(job => !("taskUid" in job))).toBe(true);
    expect(["current", "late", "not_yet_available", "unavailable"]).toContain(health.prospectiveInputs.state);
    const db = await getDb();
    const latest = await db?.select({ observedDate: rainfallHistory.observedDate }).from(rainfallHistory).orderBy(desc(rainfallHistory.observedDate)).limit(1);
    expect(health.rainfallHistory.latestObservedDate).toBe(latest?.[0]?.observedDate ?? null);
  });

  it("classifies a persisted prospective-refresh failure as failed without disclosing raw error details", () => {
    expect(summarizeScheduleHealth(new Date("2026-08-16T18:00:00Z"), { status: "failed", errorCode: "prospective_refresh_failed" }, 6, new Date("2026-08-16T19:00:00Z"))).toEqual({ state: "failed", lastResultStatus: "failed" });
  });
});
