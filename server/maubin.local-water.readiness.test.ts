import { describe, expect, it } from "vitest";
import { readFile } from "node:fs/promises";

describe("Maubin local-water readiness disclosure", () => {
  it("shows audited historical context and unavailable live/tide evidence without authorizing prediction", async () => {
    const [home, spatial, seedScript] = await Promise.all([
      readFile(new URL("../client/src/pages/Home.tsx", import.meta.url), "utf8"),
      readFile(new URL("../spatial_api/main.py", import.meta.url), "utf8"),
      readFile(new URL("../scripts/prepare_maubin_local_water_evidence_readiness.py", import.meta.url), "utf8"),
    ]);
    expect(home).toContain('fetch("/api/spatial/maubin/local-water-evidence-readiness")');
    expect(home).toContain("Local water evidence");
    expect(home).toContain("Historical context only");
    expect(home).toContain("not a Maubin live gauge");
    expect(home).toContain("Local river-stage and tide evidence remain unavailable for a live model.");
    expect(spatial).toContain('@app.get("/maubin/local-water-evidence-readiness")');
    expect(spatial).toContain('"river_stage": seed.get("river_stage")');
    expect(spatial).toContain('"tide_and_coastal_water": seed.get("tide_and_coastal_water")');
    expect(seedScript).toContain('"live_feed_available": False');
    expect(seedScript).toContain('"prediction_authorized": False');
    expect(seedScript).toContain('"alert_authorized": False');
    expect(seedScript).toContain("no stage threshold, model score, probability, prediction, forecast, alert");
  });
});
