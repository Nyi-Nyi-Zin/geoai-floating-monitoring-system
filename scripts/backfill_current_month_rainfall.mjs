import { refreshCurrentMonthRainfall } from "../server/monitoring.ts";

const result = await refreshCurrentMonthRainfall();
console.log(JSON.stringify({ operation: "current_month_era5_backfill", ...result }, null, 2));
