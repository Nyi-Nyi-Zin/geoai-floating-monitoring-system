import fs from "node:fs";
import { describe, expect, it } from "vitest";

const project = "/home/ubuntu/deltawatch-permanent";

describe("mobile dashboard layout contract", () => {
  it("keeps map layers reachable through a touch control on small screens", () => {
    const home = fs.readFileSync(`${project}/client/src/pages/Home.tsx`, "utf8");
    expect(home).toContain("mobile-layers-button");
    expect(home).toContain("mobileControlsOpen");
    expect(home).toContain("aria-label=\"Open map layers\"");
  });

  it("reserves mobile layouts for panel containment and readable monitoring status", () => {
    const css = fs.readFileSync(`${project}/client/src/index.css`, "utf8");
    expect(css).toContain("@media (max-width: 620px)");
    expect(css).toContain(".controls-panel.mobile-controls-open");
    expect(css).toContain("max-height: calc(100svh - 368px)");
    expect(css).toContain("grid-template-columns: repeat(2, minmax(0, 1fr))");
    expect(css).toContain(".methodology-modal { max-height: calc(100svh - 24px)");
  });
});
