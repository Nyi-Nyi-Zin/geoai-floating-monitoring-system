import { describe, expect, it } from "vitest";
import { appRouter } from "./routers";
import type { TrpcContext } from "./_core/context";

const observationInput = {
  observedAt: new Date("2026-08-16T18:00:00Z"), latitude: 16.7247, longitude: 95.6687,
  impactClass: "flooded" as const, locationAccuracyM: null, waterDepthCm: null, notes: null, photo: null,
};

describe("field observation access controls", () => {
  it("rejects anonymous evidence submissions before any storage or database write", async () => {
    const caller = appRouter.createCaller({ user: null, req: {} as TrpcContext["req"], res: {} as TrpcContext["res"] });
    await expect(caller.observations.submit(observationInput)).rejects.toMatchObject({ code: "UNAUTHORIZED" });
  });

  it("rejects non-admin evidence review attempts", async () => {
    const caller = appRouter.createCaller({
      user: { id: 42, openId: "field-reporter", name: "Field reporter", email: null, loginMethod: "manus", role: "user", createdAt: new Date(), updatedAt: new Date(), lastSignedIn: new Date() },
      req: {} as TrpcContext["req"], res: {} as TrpcContext["res"],
    });
    await expect(caller.observations.review({ id: 1, reviewStatus: "verified", reviewNotes: "Evidence reviewed." })).rejects.toMatchObject({ code: "FORBIDDEN" });
  });
});
