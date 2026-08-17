import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";

describe("nationwide validation protocol", () => {
  it("requires chronological isolation and prohibits nationwide prediction claims before regional validation", async () => {
    const protocol = await readFile(new URL("../model_pipeline/myanmar_nationwide_validation_protocol.md", import.meta.url), "utf8");
    expect(protocol).toContain("Frozen chronological holdout");
    expect(protocol).toContain("No observation from the frozen 2018 holdout may influence");
    expect(protocol).toContain("The workflow must not publish a nationwide flood-risk score, probability, forecast, alert, or life-safety decision");
    expect(protocol).toContain("Maubin v7 metrics cannot be transferred as Myanmar-wide accuracy claims.");
  });
});
