import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TrpcContext } from "./_core/context";

const mocked = vi.hoisted(() => ({ getUserByOpenId: vi.fn(), upsertUser: vi.fn(), cookie: vi.fn() }));

vi.mock("./db", () => ({ getUserByOpenId: mocked.getUserByOpenId, upsertUser: mocked.upsertUser }));
vi.mock("./_core/cookies", () => ({ getSessionCookieOptions: vi.fn(() => ({ httpOnly: true, path: "/", sameSite: "none", secure: true })) }));

import { ANONYMOUS_CONTRIBUTOR_COOKIE, getAnonymousContributorId } from "./anonymousContributor";

function context(cookie?: string): TrpcContext {
  return { user: null, req: { headers: cookie ? { cookie } : {}, protocol: "https" } as TrpcContext["req"], res: { cookie: mocked.cookie } as TrpcContext["res"] };
}

describe("anonymous contributor identity", () => {
  beforeEach(() => vi.clearAllMocks());

  it("creates a non-identifying contributor and issues an opaque secure cookie", async () => {
    mocked.getUserByOpenId.mockResolvedValueOnce(undefined).mockResolvedValueOnce({ id: 73 });
    await expect(getAnonymousContributorId(context())).resolves.toBe(73);
    expect(mocked.upsertUser).toHaveBeenCalledWith(expect.objectContaining({ loginMethod: "anonymous-device", role: "user" }));
    expect(mocked.cookie).toHaveBeenCalledWith(ANONYMOUS_CONTRIBUTOR_COOKIE, expect.stringMatching(/^[A-Za-z0-9_-]{32,128}$/), expect.objectContaining({ httpOnly: true, secure: true, maxAge: expect.any(Number) }));
  });

  it("reuses a valid browser token without issuing another cookie", async () => {
    const token = "A".repeat(43);
    mocked.getUserByOpenId.mockResolvedValueOnce({ id: 74 });
    await expect(getAnonymousContributorId(context(`${ANONYMOUS_CONTRIBUTOR_COOKIE}=${token}`))).resolves.toBe(74);
    expect(mocked.cookie).not.toHaveBeenCalled();
    expect(mocked.upsertUser).not.toHaveBeenCalled();
  });
});
