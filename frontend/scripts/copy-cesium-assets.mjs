import { cp, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const cesiumBuild = join(
  frontendRoot,
  "node_modules",
  "cesium",
  "Build",
  "Cesium",
);
const publicRoot = join(frontendRoot, "public", "cesium");
const runtimeDirectories = ["Workers", "ThirdParty", "Assets", "Widgets"];

await mkdir(publicRoot, { recursive: true });
await Promise.all(
  runtimeDirectories.map((directory) =>
    cp(join(cesiumBuild, directory), join(publicRoot, directory), {
      recursive: true,
      force: true,
    }),
  ),
);
await cp(join(cesiumBuild, "Cesium.js"), join(publicRoot, "Cesium.js"), {
  force: true,
});

console.log("Cesium runtime assets copied to public/cesium.");
