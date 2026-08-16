import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TrpcContext } from "./_core/context";

const mocked = vi.hoisted(() => ({ getDb: vi.fn() }));

vi.mock("./db", () => ({ getDb: mocked.getDb }));

import { appRouter } from "./routers";

describe("public operational status failed-refresh disclosure", () => {
  beforeEach(() => {
    let selectCall = 0;
    mocked.getDb.mockResolvedValue({
      select: vi.fn(() => {
        selectCall += 1;
        if (selectCall === 1) return { from: vi.fn(async () => [{
          key: "six-hour-prospective-monitoring-refresh",
          scheduleCronTaskUid: "internal-scheduler-identifier",
          lastRunAt: new Date("2026-08-16T18:00:00Z"),
          lastResult: { status: "failed", errorCode: "raw-internal-timeout-details" },
        }]) };
        return { from: vi.fn(() => ({ orderBy: vi.fn(() => ({ limit: vi.fn(async () => []) })) })) };
      }),
    });
  });

  it("exposes the failed prospective job state while withholding task identifiers and raw error details", async () => {
    const caller = appRouter.createCaller({ user: null, req: {} as TrpcContext["req"], res: {} as TrpcContext["res"] });
    const health = await caller.monitoring.operationalStatus();
    expect(health.jobs).toContainEqual(expect.objectContaining({
      key: "six-hour-prospective-monitoring-refresh",
      state: "failed",
      lastResultStatus: "failed",
    }));
    const serialized = JSON.stringify(health);
    expect(serialized).not.toContain("internal-scheduler-identifier");
    expect(serialized).not.toContain("raw-internal-timeout-details");
  });
});
