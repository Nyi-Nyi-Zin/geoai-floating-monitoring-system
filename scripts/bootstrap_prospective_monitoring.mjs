import { recordScheduleResult, refreshProspectiveMonitoring } from "../server/monitoring.ts";

const scheduleKey = "six-hour-prospective-monitoring-refresh";
const taskUid = "nD7x3Sg42HkUT7d3XRm8de";

const result = await refreshProspectiveMonitoring();
await recordScheduleResult(scheduleKey, taskUid, result);
console.log(JSON.stringify({ ok: true, scheduleKey, ...result }, null, 2));
