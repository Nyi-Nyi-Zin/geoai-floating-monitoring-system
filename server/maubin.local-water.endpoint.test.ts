import { describe, expect, it } from "vitest";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

describe("Maubin local-water evidence endpoint", () => {
  it("returns only the monitoring-only historical and no-live-source contract", async () => {
    const { stdout } = await execFileAsync("python3", ["scripts/check_maubin_local_water_evidence_endpoint.py"], { cwd: process.cwd() });
    expect(stdout).toContain("maubin-local-water-evidence-endpoint-contract: ok");
  });
});
