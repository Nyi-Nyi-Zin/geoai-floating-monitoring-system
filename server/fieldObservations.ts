import { desc, eq, sql } from "drizzle-orm";
import { fieldObservations } from "../drizzle/schema";
import { getDb } from "./db";
import { storageGet, storagePut } from "./storage";

export const impactClasses = ["flooded", "water_on_road", "access_disrupted", "no_flood_observed"] as const;
export const reviewStatuses = ["submitted", "verified", "rejected"] as const;
export type ImpactClass = (typeof impactClasses)[number];
export type ReviewStatus = (typeof reviewStatuses)[number];

export type ObservationInput = {
  observedAt: Date;
  latitude: number;
  longitude: number;
  locationAccuracyM?: number | null;
  impactClass: ImpactClass;
  waterDepthCm?: number | null;
  notes?: string | null;
  photo?: { dataUrl: string; contentType: "image/jpeg" | "image/png" | "image/webp"; filename: string } | null;
};

const MAX_PHOTO_BYTES = 900_000;

function decodePhoto(photo: NonNullable<ObservationInput["photo"]>) {
  const match = photo.dataUrl.match(/^data:(image\/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)$/);
  if (!match || match[1] !== photo.contentType) throw new Error("Invalid observation photo format");
  const bytes = Buffer.from(match[2], "base64");
  if (!bytes.length || bytes.length > MAX_PHOTO_BYTES) throw new Error("Observation photo must be at most 900 KB");
  const extension = photo.contentType === "image/jpeg" ? "jpg" : photo.contentType.split("/")[1];
  return { bytes, extension };
}

export async function submitObservation(reporterUserId: number, input: ObservationInput) {
  const db = await getDb();
  if (!db) throw new Error("Database unavailable for field observation submission");
  let photoKey: string | null = null;
  let photoContentType: string | null = null;
  if (input.photo) {
    const photo = decodePhoto(input.photo);
    const stored = await storagePut(`field-observations/${reporterUserId}/observation.${photo.extension}`, photo.bytes, input.photo.contentType);
    photoKey = stored.key;
    photoContentType = input.photo.contentType;
  }
  const [created] = await db.insert(fieldObservations).values({
    reporterUserId,
    observedAt: input.observedAt,
    latitude: input.latitude.toFixed(6),
    longitude: input.longitude.toFixed(6),
    locationAccuracyM: input.locationAccuracyM == null ? null : input.locationAccuracyM.toFixed(1),
    impactClass: input.impactClass,
    waterDepthCm: input.waterDepthCm == null ? null : input.waterDepthCm.toFixed(1),
    notes: input.notes?.trim() || null,
    photoKey,
    photoContentType,
  }).$returningId();
  return { id: created.id, reviewStatus: "submitted" as const, photoStored: Boolean(photoKey) };
}

export async function listMyObservations(reporterUserId: number) {
  const db = await getDb();
  if (!db) return [];
  const rows = await db.select().from(fieldObservations).where(eq(fieldObservations.reporterUserId, reporterUserId)).orderBy(desc(fieldObservations.observedAt)).limit(50);
  return rows.map(row => ({
    id: row.id, observedAt: row.observedAt, latitude: Number(row.latitude), longitude: Number(row.longitude), impactClass: row.impactClass,
    waterDepthCm: row.waterDepthCm == null ? null : Number(row.waterDepthCm), reviewStatus: row.reviewStatus, reviewNotes: row.reviewNotes, createdAt: row.createdAt,
  }));
}

export async function listReviewQueue() {
  const db = await getDb();
  if (!db) return [];
  const rows = await db.select().from(fieldObservations).where(eq(fieldObservations.reviewStatus, "submitted")).orderBy(desc(fieldObservations.observedAt)).limit(100);
  return Promise.all(rows.map(async row => ({
    id: row.id, reporterUserId: row.reporterUserId, observedAt: row.observedAt, latitude: Number(row.latitude), longitude: Number(row.longitude), locationAccuracyM: row.locationAccuracyM == null ? null : Number(row.locationAccuracyM),
    impactClass: row.impactClass, waterDepthCm: row.waterDepthCm == null ? null : Number(row.waterDepthCm), notes: row.notes, photoUrl: row.photoKey ? (await storageGet(row.photoKey)).url : null, createdAt: row.createdAt,
  })));
}

export async function reviewObservation(id: number, reviewerUserId: number, reviewStatus: Exclude<ReviewStatus, "submitted">, reviewNotes: string) {
  const db = await getDb();
  if (!db) throw new Error("Database unavailable for observation review");
  await db.update(fieldObservations).set({ reviewStatus, reviewNotes: reviewNotes.trim(), reviewerUserId, reviewedAt: new Date() }).where(eq(fieldObservations.id, id));
  return { id, reviewStatus };
}

export async function getObservationSummary() {
  const db = await getDb();
  const empty = { submitted: 0, verified: 0, rejected: 0, label: "Field evidence" as const, readiness: "no_verified_local_evidence" as const };
  if (!db) return empty;
  const rows = await db.select({ reviewStatus: fieldObservations.reviewStatus, count: sql<number>`count(*)` }).from(fieldObservations).groupBy(fieldObservations.reviewStatus);
  const counts = new Map(rows.map(row => [row.reviewStatus, Number(row.count)]));
  return { submitted: counts.get("submitted") ?? 0, verified: counts.get("verified") ?? 0, rejected: counts.get("rejected") ?? 0, label: "Field evidence" as const, readiness: (counts.get("verified") ? "verified_evidence_available" : "no_verified_local_evidence") as "verified_evidence_available" | "no_verified_local_evidence" };
}
