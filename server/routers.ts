import { COOKIE_NAME } from "@shared/const";
import { z } from "zod";
import { getAnonymousContributorId } from "./anonymousContributor";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { adminProcedure, publicProcedure, router } from "./_core/trpc";
import { getObservationSummary, impactClasses, listMyObservations, listReviewQueue, reviewObservation, reviewStatuses, submitObservation } from "./fieldObservations";
import { getLatestProspectiveMonitoring, getOperationalMonitoringStatus, getProspectiveFeatureProjection, getWeatherSnapshot, listStoredRainfall, monitoringStatus } from "./monitoring";

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
    operationalStatus: publicProcedure.query(() => getOperationalMonitoringStatus()),
    prospectiveFeatures: publicProcedure.input(z.object({ issueKey: z.string().min(1), targetDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/) })).query(({ input }) => getProspectiveFeatureProjection(input.issueKey, input.targetDate)),
  }),
  observations: router({
    summary: publicProcedure.query(() => getObservationSummary()),
    mine: publicProcedure.query(async ({ ctx }) => listMyObservations(await getAnonymousContributorId(ctx))),
    submit: publicProcedure.input(z.object({
      observedAt: z.coerce.date(),
      latitude: z.number().min(16.0).max(17.5),
      longitude: z.number().min(95.0).max(96.5),
      locationAccuracyM: z.number().positive().max(10_000).nullable().optional(),
      impactClass: z.enum(impactClasses),
      waterDepthCm: z.number().min(0).max(2_000).nullable().optional(),
      notes: z.string().max(1_200).nullable().optional(),
      photo: z.object({ dataUrl: z.string().max(1_300_000), contentType: z.enum(["image/jpeg", "image/png", "image/webp"]), filename: z.string().max(160) }).nullable().optional(),
    })).mutation(async ({ ctx, input }) => submitObservation(await getAnonymousContributorId(ctx), input)),
    reviewQueue: adminProcedure.query(() => listReviewQueue()),
    review: adminProcedure.input(z.object({ id: z.number().int().positive(), reviewStatus: z.enum(reviewStatuses).exclude(["submitted"]), reviewNotes: z.string().min(3).max(1_200) })).mutation(({ ctx, input }) => reviewObservation(input.id, ctx.user.id, input.reviewStatus, input.reviewNotes)),
  }),
});

export type AppRouter = typeof appRouter;
