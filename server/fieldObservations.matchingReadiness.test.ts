import { describe, expect, it } from "vitest";
import { classifyProspectiveEvidenceMatchingReadiness } from "./fieldObservations";

describe("prospective evidence-matching readiness", () => {
  const now = new Date("2026-08-17T00:00:00.000Z");

  it("keeps empty, unavailable, stale, and unmatched evidence states outside metrics", () => {
    const noEvidence = classifyProspectiveEvidenceMatchingReadiness({ verifiedObservationCount: 0, prospectiveSnapshotCount: 30, matchedPairCount: 0, now });
    const noSnapshots = classifyProspectiveEvidenceMatchingReadiness({ verifiedObservationCount: 1, prospectiveSnapshotCount: 0, matchedPairCount: 0, latestVerifiedObservationAt: now, now });
    const stale = classifyProspectiveEvidenceMatchingReadiness({ verifiedObservationCount: 1, prospectiveSnapshotCount: 30, matchedPairCount: 0, latestVerifiedObservationAt: new Date("2026-01-01T00:00:00.000Z"), now });
    const unmatched = classifyProspectiveEvidenceMatchingReadiness({ verifiedObservationCount: 1, prospectiveSnapshotCount: 30, matchedPairCount: 0, latestVerifiedObservationAt: now, now });
    expect([noEvidence.status, noSnapshots.status, stale.status, unmatched.status]).toEqual([
      "no_verified_observations", "verified_observations_no_snapshots", "verified_observations_stale", "verified_observations_unmatched",
    ]);
    for (const readiness of [noEvidence, noSnapshots, stale, unmatched]) {
      expect(readiness.metricsAuthorized).toBe(false);
      expect(readiness.modelPromotionAuthorized).toBe(false);
    }
  });

  it("keeps insufficient and analyst-review-pending pairs outside metrics and promotion", () => {
    const insufficient = classifyProspectiveEvidenceMatchingReadiness({ verifiedObservationCount: 4, prospectiveSnapshotCount: 30, matchedPairCount: 9, latestVerifiedObservationAt: now, now });
    const reviewPending = classifyProspectiveEvidenceMatchingReadiness({ verifiedObservationCount: 12, prospectiveSnapshotCount: 30, matchedPairCount: 10, latestVerifiedObservationAt: now, now });
    expect(insufficient.status).toBe("matched_evidence_insufficient_for_metrics");
    expect(reviewPending.status).toBe("eligible_pairs_pending_analyst_review");
    expect(insufficient.minimumMatchedPairsForMetrics).toBe(10);
    expect(reviewPending.metricsAuthorized).toBe(false);
    expect(reviewPending.modelPromotionAuthorized).toBe(false);
  });
});
