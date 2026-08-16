import { desc } from "drizzle-orm";
import { describe, expect, it } from "vitest";
import { prospectiveForecastSnapshots } from "../drizzle/schema";
import { getDb } from "./db";
import type { TrpcContext } from "./_core/context";
import { appRouter } from "./routers";

describe("prospective feature retrieval integration", () => {
  it("retrieves the persisted latest target's full per-cell v7 context without returning a score, label, or alert", async () => {
    const db = await getDb();
    expect(db).not.toBeNull();
    const latest = (await db!.select({ issueKey: prospectiveForecastSnapshots.issueKey, targetDate: prospectiveForecastSnapshots.targetDate })
      .from(prospectiveForecastSnapshots)
      .orderBy(desc(prospectiveForecastSnapshots.issueTime), desc(prospectiveForecastSnapshots.targetDate))
      .limit(1))[0];
    expect(latest).toBeDefined();

    const caller = appRouter.createCaller({ user: null, req: {} as TrpcContext["req"], res: {} as TrpcContext["res"] });
    const result = await caller.monitoring.prospectiveFeatures({ issueKey: latest.issueKey, targetDate: latest.targetDate });
    expect(result).not.toBeNull();
    expect(result).toMatchObject({ issueKey: latest.issueKey, targetDate: latest.targetDate, staticFeatureCellCount: 5549, projectionStatus: "per_cell_v7_features_no_probability" });
    expect(result!.cells).toHaveLength(5549);
    expect(result!.cells[0]).toHaveProperty("elevation_mean_m");
    expect(result!.cells[0]).toHaveProperty("rainfall_lag_30d_mm");
    expect(result!.cells[0]).not.toHaveProperty("probability");
    expect(result!.cells[0]).not.toHaveProperty("predicted_label");
    expect(result!.cells[0]).not.toHaveProperty("alert");
  }, 30000);
});
