import { describe, expect, it, vi } from "vitest";
import type { TrpcContext } from "./_core/context";

const mocked = vi.hoisted(() => ({ submitObservation: vi.fn(), reviewObservation: vi.fn() }));

vi.mock("./fieldObservations", () => ({
  impactClasses: ["flooded", "water_on_road", "access_disrupted", "no_flood_observed"],
  reviewStatuses: ["submitted", "verified", "rejected"],
  submitObservation: mocked.submitObservation,
  reviewObservation: mocked.reviewObservation,
  getObservationSummary: vi.fn(),
  listMyObservations: vi.fn(),
  listReviewQueue: vi.fn(),
}));

import { appRouter } from "./routers";

const reporter = { id: 21, openId: "field-reporter", name: "Reporter", email: null, loginMethod: "manus", role: "user" as const, createdAt: new Date(), updatedAt: new Date(), lastSignedIn: new Date() };
const administrator = { ...reporter, id: 1, openId: "field-admin", role: "admin" as const };

describe("field observation protected router success paths", () => {
  it("passes an authenticated report through the protected API to persistence", async () => {
    mocked.submitObservation.mockResolvedValueOnce({ id: 91, reviewStatus: "submitted", photoStored: false });
    const caller = appRouter.createCaller({ user: reporter, req: {} as TrpcContext["req"], res: {} as TrpcContext["res"] });
    const input = { observedAt: new Date("2026-08-16T18:00:00Z"), latitude: 16.7247, longitude: 95.6687, impactClass: "flooded" as const, locationAccuracyM: null, waterDepthCm: 18, notes: "Observed water on the access road.", photo: null };
    await expect(caller.observations.submit(input)).resolves.toEqual({ id: 91, reviewStatus: "submitted", photoStored: false });
    expect(mocked.submitObservation).toHaveBeenCalledWith(21, expect.objectContaining({ latitude: 16.7247, longitude: 95.6687, impactClass: "flooded" }));
  });

  it("passes an administrator review and rationale through the protected API to persistence", async () => {
    mocked.reviewObservation.mockResolvedValueOnce({ id: 91, reviewStatus: "verified" });
    const caller = appRouter.createCaller({ user: administrator, req: {} as TrpcContext["req"], res: {} as TrpcContext["res"] });
    await expect(caller.observations.review({ id: 91, reviewStatus: "verified", reviewNotes: "Coordinates and photo reviewed." })).resolves.toEqual({ id: 91, reviewStatus: "verified" });
    expect(mocked.reviewObservation).toHaveBeenCalledWith(91, 1, "verified", "Coordinates and photo reviewed.");
  });

  it("does not bypass an immutable-review service rejection through the protected API", async () => {
    mocked.reviewObservation.mockRejectedValueOnce(new Error("Field observation has already been reviewed and cannot be changed"));
    const caller = appRouter.createCaller({ user: administrator, req: {} as TrpcContext["req"], res: {} as TrpcContext["res"] });
    await expect(caller.observations.review({ id: 91, reviewStatus: "rejected", reviewNotes: "A second review is not permitted." })).rejects.toThrow("already been reviewed");
  });
});
