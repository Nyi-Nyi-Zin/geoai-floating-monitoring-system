import { mkdir, readFile, writeFile } from "node:fs/promises";
import simplify from "@turf/simplify";

const sourceDir = "/home/ubuntu/nationwide-data/mmr_admin_boundaries";
const outputDir = "/home/ubuntu/webdev-static-assets";
const outputPath = `${outputDir}/myanmar_admin_seed_v1.json`;
const displayOutputPath = `${outputDir}/myanmar_admin1_display_v1.json`;
const partitionOutputPath = `${outputDir}/myanmar_admin1_partitions_v1.json`;

const [admin0Raw, admin1Raw] = await Promise.all([
  readFile(`${sourceDir}/mmr_admin0.geojson`, "utf8"),
  readFile(`${sourceDir}/mmr_admin1.geojson`, "utf8"),
]);

const admin0 = JSON.parse(admin0Raw);
const admin1 = JSON.parse(admin1Raw);

function collectCoordinates(value, coordinates = []) {
  if (!Array.isArray(value)) return coordinates;
  if (typeof value[0] === "number" && typeof value[1] === "number") {
    coordinates.push(value);
    return coordinates;
  }
  for (const child of value) collectCoordinates(child, coordinates);
  return coordinates;
}

function boundsForGeometry(geometry) {
  const coordinates = collectCoordinates(geometry?.coordinates);
  if (!coordinates.length) throw new Error("Admin 1 geometry contains no coordinates");
  const longitudes = coordinates.map(([longitude]) => longitude);
  const latitudes = coordinates.map(([, latitude]) => latitude);
  return {
    west: Math.min(...longitudes),
    south: Math.min(...latitudes),
    east: Math.max(...longitudes),
    north: Math.max(...latitudes),
  };
}

if (admin0.type !== "FeatureCollection" || admin0.features.length !== 1) throw new Error("Expected exactly one Myanmar Admin 0 feature");
if (admin1.type !== "FeatureCollection" || admin1.features.length !== 18) throw new Error("Expected 18 Myanmar Admin 1 features");

const validOn = admin1.features.map(feature => feature.properties?.valid_on).filter(Boolean).sort().at(-1) ?? null;
const seed = {
  schema: "deltawatch-myanmar-admin-boundaries-v1",
  generated_at: "2026-08-17T00:00:00Z",
  source: {
    provider: "OCHA Field Information Services Section / MIMU",
    dataset: "Myanmar Subnational Administrative Boundaries (COD-AB) v01",
    landing_page: "https://data.humdata.org/dataset/cod-ab-mmr",
    resource: "mmr_admin_boundaries.geojson.zip",
    resource_modified: "2026-08-14",
    boundary_valid_on: validOn,
  },
  coverage: {
    admin0_feature_count: admin0.features.length,
    admin1_feature_count: admin1.features.length,
    partition: "Admin 1 only; regional monitoring index, not a flood-risk prediction layer",
    status: "source_geometry_ready_prediction_not_assessed",
  },
  admin0,
  admin1,
};

await mkdir(outputDir, { recursive: true });
await writeFile(outputPath, `${JSON.stringify(seed)}\n`, "utf8");
const admin1Display = simplify(admin1, { tolerance: 0.003, highQuality: false, mutate: false });
const displaySeed = {
  schema: "deltawatch-myanmar-admin1-display-v1",
  generated_at: seed.generated_at,
  source: { ...seed.source, geometry_role: "simplified_country_view_display", simplification_tolerance_degrees: 0.003 },
  coverage: seed.coverage,
  admin1: admin1Display,
};
await writeFile(displayOutputPath, `${JSON.stringify(displaySeed)}\n`, "utf8");
const partitionSeed = {
  schema: "deltawatch-myanmar-admin1-partitions-v1",
  generated_at: seed.generated_at,
  source: { ...seed.source, partition_role: "bounded_regional_processing_manifest" },
  status: "source_partitions_ready_no_nationwide_features_labels_scores_or_predictions",
  partitions: admin1.features.map((feature) => ({
    admin1_pcode: feature.properties.adm1_pcode,
    admin1_name: feature.properties.adm1_name,
    admin1_name_mm: feature.properties.adm1_name1,
    source_center: { longitude: feature.properties.center_lon, latitude: feature.properties.center_lat },
    bounds: boundsForGeometry(feature.geometry),
    area_sqkm: feature.properties.area_sqkm,
    valid_on: feature.properties.valid_on,
  })),
};
await writeFile(partitionOutputPath, `${JSON.stringify(partitionSeed)}\n`, "utf8");
const [sourceBytes, displayBytes, partitionBytes] = await Promise.all([readFile(outputPath), readFile(displayOutputPath), readFile(partitionOutputPath)]);
console.log(JSON.stringify({ outputPath, displayOutputPath, partitionOutputPath, admin0Features: admin0.features.length, admin1Features: admin1.features.length, validOn, sourceBytes: sourceBytes.length, displayBytes: displayBytes.length, partitionBytes: partitionBytes.length }, null, 2));
