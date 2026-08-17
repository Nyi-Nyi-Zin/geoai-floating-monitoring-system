import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";

describe("nationwide Admin 1 partition service", () => {
  it("serves the dedicated source partition manifest without model-output fields", async () => {
    const source = await readFile(new URL("../spatial_api/main.py", import.meta.url), "utf8");
    expect(source).toContain('MYANMAR_ADMIN_PARTITIONS_PATH = "/manus-storage/myanmar_admin1_partitions_v1_a330f15d.json"');
    expect(source).toContain('@app.get("/national-admin/partitions")');
    expect(source).toContain('"partitions": seed.get("partitions", [])');
    expect(source).not.toContain('national_admin_partitions() -> dict:\n    return {"probability"');
  });
});
