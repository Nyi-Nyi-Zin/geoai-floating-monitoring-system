import { and, desc, eq, gte, sql } from "drizzle-orm";
import { randomUUID } from "node:crypto";
import { fieldObservations } from "../drizzle/schema";
import { getDb } from "./db";
import { storageGet, storagePut } from "./storage";

export const impactClasses = ["flooded", "water_on_road", "access_disrupted", "no_flood_observed"] as const;
export const reviewStatuses = ["submitted", "verified", "rejected"] as const;
export type ImpactClass = (typeof impactClasses)[number];
export type ReviewStatus = (typeof reviewStatuses)[number];

export type ProspectiveEvidenceMatchingInput = {
  verifiedObservationCount: number;
  prospectiveSnapshotCount: number;
  matchedPairCount: number;
  latestVerifiedObservationAt?: Date | null;
  now?: Date;
};

export type ProspectiveEvidenceMatchingReadiness = {
  status: "no_verified_observations" | "verified_observations_no_snapshots" | "verified_observations_stale" | "verified_observations_unmatched" | "matched_evidence_insufficient_for_metrics" | "eligible_pairs_pending_analyst_review";
  verifiedObservationCount: number;
  prospectiveSnapshotCount: number;
  matchedPairCount: number;
  minimumMatchedPairsForMetrics: number;
  metricsAuthorized: false;
  modelPromotionAuthorized: false;
  reason: string;
};

const STALE_EVIDENCE_MS = 90 * 24 * 60 * 60 * 1_000;
const MINIMUM_MATCHED_PAIRS_FOR_METRICS = 10;

export function classifyProspectiveEvidenceMatchingReadiness(input: ProspectiveEvidenceMatchingInput): ProspectiveEvidenceMatchingReadiness {
  const now = input.now ?? new Date();
  const verifiedObservationCount = Math.max(0, input.verifiedObservationCount);
  const prospectiveSnapshotCount = Math.max(0, input.prospectiveSnapshotCount);
  const matchedPairCount = Math.max(0, input.matchedPairCount);
  const base = { verifiedObservationCount, prospectiveSnapshotCount, matchedPairCount, minimumMatchedPairsForMetrics: MINIMUM_MATCHED_PAIRS_FOR_METRICS, metricsAuthorized: false as const, modelPromotionAuthorized: false as const };
  if (!verifiedObservationCount) return { ...base, status: "no_verified_observations", reason: "No verified field observations are available; no prospective matching or metric may be calculated." };
  if (!prospectiveSnapshotCount) return { ...base, status: "verified_observations_no_snapshots", reason: "Verified observations exist, but no immutable prospective snapshots are available for issue-time matching." };
  if (input.latestVerifiedObservationAt && now.getTime() - input.latestVerifiedObservationAt.getTime() > STALE_EVIDENCE_MS) return { ...base, status: "verified_observations_stale", reason: "The newest verified observation is older than the 90-day readiness window; analyst review is required before matching." };
  if (!matchedPairCount) return { ...base, status: "verified_observations_unmatched", reason: "Verified observations and prospective snapshots exist, but no eligible time-and-location pairs have been reviewed." };
  if (matchedPairCount < MINIMUM_MATCHED_PAIRS_FOR_METRICS) return { ...base, status: "matched_evidence_insufficient_for_metrics", reason: "Eligible reviewed pairs exist, but the pre-registered minimum of 10 pairs for exploratory metrics is not met." };
  return { ...base, status: "eligible_pairs_pending_analyst_review", reason: "The minimum pair count is reached, but analyst review and the prospective protocol remain required before any metric or promotion decision." };
}

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
const MAX_SUBMISSIONS_PER_HOUR = 3;
const SUBMISSION_WINDOW_MS = 60 * 60 * 1_000;

function validImageSignature(bytes: Buffer, contentType: "image/jpeg" | "image/png" | "image/webp") {
  if (contentType === "image/jpeg") return bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;
  if (contentType === "image/png") return bytes.length >= 8 && bytes.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]));
  return bytes.length >= 12 && bytes.subarray(0, 4).equals(Buffer.from("RIFF")) && bytes.subarray(8, 12).equals(Buffer.from("WEBP"));
}

function decodePhoto(photo: NonNullable<ObservationInput["photo"]>) {
  const match = photo.dataUrl.match(/^data:(image\/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)$/);
  if (!match || match[1] !== photo.contentType) throw new Error("Invalid observation photo format");
  const bytes = Buffer.from(match[2], "base64");
  if (!bytes.length || bytes.length > MAX_PHOTO_BYTES) throw new Error("Observation photo must be at most 900 KB");
  if (!validImageSignature(bytes, photo.contentType)) throw new Error("Observation photo bytes do not match the declared image type");
  const extension = photo.contentType === "image/jpeg" ? "jpg" : photo.contentType.split("/")[1];
  return { bytes, extension };
}

export async function submitObservation(reporterUserId: number, input: ObservationInput) {
  const db = await getDb();
  if (!db) throw new Error("Database unavailable for field observation submission");
  const submittedSince = new Date(Date.now() - SUBMISSION_WINDOW_MS);
  const recentRows = await db.select({ count: sql<number>`count(*)` }).from(fieldObservations).where(and(eq(fieldObservations.reporterUserId, reporterUserId), gte(fieldObservations.createdAt, submittedSince)));
  if (Number(recentRows[0]?.count ?? 0) >= MAX_SUBMISSIONS_PER_HOUR) throw new Error("Observation submission limit reached. Please wait before submitting another report.");
  let photoKey: string | null = null;
  let photoContentType: string | null = null;
  if (input.photo) {
    const photo = decodePhoto(input.photo);
    const stored = await storagePut(`field-observations/${reporterUserId}/${randomUUID()}.${photo.extension}`, photo.bytes, input.photo.contentType);
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
  const rows = await db.select({ reviewStatus: fieldObservations.reviewStatus }).from(fieldObservations).where(eq(fieldObservations.id, id)).limit(1);
  if (!rows[0]) throw new Error("Field observation not found");
  if (rows[0].reviewStatus !== "submitted") throw new Error("Field observation has already been reviewed and cannot be changed");
  await db.update(fieldObservations).set({ reviewStatus, reviewNotes: reviewNotes.trim(), reviewerUserId, reviewedAt: new Date() }).where(eq(fieldObservations.id, id));
  return { id, reviewStatus };
}

export async function getObservationSummary() {
  const db = await getDb();
  const empty = { submitted: 0, verified: 0, rejected: 0, latestVerifiedObservedAt: null as string | null, label: "Field evidence" as const, readiness: "no_verified_local_evidence" as const };
  if (!db) return empty;
  const [rows, latestVerifiedRows] = await Promise.all([
    db.select({ reviewStatus: fieldObservations.reviewStatus, count: sql<number>`count(*)` }).from(fieldObservations).groupBy(fieldObservations.reviewStatus),
    db.select({ observedAt: fieldObservations.observedAt }).from(fieldObservations).where(eq(fieldObservations.reviewStatus, "verified")).orderBy(desc(fieldObservations.observedAt)).limit(1),
  ]);
  const counts = new Map(rows.map(row => [row.reviewStatus, Number(row.count)]));
  return { submitted: counts.get("submitted") ?? 0, verified: counts.get("verified") ?? 0, rejected: counts.get("rejected") ?? 0, latestVerifiedObservedAt: latestVerifiedRows[0]?.observedAt?.toISOString() ?? null, label: "Field evidence" as const, readiness: (counts.get("verified") ? "verified_evidence_available" : "no_verified_local_evidence") as "verified_evidence_available" | "no_verified_local_evidence" };
}
