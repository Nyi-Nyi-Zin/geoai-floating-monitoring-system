import { describe, expect, it } from "vitest";
import { buildProjectionFromStoredInputs, monitoringStatus, projectV7FeaturesForCells } from "./monitoring";

describe("prospective monitoring safety contract", () => {
  it("labels future-time input logging as monitoring only, never a live flood alert", () => {
    expect(monitoringStatus.prospectiveReadiness).toEqual({
      mode: "inputs_only",
      label: "Prospective monitoring",
      delivery: "dashboard_only",
      reason: "Forecast inputs are logged every six hours for validation; no live flood probability or public alert is produced.",
    });
    expect(monitoringStatus.alertReadiness.mode).toBe("disabled");
    expect(monitoringStatus.openAlerts).toBe(0);
  });

  it("creates model-ready per-cell v7 feature projections without a probability output", () => {
    const projections = projectV7FeaturesForCells([{
      cell_id: "cell-1", elevation_mean_m: 0.5, elevation_percentile: 0, local_relief_m: 0,
      distance_to_waterway_m: 48.3, land_cover_dominant_code: 80, osm_drainage_distance_m: 1752, osm_levee_distance_m: 41725.5,
    }], {
      rainfall_lag_1d_mm: 12, rainfall_lag_3d_mm: 30, rainfall_lag_7d_mm: 56, rainfall_lag_14d_mm: 88, rainfall_lag_30d_mm: 120,
      discharge_lag_1d_m3s: 100, discharge_lag_3d_m3s: 300, discharge_lag_7d_m3s: 700, discharge_lag_14d_m3s: 1400, discharge_lag_30d_m3s: 3000,
    });
    expect(projections).toHaveLength(1);
    expect(projections[0]).toMatchObject({ cell_id: "cell-1", elevation_mean_m: 0.5, rainfall_lag_7d_mm: 56, discharge_lag_30d_m3s: 3000 });
    expect(projections[0]).not.toHaveProperty("probability");
    expect(projections[0]).not.toHaveProperty("predicted_label");
  });

  it("durably reconstructs every cell feature vector from stored snapshot inputs and the versioned static seed", () => {
    const result = buildProjectionFromStoredInputs({
      sourceKey: "open-meteo-glofas-maubin-six-hour", issueKey: "20260816Z", issueTime: new Date("2026-08-16T18:00:00Z"), targetDate: "2026-08-18", horizonDays: 2,
      rainfallLag1dMm: "12.00", rainfallLag3dMm: "30.00", rainfallLag7dMm: "56.00", rainfallLag14dMm: "88.00", rainfallLag30dMm: "120.00",
      dischargeLag1dM3s: "100.00", dischargeLag3dM3s: "300.00", dischargeLag7dM3s: "700.00", dischargeLag14dM3s: "1400.00", dischargeLag30dM3s: "3000.00",
      projectionStatus: "per_cell_v7_features_no_probability", modelVersion: "maubin-flood-event-hgb-v7", qualityFlags: ["monitoring_only_no_flood_probability"],
    }, {
      schema: "maubin-v7-static-cell-features-v1", model_version: "maubin-flood-event-hgb-v7", cell_count: 2,
      cells: [
        { cell_id: "cell-1", elevation_mean_m: 0.5, elevation_percentile: 0, local_relief_m: 0, distance_to_waterway_m: 48.3, land_cover_dominant_code: 80, osm_drainage_distance_m: 1752, osm_levee_distance_m: 41725.5 },
        { cell_id: "cell-2", elevation_mean_m: 0.8, elevation_percentile: 0.2, local_relief_m: 0.1, distance_to_waterway_m: 60, land_cover_dominant_code: 40, osm_drainage_distance_m: 800, osm_levee_distance_m: 1200 },
      ],
    });
    expect(result).toMatchObject({ issueKey: "20260816Z", targetDate: "2026-08-18", staticFeatureCellCount: 2, projectionStatus: "per_cell_v7_features_no_probability" });
    expect(result.cells).toHaveLength(2);
    expect(result.cells[1]).toMatchObject({ cell_id: "cell-2", rainfall_lag_7d_mm: 56, discharge_lag_30d_m3s: 3000, osm_levee_distance_m: 1200 });
    expect(result.cells[0]).not.toHaveProperty("probability");
    expect(result.cells[0]).not.toHaveProperty("predicted_label");
  });
});
