import { describe, expect, it } from "vitest";
import { appRouter } from "./routers";
import type { TrpcContext } from "./_core/context";

describe("monitoring.status", () => {
  it("exposes the exact terrain-screening risk basis used by the status bar", async () => {
    const caller = appRouter.createCaller({
      user: null,
      req: {} as TrpcContext["req"],
      res: {} as TrpcContext["res"],
    });

    await expect(caller.monitoring.status()).resolves.toMatchObject({
      riskBasis: "terrain_screening",
      openAlerts: 0,
      spatialDb: "online",
      modelVersion: "maubin-flood-event-logistic-v6",
      modelStatus: "experimental",
      alertReadiness: {
        mode: "disabled",
        label: "Monitoring only",
        delivery: "dashboard_only",
      },
    });
  });
});
