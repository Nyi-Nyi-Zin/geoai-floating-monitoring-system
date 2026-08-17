import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { describe, expect, it } from "vitest";

const execFileAsync = promisify(execFile);

describe("nationwide evidence-readiness endpoint", () => {
  it("serves the explicit non-predictive historical-source contract", async () => {
    const { stdout } = await execFileAsync("python3", ["scripts/check_national_evidence_endpoint.py"], { cwd: process.cwd() });
    expect(stdout).toContain("national evidence endpoint contract passed");
  });
});
