import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router } from "./_core/trpc";
import { getWeatherSnapshot, listStoredRainfall, monitoringStatus } from "./monitoring";

export const appRouter = router({
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => { ctx.res.clearCookie(COOKIE_NAME, { ...getSessionCookieOptions(ctx.req), maxAge: -1 }); return { success: true } as const; }),
  }),
  monitoring: router({
    status: publicProcedure.query(() => monitoringStatus),
    weather: publicProcedure.query(async () => ({ forecast: await getWeatherSnapshot(), storedHistory: await listStoredRainfall() })),
  }),
});

export type AppRouter = typeof appRouter;
