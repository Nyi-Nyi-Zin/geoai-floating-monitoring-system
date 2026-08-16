import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({ inserted: [] as Record<string, unknown>[], reviews: [] as Record<string, unknown>[], storagePut: vi.fn(), selectQueue: [] as Array<Record<string, unknown>[]> }));

vi.mock("./db", () => ({
  getDb: vi.fn(async () => ({
    select: vi.fn(() => ({ from: vi.fn(() => ({ where: vi.fn(() => { const rows = state.selectQueue.shift() ?? []; return { limit: vi.fn(async () => rows), then: (resolve: (value: Record<string, unknown>[]) => unknown, reject: (reason: unknown) => unknown) => Promise.resolve(rows).then(resolve, reject) }; }) })) })),
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
    state.selectQueue.length = 0;
    state.selectQueue.push([{ count: 0 }]);
    state.storagePut.mockReset().mockResolvedValue({ key: "field-observations/7/observation.jpg", url: "/manus-storage/field-observations/7/observation.jpg" });
  });

  it("persists a protected observation without fabricating a photo reference", async () => {
    const result = await submitObservation(7, { observedAt: new Date("2026-08-16T18:00:00Z"), latitude: 16.7247, longitude: 95.6687, impactClass: "flooded", notes: "Observed road flooding.", photo: null });
    expect(result).toEqual({ id: 77, reviewStatus: "submitted", photoStored: false });
    expect(state.storagePut).not.toHaveBeenCalled();
    expect(state.inserted[0]).toMatchObject({ reporterUserId: 7, latitude: "16.724700", longitude: "95.668700", photoKey: null, notes: "Observed road flooding." });
  });

  it("stores an uploaded photo reference and preserves submitted review state", async () => {
    const photo = { contentType: "image/jpeg" as const, filename: "water.jpg", dataUrl: "data:image/jpeg;base64,/9j/" };
    const result = await submitObservation(7, { observedAt: new Date("2026-08-16T18:00:00Z"), latitude: 16.7247, longitude: 95.6687, impactClass: "water_on_road", photo });
    expect(result).toEqual({ id: 77, reviewStatus: "submitted", photoStored: true });
    expect(state.storagePut).toHaveBeenCalledWith(expect.stringMatching(/^field-observations\/7\/[a-f0-9-]+\.jpg$/), expect.any(Buffer), "image/jpeg");
    expect(state.inserted[0]).toMatchObject({ photoKey: "field-observations/7/observation.jpg", photoContentType: "image/jpeg" });
  });

  it("rejects image bytes that do not match the declared upload type before storage", async () => {
    const photo = { contentType: "image/jpeg" as const, filename: "invalid.jpg", dataUrl: "data:image/jpeg;base64,aGVsbG8=" };
    await expect(submitObservation(7, { observedAt: new Date("2026-08-16T18:00:00Z"), latitude: 16.7247, longitude: 95.6687, impactClass: "water_on_road", photo })).rejects.toThrow("bytes do not match");
    expect(state.storagePut).not.toHaveBeenCalled();
  });

  it("uses a distinct managed-storage object key for each accepted photo upload", async () => {
    const keys: string[] = [];
    state.storagePut.mockImplementation(async (key: string) => { keys.push(key); return { key, url: `/manus-storage/${key}` }; });
    const photo = { contentType: "image/jpeg" as const, filename: "water.jpg", dataUrl: "data:image/jpeg;base64,/9j/" };
    await submitObservation(7, { observedAt: new Date("2026-08-16T18:00:00Z"), latitude: 16.7247, longitude: 95.6687, impactClass: "water_on_road", photo });
    state.selectQueue.push([{ count: 0 }]);
    await submitObservation(7, { observedAt: new Date("2026-08-16T18:05:00Z"), latitude: 16.7247, longitude: 95.6687, impactClass: "water_on_road", photo });
    expect(keys).toHaveLength(2);
    expect(new Set(keys).size).toBe(2);
  });

  it("throttles repeated submissions before uploading or persisting another evidence record", async () => {
    state.selectQueue.splice(0, 1, [{ count: 3 }]);
    await expect(submitObservation(7, { observedAt: new Date("2026-08-16T18:00:00Z"), latitude: 16.7247, longitude: 95.6687, impactClass: "flooded", photo: null })).rejects.toThrow("submission limit reached");
    expect(state.storagePut).not.toHaveBeenCalled();
    expect(state.inserted).toHaveLength(0);
  });

  it("persists an administrator review rationale and immutable review provenance", async () => {
    state.selectQueue.splice(0, 1, [{ reviewStatus: "submitted" }]);
    await expect(reviewObservation(77, 1, "verified", "Photo and coordinates reviewed.")).resolves.toEqual({ id: 77, reviewStatus: "verified" });
    expect(state.reviews[0]).toMatchObject({ reviewStatus: "verified", reviewNotes: "Photo and coordinates reviewed.", reviewerUserId: 1, reviewedAt: expect.any(Date) });
  });

  it("does not allow an already reviewed observation to be changed again", async () => {
    state.selectQueue.splice(0, 1, [{ reviewStatus: "verified" }]);
    await expect(reviewObservation(77, 1, "rejected", "Second review should not replace the first.")).rejects.toThrow("already been reviewed");
    expect(state.reviews).toHaveLength(0);
  });

  it("returns a controlled error when an analyst attempts to review a missing observation", async () => {
    state.selectQueue.splice(0, 1, []);
    await expect(reviewObservation(404, 1, "verified", "No record exists for this review.")).rejects.toThrow("not found");
    expect(state.reviews).toHaveLength(0);
  });
});
