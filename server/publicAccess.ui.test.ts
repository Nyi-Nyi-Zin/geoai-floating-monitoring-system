import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";

describe("public evidence access", () => {
  it("keeps field observation submission available without a sign-in gate while preserving review and no-alert disclosures", async () => {
    const source = await readFile(new URL("../client/src/components/FieldObservationModal.tsx", import.meta.url), "utf8");
    expect(source).toContain("No sign-in is required.");
    expect(source).toContain("private anonymous contributor identifier");
    expect(source).toContain("requires analyst review");
    expect(source).toContain("never creates a public flood alert");
    expect(source).not.toContain("startLogin");
    expect(source).not.toContain("useAuth");
  });
});
