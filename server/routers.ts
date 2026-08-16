import { COOKIE_NAME } from "@shared/const";
import { z } from "zod";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router } from "./_core/trpc";
import { getLatestProspectiveMonitoring, getProspectiveFeatureProjection, getWeatherSnapshot, listStoredRainfall, monitoringStatus } from "./monitoring";

export const appRouter = router({
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => { ctx.res.clearCookie(COOKIE_NAME, { ...getSessionCookieOptions(ctx.req), maxAge: -1 }); return { success: true } as const; }),
  }),
  monitoring: router({
    status: publicProcedure.query(() => monitoringStatus),
    weather: publicProcedure.query(async () => ({ forecast: await getWeatherSnapshot(), storedHistory: await listStoredRainfall() })),
    prospective: publicProcedure.query(() => getLatestProspectiveMonitoring()),
    prospectiveFeatures: publicProcedure.input(z.object({ issueKey: z.string().min(1), targetDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/) })).query(({ input }) => getProspectiveFeatureProjection(input.issueKey, input.targetDate)),
  }),
});

export type AppRouter = typeof appRouter;
