import { createHash, randomBytes } from "node:crypto";
import type { TrpcContext } from "./_core/context";
import { getSessionCookieOptions } from "./_core/cookies";
import { getUserByOpenId, upsertUser } from "./db";

export const ANONYMOUS_CONTRIBUTOR_COOKIE = "deltawatch_contributor";

const TOKEN_PATTERN = /^[A-Za-z0-9_-]{32,128}$/;
const ONE_YEAR_MS = 365 * 24 * 60 * 60 * 1_000;

function readCookie(ctx: TrpcContext, name: string): string | null {
  const cookieHeader = ctx.req.headers.cookie;
  const raw = Array.isArray(cookieHeader) ? cookieHeader.join(";") : cookieHeader;
  if (!raw) return null;

  const encoded = raw
    .split(";")
    .map(part => part.trim())
    .find(part => part.startsWith(`${name}=`))
    ?.slice(name.length + 1);
  if (!encoded) return null;

  try {
    const token = decodeURIComponent(encoded);
    return TOKEN_PATTERN.test(token) ? token : null;
  } catch {
    return null;
  }
}

function anonymousOpenId(token: string) {
  return `anon.${createHash("sha256").update(token).digest("base64url")}`;
}

/** Uses a random opaque browser cookie and a hash-derived database identifier. */
export async function getAnonymousContributorId(ctx: TrpcContext): Promise<number> {
  let token = readCookie(ctx, ANONYMOUS_CONTRIBUTOR_COOKIE);
  if (!token) {
    token = randomBytes(32).toString("base64url");
    ctx.res.cookie(ANONYMOUS_CONTRIBUTOR_COOKIE, token, {
      ...getSessionCookieOptions(ctx.req),
      maxAge: ONE_YEAR_MS,
    });
  }

  const openId = anonymousOpenId(token);
  let contributor = await getUserByOpenId(openId);
  if (!contributor) {
    await upsertUser({ openId, loginMethod: "anonymous-device", role: "user" });
    contributor = await getUserByOpenId(openId);
  }
  if (!contributor) throw new Error("Anonymous contributor identity could not be initialized");
  return contributor.id;
}
