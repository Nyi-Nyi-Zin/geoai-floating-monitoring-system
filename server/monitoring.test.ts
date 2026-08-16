import { describe, expect, it } from "vitest";
import { buildRainfallRecords } from "./monitoring";

describe("buildRainfallRecords", () => {
  it("creates non-negative daily values and rolling seven-day accumulations", () => {
    const records = buildRainfallRecords(
      { time: ["2026-08-01", "2026-08-02", "2026-08-03"], precipitation_sum: [1.2, null, 4.8] },
      "open-meteo-era5-maubin",
    );
    expect(records).toEqual([
      { sourceKey: "open-meteo-era5-maubin", observedDate: "2026-08-01", precipitationMm: 1.2, accumulation7dMm: 1.2 },
      { sourceKey: "open-meteo-era5-maubin", observedDate: "2026-08-02", precipitationMm: 0, accumulation7dMm: 1.2 },
      { sourceKey: "open-meteo-era5-maubin", observedDate: "2026-08-03", precipitationMm: 4.8, accumulation7dMm: 6 },
    ]);
  });
});
