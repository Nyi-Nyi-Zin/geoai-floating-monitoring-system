import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({ inserted: [] as Record<string, unknown>[], reviews: [] as Record<string, unknown>[], storagePut: vi.fn() }));

vi.mock("./db", () => ({
  getDb: vi.fn(async () => ({
    insert: vi.fn(() => ({ values: vi.fn((values: Record<string, unknown>) => { state.inserted.push(values); return { $returningId: async () => [{ id: 77 }] }; }) })),
    update: vi.fn(() => ({ set: vi.fn((values: Record<string, unknown>) => { state.reviews.push(values); return { where: vi.fn(async () => undefined) }; }) })),
  })),
}));

vi.mock("./storage", () => ({
  storagePut: state.storagePut,
  storageGet: vi.fn(),
}));

import { reviewObservation, submitObservation } from "./fieldObservations";

describe("field observation success paths", () => {
  beforeEach(() => {
    state.inserted.length = 0;
    state.reviews.length = 0;
    state.storagePut.mockReset().mockResolvedValue({ key: "field-observations/7/observation.jpg", url: "/manus-storage/field-observations/7/observation.jpg" });
  });

  it("persists a protected observation without fabricating a photo reference", async () => {
    const result = await submitObservation(7, { observedAt: new Date("2026-08-16T18:00:00Z"), latitude: 16.7247, longitude: 95.6687, impactClass: "flooded", notes: "Observed road flooding.", photo: null });
    expect(result).toEqual({ id: 77, reviewStatus: "submitted", photoStored: false });
    expect(state.storagePut).not.toHaveBeenCalled();
    expect(state.inserted[0]).toMatchObject({ reporterUserId: 7, latitude: "16.724700", longitude: "95.668700", photoKey: null, notes: "Observed road flooding." });
  });

  it("stores an uploaded photo reference and preserves submitted review state", async () => {
    const photo = { contentType: "image/jpeg" as const, filename: "water.jpg", dataUrl: "data:image/jpeg;base64,aGVsbG8=" };
    const result = await submitObservation(7, { observedAt: new Date("2026-08-16T18:00:00Z"), latitude: 16.7247, longitude: 95.6687, impactClass: "water_on_road", photo });
    expect(result).toEqual({ id: 77, reviewStatus: "submitted", photoStored: true });
    expect(state.storagePut).toHaveBeenCalledWith("field-observations/7/observation.jpg", expect.any(Buffer), "image/jpeg");
    expect(state.inserted[0]).toMatchObject({ photoKey: "field-observations/7/observation.jpg", photoContentType: "image/jpeg" });
  });

  it("persists an administrator review rationale and immutable review provenance", async () => {
    await expect(reviewObservation(77, 1, "verified", "Photo and coordinates reviewed.")).resolves.toEqual({ id: 77, reviewStatus: "verified" });
    expect(state.reviews[0]).toMatchObject({ reviewStatus: "verified", reviewNotes: "Photo and coordinates reviewed.", reviewerUserId: 1, reviewedAt: expect.any(Date) });
  });
});
