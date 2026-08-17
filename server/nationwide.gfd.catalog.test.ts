import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";

describe("nationwide GFD catalog builder", () => {
  it("selects Myanmar source metadata while excluding raster labels, scores, probabilities, and alerts", async () => {
    const source = await readFile(new URL("../scripts/build_myanmar_gfd_catalog.py", import.meta.url), "utf8");
    expect(source).toContain('COUNTRY_NAMES = {"myanmar", "burma"}');
    expect(source).toContain('glide.endswith("-MMR")');
    expect(source).toContain('"No flood-raster archive, cell label, feature table, model score, probability, or alert is produced by this step."');
  });
});
