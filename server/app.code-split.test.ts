import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";

describe("dashboard code splitting", () => {
  it("loads the map dashboard lazily while retaining an accessible loading fallback", async () => {
    const source = await readFile(new URL("../client/src/App.tsx", import.meta.url), "utf8");
    expect(source).toContain('const Home = lazy(() => import("./pages/Home"));');
    expect(source).toContain("<Suspense fallback=");
    expect(source).toContain('aria-live="polite"');
  });
});
