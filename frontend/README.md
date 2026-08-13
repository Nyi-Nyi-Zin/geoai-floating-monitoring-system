# FloodGuard dashboard (Next.js)

Next.js 16 dashboard for the **FloodGuard Myanmar** GeoAI project in Maubin
Township. It fetches health, waterways, the township boundary, terrain cells,
ML predictions, forecast runs, and flood intelligence from FastAPI on the server.

The client offers a 2D Leaflet view, a regional 3D MapLibre terrain view, and
an optional CesiumJS globe with Satellite / Streets basemap switching. Context
remains visible beneath elevation, susceptibility, land cover, historical flood,
ML probability, event hindcast, forecast, township-boundary, and waterway
overlays. All views support terrain-cell inspection and layer switching.

## Map layers

### Elevation and susceptibility

The susceptibility layer combines relative elevation (55%), mapped-waterway
proximity (30%), and local flatness (15%). Selecting a cell shows the score and
each weighted contribution. This is transparent terrain screening from Copernicus
DEM GLO-30 and OpenStreetMap — not flood depth, probability, or arrival-time
prediction.

### Land cover and waterways

The land-cover layer colors each 500 m cell by its dominant ESA WorldCover 2021
class. Selecting a cell shows class composition from the original 10 m pixels.
This is descriptive historical evidence and is not weighted in the susceptibility
score.

### Historical flood (GFD)

Renders stored MODIS/GFD satellite-observed polygons in 2D, MapLibre 3D, and
Cesium. The Maubin 2000–2018 composite preserves 1–8 observed-event frequency
classes. The control stays disabled when the API returns no labels.

### ML probability (historical susceptibility)

Joins the latest versioned spatial prediction index to the same 5,549 terrain
cells. Four probability bands, selected-cell label and model version, and
spatial-test metrics. Every label describes this as historical susceptibility,
not a live flood forecast.

### Event hindcast

Uses the rainfall-aligned v5 event model for held-out historical GFD events. The
event selector switches among validation and test dates. The inspector shows
probability, observed flooded share, validation-calibrated threshold, and test
metrics. This is not a future forecast or operational warning.

### Experimental forecast

The dashboard can trigger `POST /api/v1/flood-forecast/runs` and display the
latest forecast prediction index on the map. Forecast cells use live Open-Meteo
rainfall combined with ERA5 antecedent features through the v5 model. Treat this
as experimental analysis only.

## Situation overview and flood intelligence

The overview cards consume `/api/v1/flood-intelligence/summary` alongside
terrain screening, rainfall forecast, and station status. When available, they
show:

- Flood intelligence scenario headline (ML + SAR fusion)
- Flagged cell count and affected area
- Approximate buildings at risk (WorldCover built-up × 450/km²)
- Early-warning level and recommendation

Risk cards fall back to forecast, ML susceptibility, or terrain screening when
intelligence data is unavailable.

## Validation panel

The validation panel combines:

- **Historical event hindcast** — per-event TP/FP/FN metrics and threshold mode
- **Sentinel-1 SAR validation** — independent label comparison when SAR events
  are imported (`docs/SAR_FLOOD_LABELS.md`)

SAR metrics include precision/recall vs SAR, paired event table, and overall
model-vs-SAR scores from `artifacts/maubin_sar_label_validation.json`.

## Rainfall, sensors, and provenance

- Open-Meteo 1–7 day rainfall forecast cards
- ERA5 reanalysis chart with 30/90/366-day windows
- Registered stations, recent observations, and threshold alerts
- Live water-level chart fed by WebSocket (`NEXT_PUBLIC_WS_URL`)
- Data provenance section listing every active layer with licence and limitations

The historical-input panel visualizes area-weighted Maubin ERA5 reanalysis. ERA5
is coarse reanalysis for feature engineering — not a local gauge or flood warning.

## Configure

Copy the environment example:

```powershell
Copy-Item .env.example .env.local
```

Default:

```dotenv
API_BASE_URL=http://127.0.0.1:8000/api/v1
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8000/api/v1/ws/live
NEXT_PUBLIC_MAP_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
NEXT_PUBLIC_TERRAIN_TILEJSON_URL=https://tiles.mapterhorn.com/tilejson.json
NEXT_PUBLIC_CESIUM_TERRAIN_URL=https://elevation3d.arcgis.com/arcgis/rest/services/WorldElevation3D/Terrain3D/ImageServer
NEXT_PUBLIC_CESIUM_ION_TOKEN=
```

`API_BASE_URL` is server-only and is not bundled into browser JavaScript.
`NEXT_PUBLIC_API_URL` lets the browser load large terrain and screening datasets
after the initial page render. Its origin must be allowed by backend CORS.
`NEXT_PUBLIC_WS_URL` is public because the browser connects directly. Use
`wss://` when served over HTTPS.

Cesium requires static runtime assets. `predev` and `prebuild` run
`scripts/copy-cesium-assets.mjs` automatically.

## Read the map

Select `Susceptibility` and click a coloured 500 m cell. Red `VERY HIGH` cells
are higher screening priorities, not guaranteed flood probability. Use the
`2D` / `3D` / `Cesium` switch above the map. Vertical exaggeration (1×–8×)
changes presentation only — it is not flood depth or a model prediction.

## Run

Start the backend first:

```powershell
cd D:\geo-ai-floating-predection\backend
.\start.ps1
# or:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Then start the frontend:

```powershell
cd D:\geo-ai-floating-predection\frontend
pnpm dev
```

Open <http://127.0.0.1:3000>.

## Verify

```powershell
pnpm lint
pnpm build
```
