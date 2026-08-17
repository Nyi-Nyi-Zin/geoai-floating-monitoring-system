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
  beforeEach(() => { mocked.getUserByOpenId.mockReset(); mocked.upsertUser.mockReset(); mocked.cookie.mockReset(); });

  it("issues an opaque httpOnly browser token and persists only its hash-derived identity", async () => {
    mocked.getUserByOpenId.mockResolvedValueOnce(undefined).mockResolvedValueOnce({ id: 73 });
    await expect(getAnonymousContributorId(context())).resolves.toBe(73);
    expect(mocked.cookie).toHaveBeenCalledWith(ANONYMOUS_CONTRIBUTOR_COOKIE, expect.stringMatching(/^[A-Za-z0-9_-]{32,128}$/), expect.objectContaining({ httpOnly: true, secure: true, sameSite: "none" }));
    expect(mocked.upsertUser).toHaveBeenCalledWith(expect.objectContaining({ openId: expect.stringMatching(/^anon\.[A-Za-z0-9_-]+$/), loginMethod: "anonymous-device", role: "user" }));
  });

  it("reuses a valid browser token without writing a new cookie", async () => {
    mocked.getUserByOpenId.mockResolvedValueOnce({ id: 74 });
    await expect(getAnonymousContributorId(context(`${ANONYMOUS_CONTRIBUTOR_COOKIE}=valid_opaque_token_0123456789012345678901`))).resolves.toBe(74);
    expect(mocked.cookie).not.toHaveBeenCalled();
    expect(mocked.upsertUser).not.toHaveBeenCalled();
  });
});
