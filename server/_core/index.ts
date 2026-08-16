import "dotenv/config";
import { spawn } from "child_process";
import express from "express";
import { createServer } from "http";
import net from "net";
import { createExpressMiddleware } from "@trpc/server/adapters/express";
import { registerOAuthRoutes } from "./oauth";
import { registerStorageProxy } from "./storageProxy";
import { appRouter } from "../routers";
import { createContext } from "./context";
import { serveStatic, setupVite } from "./vite";
import { getScheduleConfig, recordScheduleResult, refreshCurrentMonthRainfall } from "../monitoring";
import { sdk } from "./sdk";

async function portAvailable(port: number) { return await new Promise<boolean>(resolve => { const server = net.createServer(); server.listen(port, () => server.close(() => resolve(true))); server.on("error", () => resolve(false)); }); }
async function findAvailablePort(start = 3000) { for (let port = start; port < start + 20; port++) if (await portAvailable(port)) return port; throw new Error("No available HTTP port"); }

function launchSpatialApi(appPort: number) {
  const processHandle = spawn("python3", ["-m", "uvicorn", "spatial_api.main:app", "--host", "127.0.0.1", "--port", "8010"], {
    env: { ...process.env, SPATIAL_SEED_BASE_URL: `http://127.0.0.1:${appPort}` },
    stdio: "ignore",
  });
  const shutdown = () => processHandle.kill("SIGTERM");
  process.once("SIGTERM", shutdown); process.once("SIGINT", shutdown);
}

async function startServer() {
  const app = express(); const server = createServer(app);
  app.use(express.json({ limit: "2mb" })); app.use(express.urlencoded({ limit: "2mb", extended: true }));
  registerStorageProxy(app); registerOAuthRoutes(app);
  app.use("/api/trpc", createExpressMiddleware({ router: appRouter, createContext }));
  app.post("/api/scheduled/rainfall-refresh", async (req, res) => {
    try {
      const user = await sdk.authenticateRequest(req);
      if (!user.isCron || !user.taskUid) return res.status(403).json({ error: "cron-only" });
      const config = await getScheduleConfig("nightly-rainfall-refresh");
      if (!config || config.scheduleCronTaskUid !== user.taskUid) return res.json({ ok: true, skipped: "orphan" });
      const result = await refreshCurrentMonthRainfall(); await recordScheduleResult("nightly-rainfall-refresh", user.taskUid, result);
      return res.json({ ok: true, result });
    } catch (error) { return res.status(500).json({ error: error instanceof Error ? error.message : String(error), timestamp: new Date().toISOString() }); }
  });
  app.all("/api/spatial/*", async (req, res) => {
    try { const upstream = await fetch(`http://127.0.0.1:8010${req.originalUrl.replace("/api/spatial", "")}`); const body = await upstream.arrayBuffer(); res.status(upstream.status); res.setHeader("content-type", upstream.headers.get("content-type") ?? "application/json"); res.send(Buffer.from(body)); }
    catch { res.status(503).json({ ok: false, error: "Spatial API is starting" }); }
  });
  if (process.env.NODE_ENV === "development") await setupVite(app, server); else serveStatic(app);
  const requestedPort = Number(process.env.PORT || 3000); const port = await findAvailablePort(requestedPort);
  launchSpatialApi(port);
  server.listen(port, () => console.log(`Server running on http://localhost:${port}/`));
}

startServer().catch(console.error);
