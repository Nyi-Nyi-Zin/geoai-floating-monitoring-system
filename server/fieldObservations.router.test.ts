import { describe, expect, it, vi } from "vitest";
import { appRouter } from "./routers";
import type { TrpcContext } from "./_core/context";

const mocked = vi.hoisted(() => ({
  contributorId: vi.fn(async () => 73),
  submitObservation: vi.fn(async () => ({ id: 92, reviewStatus: "submitted" as const, photoStored: false })),
}));

vi.mock("./anonymousContributor", () => ({ getAnonymousContributorId: mocked.contributorId }));
vi.mock("./fieldObservations", () => ({
  impactClasses: ["flooded", "water_on_road", "access_disrupted", "no_flood_observed"],
  reviewStatuses: ["submitted", "verified", "rejected"],
  submitObservation: mocked.submitObservation,
  reviewObservation: vi.fn(),
  getObservationSummary: vi.fn(),
  listMyObservations: vi.fn(),
  listReviewQueue: vi.fn(),
}));

const observationInput = {
  observedAt: new Date("2026-08-16T18:00:00Z"), latitude: 16.7247, longitude: 95.6687,
  impactClass: "flooded" as const, locationAccuracyM: null, waterDepthCm: null, notes: null, photo: null,
};

describe("field observation access controls", () => {
  it("accepts anonymous evidence submissions through a non-identifying contributor record", async () => {
    const caller = appRouter.createCaller({ user: null, req: {} as TrpcContext["req"], res: {} as TrpcContext["res"] });
    await expect(caller.observations.submit(observationInput)).resolves.toEqual({ id: 92, reviewStatus: "submitted", photoStored: false });
    expect(mocked.contributorId).toHaveBeenCalled();
    expect(mocked.submitObservation).toHaveBeenCalledWith(73, expect.objectContaining({ impactClass: "flooded" }));
  });

  it("rejects non-admin evidence review attempts", async () => {
    const caller = appRouter.createCaller({
      user: { id: 42, openId: "field-reporter", name: "Field reporter", email: null, loginMethod: "manus", role: "user", createdAt: new Date(), updatedAt: new Date(), lastSignedIn: new Date() },
      req: {} as TrpcContext["req"], res: {} as TrpcContext["res"],
    });
    await expect(caller.observations.review({ id: 1, reviewStatus: "verified", reviewNotes: "Evidence reviewed." })).rejects.toMatchObject({ code: "FORBIDDEN" });
  });
});
