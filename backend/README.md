# GeoAI Flood Prediction API

The backend provides a reusable FastAPI and PostGIS foundation for auditable
flood decision-support workflows. The core entity is intentionally generic: a
`GeoAsset` can represent infrastructure, an administrative area, a hazard
footprint, a monitoring site, or another spatial object.

The current Maubin baseline stores waterways, the township boundary, and
terrain screening cells. A live weather-model rainfall forecast is available,
and the API can store time-stamped rainfall, river-level, and discharge
observations. It does not claim to predict flooding until observed river data,
historical flood labels, calibration, and human review are added.

## Requirements

- Python 3.11 or newer
- PostgreSQL 15 or newer
- PostGIS 3.x
- Permission to run `CREATE EXTENSION postgis` and `postgis_raster` in the
  target database

Docker is not used.

## Local setup

From `backend/`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

On macOS/Linux, activation is `source .venv/bin/activate` and the copy command
is `cp .env.example .env`.

Edit `.env` before running migrations. `.env` is gitignored and must not contain
credentials that are committed or pasted into logs.

```dotenv
APP_NAME=GeoAI Flood Prediction API
ENVIRONMENT=development
DEBUG=false
API_V1_PREFIX=/api/v1
DATABASE_URL=postgresql+psycopg://geoai_user:your-password@localhost:5432/geoai
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
WEATHER_PROVIDER_ENABLED=true
OPEN_METEO_BASE_URL=https://api.open-meteo.com/v1/forecast
WEATHER_CACHE_TTL_SECONDS=600
MAUBIN_FORECAST_LATITUDE=16.712
MAUBIN_FORECAST_LONGITUDE=95.643
MQTT_ENABLED=false
MQTT_BROKER_HOST=127.0.0.1
MQTT_BROKER_PORT=1883
MQTT_TOPIC=floodguard/stations/+/readings
MQTT_QOS=1
MQTT_CLIENT_ID=floodguard-backend
MQTT_USERNAME=
MQTT_PASSWORD=
MQTT_TLS_ENABLED=false
MQTT_KEEPALIVE_SECONDS=60
```

`CORS_ORIGINS` is a comma-separated allowlist. Do not use `*` with credentials
in production.

## Create the PostgreSQL/PostGIS database

Run the following as a PostgreSQL administrator. Replace the sample password:

```sql
CREATE ROLE geoai_user WITH LOGIN PASSWORD 'replace-with-a-strong-password';
CREATE DATABASE geoai OWNER geoai_user;
```

The initial Alembic migration runs:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

The database user therefore needs permission to create the extension. If the
deployment policy reserves extension management for an administrator, have the
administrator run `CREATE EXTENSION postgis;` once, then run migrations as the
application user.

The SQLAlchemy URL format is:

```text
postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE
```

Percent-encode reserved characters in credentials. Prefer a secret manager or
injected environment variable outside local development.

## Migrations

From `backend/`, with `.env` configured:

```powershell
alembic upgrade head
```

The initial migration enables PostGIS, creates `geo_assets`, uses EPSG:4326
(WGS84), adds an `asset_type` index, and adds a GiST spatial index.

## Start the API

```powershell
.\start.ps1
# or:
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

- Swagger UI: <http://127.0.0.1:8000/docs>
- Service health: <http://127.0.0.1:8000/health>
- Versioned API health: <http://127.0.0.1:8000/api/v1/health>
- Maubin rainfall forecast:
  <http://127.0.0.1:8000/api/v1/weather/rainfall-forecast>
- Latest gauge observations:
  <http://127.0.0.1:8000/api/v1/hydro-observations/latest>
- Registered sensor stations:
  <http://127.0.0.1:8000/api/v1/stations>
- Open water-level alerts:
  <http://127.0.0.1:8000/api/v1/alerts?status=open>
- Live sensor WebSocket: `ws://127.0.0.1:8000/api/v1/ws/live`
- MQTT bridge status:
  <http://127.0.0.1:8000/api/v1/mqtt/status>
- Relative terrain susceptibility screening:
  <http://127.0.0.1:8000/api/v1/flood-screening/terrain>
- Auditable data-layer catalog:
  <http://127.0.0.1:8000/api/v1/data-layers>

When `DATABASE_URL` is absent, health remains available and reports
`database.status: "not_configured"`. When a configured database cannot be
reached, it reports `"unhealthy"` and the overall service status is
`"degraded"`. Database-backed endpoints return a structured `503` if no
database is configured.

The rainfall endpoint retrieves Open-Meteo data on the server and caches each
forecast for 10 minutes by default. The public free endpoint is intended for
non-commercial use and requires attribution; review Open-Meteo's current terms
before production or commercial deployment. Provider failure is reported as a
structured `503` and does not create synthetic gauge readings.

## Historical flood extent labels

The `flood_extents` PostGIS table stores immutable, provenance-aware polygonal
training evidence separately from predictions. Each record includes event and
observation dates, sensor, classification, confidence, field-validation state,
source, licence, geodesic area, metadata, and WGS84 MultiPolygon geometry.

Available endpoints:

- `POST /api/v1/flood-extents`
- `GET /api/v1/flood-extents`
- `GET /api/v1/flood-extents/{extent_id}`

Use `scripts.import_flood_extents` to validate, repair, dissolve, and clip a
GeoJSON FeatureCollection to the stored Maubin boundary before upserting it:

```powershell
python -m scripts.import_flood_extents data/raw/maubin-gfd-flood-history-2000-2018.geojson `
  --source-key maubin:gfd:history:2000-2018 `
  --event-name "GFD observed flood frequency 2000-2018" `
  --observed-date 2018-12-10 `
  --sensor "MODIS Terra/Aqua" `
  --source-name "Global Flood Database v1" `
  --source-url "https://developers.google.com/earth-engine/datasets/catalog/GLOBAL_FLOOD_DB_MODIS_EVENTS_V1" `
  --license-name "CC BY-NC 4.0" `
  --confidence moderate `
  --group-by-property event_count
```

The imported Maubin composite currently produces eight non-empty frequency
groups (1–8 observed events) totaling 473.488 km² after township clipping.
Frequency groups 9–14 fell outside the stored township boundary and were
skipped. This is historical satellite evidence, not a current flood forecast.

`scripts/gee_export_maubin_gfd.js` is a Google Earth Engine Code Editor export
template for the Global Flood Database. It excludes JRC permanent water before
vectorization. Earth Engine sign-in/project access is required to run the
export. Do not substitute a nearby UNOSAT extent that does not intersect Maubin.

## Historical ML susceptibility baseline

After importing the GFD frequency composite and applying migrations, build the
cell-level dataset and train the reproducible NumPy logistic baseline:

```powershell
python -m scripts.train_flood_susceptibility
```

The script intersects every 500 m terrain cell with historical polygons,
exports `data/derived/maubin_flood_ml_dataset_v1.csv`, and derives:

- `flooded_fraction`
- `historical_event_count`
- `historical_event_density`
- binary target `flooded_fraction >= 0.10`
- deterministic spatial train, validation, and test blocks

Model inputs are 30 m DEM aggregates, OSM waterway proximity, and ESA
WorldCover 2021 shares. Township-aggregated ERA5 rainfall is deliberately not
used because it has no cell-level spatial variation and is not aligned to the
individual GFD event dates. The current 5,549-row baseline has a spatial-test
ROC-AUC of 0.7782, PR-AUC of 0.8111, and F1 of 0.7462. These are historical
susceptibility metrics, not operational forecast accuracy.

Available endpoints:

- `GET /api/v1/flood-ml/models/latest`
- `GET /api/v1/flood-ml/predictions/index`
- `GET /api/v1/flood-ml/event-readiness`
- `GET /api/v1/flood-ml/event-models/latest`
- `GET /api/v1/flood-ml/event-predictions/index?event_id=4666`

The index is compact and joins to terrain-cell IDs already loaded by the map.
It returns model version, metrics, methodology, labels, probability, risk band,
and per-cell explanations.

## Rainfall-aligned event model pipeline

The aggregate GFD frequency layer cannot be joined honestly to rainfall because
it has no individual event dates. Use the event-preserving Earth Engine export:

1. Open `scripts/gee_export_maubin_gfd_events.js` in the Earth Engine Code
   Editor, run it, start the Tasks export, and download
   `maubin-gfd-individual-events-2000-2018.geojson`.
2. Copy the file into `backend/data/raw/` and import it:

```powershell
python -m scripts.import_flood_events `
  data/raw/maubin-gfd-individual-events-2000-2018.geojson
```

The importer groups polygons by DFO `event_id`, verifies consistent start/end
dates, clips to Maubin, and upserts one extent per event. ERA5 rainfall is
available for 2000-01-01 through 2025-12-31. Check whether at least four event
dates align:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/flood-ml/event-readiness
```

When `ready` is `true`, build and evaluate the time-aware baseline:

```powershell
python -m scripts.train_flood_event_model
```

This creates event x terrain-cell labels, adds rainfall for the event start
date plus 3/7/30-day antecedent accumulation, and holds out the latest 20% of
events for testing and the preceding 20% for validation. It refuses to train
with fewer than four aligned events. The
result remains a historical baseline, not a live operational forecast.

The current 17-event run produces 94,333 event-cell rows. The active model is
`maubin-flood-event-logistic-v5` (`scripts/train_flood_event_model.py`). The v5
pipeline selects three operating thresholds using validation data only:
`screening` maximizes recall under a precision floor, `balanced` maximizes F1,
and `conservative` maximizes precision under a recall floor. Each mode also
selects a permanent-water temper coefficient jointly with the threshold.
Training uses a reduced positive-class weight scale (default 0.75) to push the
model away from false alarms. The dashboard can switch policies and show a
TP/FP/FN comparison map without retraining.

`GET /api/v1/flood-ml/event-models/evaluation` returns the held-out test
metrics, per-event table, rolling-origin CV summary, ranking diagnostics,
calibration ECE/MCE, false-positive diagnostics, and a deployment
recommendation. See `docs/MODEL_CARD_FLOOD_EVENT.md` for v5 held-out metrics.

Retrain with `python -m scripts.train_flood_event_model` to refresh artifacts
under `artifacts/maubin_flood_event_logistic_v5.json`. Artifacts include
per-event metrics and the strongest false-positive cells for spatial diagnosis.

Build the HYDRAFloods-style event metadata catalog after importing events:

```powershell
python -m scripts.build_flood_event_catalog
python -m scripts.add_hand_features   # optional MERIT HAND 100 m enrichment
```

Output: `data/derived/maubin_flood_event_catalog.json`

## Experimental flood forecast runs

When the v5 event model is trained, the forecast service fetches live
Open-Meteo rainfall, combines it with ERA5 antecedent accumulation, and runs
inference across all terrain cells. Each run is stored as an immutable record.

Available endpoints:

- `POST /api/v1/flood-forecast/runs`
- `GET /api/v1/flood-forecast/runs`
- `GET /api/v1/flood-forecast/runs/latest`
- `GET /api/v1/flood-forecast/runs/{run_id}`
- `GET /api/v1/flood-forecast/predictions/index`

This is an experimental forward-looking product. It uses the same v5 weights as
the event hindcast but with live weather input. Do not treat it as an
operational public warning.

## Sentinel-1 SAR independent validation

SAR labels are kept separate from GFD training data. Export from Earth Engine
(`scripts/gee_export_maubin_sar_events.js`), import with
`scripts.import_flood_sar_events`, then evaluate:

```powershell
python -m scripts.evaluate_sar_label_validation
```

Output: `artifacts/maubin_sar_label_validation.json`

Full workflow: `docs/SAR_FLOOD_LABELS.md`

## Flood intelligence

The flood intelligence service combines ML predictions, SAR observations,
building exposure, and early-warning classification into a single
decision-support response.

Available endpoints:

- `GET /api/v1/flood-intelligence/summary?event_id=&use_forecast=`
- `GET /api/v1/flood-intelligence/sar-validation`
- `GET /api/v1/flood-intelligence/exposure?use_forecast=`

The summary includes:

- ML + SAR scenario matrix (`low_risk`, `high_predicted_risk`,
  `observed_flood_alert`, `confirmed_high_risk`)
- Early-warning level (`LOW` / `MODERATE` / `HIGH` / `CRITICAL`) with
  recommendations
- Exposure estimates (flagged cells, affected km², buildings at risk from
  WorldCover built-up fraction)
- SAR validation status and readiness flags
- Explicit limitations (separate screening, susceptibility, and forecast
  products; exposure is approximate)

The dashboard consumes `/flood-intelligence/summary` in the situation overview
and validation panels.

## Sensor-independent terrain screening

`GET /api/v1/flood-screening/terrain` ranks all 500 m terrain cells using data
that is available before physical sensors are installed:

- 55% lower relative elevation
- 30% proximity to mapped rivers and canals
- 15% lower local relief (flatter terrain)

Each feature returns a 0–100 relative score, a `LOWER`, `MODERATE`, `HIGH`, or
`VERY_HIGH` screening band, and the observed value, normalized score, weight,
and contribution for every factor. The response also embeds methodology,
dataset provenance, band thresholds, and limitations. Use `band=VERY_HIGH` to
filter and `include_geometry=false` when joining scores to geometry already
loaded by a client.

`GET /api/v1/flood-screening/terrain/index` is the compact map contract. It
returns only cell IDs, scores, bands, and three normalized factor scores, while
the dashboard reuses geometry and observed terrain values from `GeoAsset`.

This is a transparent prioritization index, not flood probability, flood depth,
arrival time, or an ML prediction. It intentionally does not add forecast
rainfall to the score without a historical rainfall baseline and calibration.
The imported 2021 land-cover composition is shown as a separate evidence layer
and is not yet weighted in this score. Levees, drainage capacity, soil, tides,
river stage, historical flood extents, and field verification remain required
for an operational assessment.

## ESA WorldCover land-cover enrichment

`scripts.prepare_land_cover` clips the official ESA WorldCover 2021 v200 10 m
tile to Maubin Township, stores the clipped raster in PostGIS, and calculates
the class composition of every 500 m terrain cell:

```powershell
python -m scripts.prepare_land_cover `
  --source data/raw/ESA_WorldCover_10m_2021_v200_N15E093_Map.tif
```

Each terrain asset receives its dominant class and percentage composition.
`GET /api/v1/flood-screening/land-cover/summary` returns the township totals,
source metadata, attribution, and limitations. The dashboard's `Land cover`
layer visualizes the dominant class and shows the selected cell's top class
shares.

WorldCover is a descriptive 2021 classification, not live inundation, flood
probability, or an arrival-time prediction. It is kept outside
`terrain-screening-v1` until historical flood labels support calibration and
validation of any new weighting.

## Data provenance catalog

The `data_layers` table records source, provider, licence, attribution, spatial
coverage, resolution, temporal coverage, update frequency, quality status,
quality notes, usage constraints, and machine-readable provenance. Records are
deactivated or marked `deprecated` rather than deleted from the API, preserving
the audit trail.

After migrations, idempotently register the five real baseline inputs:

```powershell
python -m scripts.register_baseline_data_layers
```

The baseline catalog currently records:

- OpenStreetMap waterways as `limited` because community coverage may omit
  local drainage and ODbL obligations apply.
- Copernicus DEM GLO-30 as `verified` for reviewed identity, resolution, and
  attribution, while retaining DSM/500 m summary limitations.
- ESA WorldCover 2021 v200 as `limited`, with its 10 m source resolution,
  CC BY 4.0 attribution, global accuracy context, reference year, and warning
  that it is not live flood water.
- MIMU 2020 township boundary as `limited`, including its 1:250,000 reference
  scale and prior-written-agreement condition for online platforms.
- Open-Meteo forecast as `limited`, including free-tier non-commercial terms,
  rate limits, lack of an uptime guarantee, and forecast uncertainty.

## Register a sensor station and ingest a reading

Register the physical station once. Replace the example values with the actual
installation metadata:

```powershell
$station = @{
  station_id = "MAUBIN-01"
  name = "Maubin river gauge"
  river_name = "Maubin River"
  status = "offline"
  warning_level_cm = 250
  danger_level_cm = 300
  critical_level_cm = 350
  geometry = @{
    type = "Point"
    coordinates = @(95.643, 16.712)
  }
} | ConvertTo-Json -Depth 4

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/stations `
  -ContentType application/json `
  -Body $station
```

The ESP32 ingestion endpoint accepts the documented camel-case message:

```powershell
$reading = @{
  stationId = "MAUBIN-01"
  timestamp = "2026-07-29T12:00:00+06:30"
  waterLevelCm = 185.4
  rainfallMm = 4.2
  soilMoisture = 72
  batteryLevel = 88
  source = "esp32"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/readings `
  -ContentType application/json `
  -Body $reading
```

The station must be registered first. Re-sending the same station, timestamp,
and source is idempotent and returns the existing reading instead of creating a
duplicate. A received reading changes an `offline` station to `active` and
updates `last_seen_at`. Raw device readings start as `unverified`.

If all three station thresholds are configured, each real water-level reading
is classified deterministically:

- below warning: `LOW` and no alert record
- at or above warning: `MEDIUM`
- at or above danger: `HIGH`
- at or above critical: `CRITICAL`

Threshold crossings create an immutable alert linked to the source observation.
This is a rule-based operational warning, not an ML flood prediction. If the
station has no complete threshold set, classification is `UNAVAILABLE` and no
alert is created.

An operator can acknowledge an alert without deleting its history:

```powershell
$acknowledgement = @{
  acknowledged_by = "operator-name"
  notes = "Field team contacted."
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Patch `
  -Uri http://127.0.0.1:8000/api/v1/alerts/ALERT_UUID/acknowledge `
  -ContentType application/json `
  -Body $acknowledgement
```

Acknowledgement identity is caller-supplied in the current local MVP. Add
authentication and derive operator identity from the authenticated account
before public deployment.

## Live reading events

The ESP32 HTTP ingestion endpoint broadcasts each newly created reading over:

```text
ws://127.0.0.1:8000/api/v1/ws/live
```

The connection first receives:

```json
{"type":"connected","channel":"sensor-readings"}
```

Each non-duplicate reading then emits a `sensor_reading` event whose `data`
field is the stored GeoJSON observation. Duplicate retries are returned
idempotently by the HTTP endpoint but are not broadcast again.

This broadcaster is intentionally in-process for the single-worker local MVP.
For multiple backend workers or multiple hosts, replace its fan-out internals
with Redis or MQTT while preserving the event payload contract. The dashboard
will reconnect automatically if the live channel drops.

## MQTT bridge

MQTT ingestion is installed but disabled in `.env.example`, so the API starts
normally when a broker is not running. On this Windows development machine, the
standard Mosquitto service remains on port `1883` and FloodGuard uses a separate
localhost-only authenticated broker on port `1884`.

After installing Mosquitto, configure a local-only development credential in
`.env`:

```dotenv
MQTT_ENABLED=true
MQTT_BROKER_HOST=127.0.0.1
MQTT_BROKER_PORT=1884
MQTT_TOPIC=floodguard/stations/+/readings
MQTT_QOS=1
MQTT_CLIENT_ID=floodguard-backend
MQTT_USERNAME=floodguard-backend
MQTT_PASSWORD=replace-with-a-local-development-password
MQTT_TLS_ENABLED=false
```

Then create and start the secured project broker from `backend/`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_local_mosquitto.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_local_mosquitto.ps1
```

The generated password hash, ACL, broker configuration, and logs are stored
under `%LOCALAPPDATA%\FloodGuard\mosquitto`, outside the repository. Run the
start script again after a reboot; it exits successfully when the broker is
already available.

Restart FastAPI after changing `.env`. The bridge uses the Paho v2 callback API
and reconnects automatically. A station publishes to:

```text
floodguard/stations/MAUBIN-01/readings
```

using the same JSON accepted by `POST /api/v1/readings`:

```json
{
  "stationId": "MAUBIN-01",
  "timestamp": "2026-07-29T12:00:00+06:30",
  "waterLevelCm": 185.4,
  "rainfallMm": 4.2,
  "soilMoisture": 72,
  "batteryLevel": 88,
  "source": "esp32"
}
```

The station must already exist in `sensor_stations`. The topic station ID must
match the payload `stationId`; mismatches and invalid messages are rejected and
counted in `/api/v1/mqtt/status`. Valid messages reuse the HTTP ingestion
service, duplicate protection, threshold alerts, and WebSocket broadcast.

`MQTT_USERNAME` and `MQTT_PASSWORD` are never returned by the status API. The
local project broker listens only on `127.0.0.1` and disallows anonymous
clients. For a field deployment, use TLS, unique device credentials,
per-station publish-only ACLs, a backend read-only subscription, and rotated
secrets. The scripts configure the separate project broker; they do not install
Mosquitto or modify the Windows Mosquitto service.

## Record a manual gauge observation

The dashboard intentionally shows `Awaiting data` until a real station reading
is submitted. A manual or third-party observation can be recorded with:

```powershell
$body = @{
  station_id = "MAUBIN-01"
  station_name = "Maubin river gauge"
  observed_at = "2026-07-29T12:00:00+06:30"
  water_level_m = 2.45
  source = "field-team"
  quality_status = "provisional"
  geometry = @{
    type = "Point"
    coordinates = @(95.643, 16.712)
  }
} | ConvertTo-Json -Depth 4

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/hydro-observations `
  -ContentType application/json `
  -Body $body
```

Replace the example coordinates, timestamp, value, source, and station metadata
with the actual instrument reading. Do not submit the example as real data.
The write endpoints are currently an unauthenticated local-development
interface; add authentication and station credentials before public deployment.

## API examples

Create a telecom tower (the same endpoint also supports flood zones, sensor
sites, suitability polygons, and other asset types):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/geo-assets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tower MM-001",
    "asset_type": "telecom_tower",
    "description": "Example infrastructure asset",
    "geometry": {
      "type": "Point",
      "coordinates": [96.1951, 16.8661]
    },
    "properties": {
      "operator": "example",
      "technology": ["4G", "5G"]
    }
  }'
```

The response is a GeoJSON Feature:

```json
{
  "type": "Feature",
  "id": "6462f93f-6f3c-4e55-8471-a7e759ccf329",
  "geometry": {
    "type": "Point",
    "coordinates": [96.1951, 16.8661]
  },
  "properties": {
    "name": "Tower MM-001",
    "asset_type": "telecom_tower",
    "description": "Example infrastructure asset",
    "metadata": {
      "operator": "example",
      "technology": ["4G", "5G"]
    },
    "created_at": "2026-07-26T07:00:00Z",
    "updated_at": "2026-07-26T07:00:00Z"
  }
}
```

List and filter:

```bash
curl "http://127.0.0.1:8000/api/v1/geo-assets?page=1&page_size=20"
curl "http://127.0.0.1:8000/api/v1/geo-assets?asset_type=telecom_tower"
```

Query assets intersecting a bounding box:

```bash
curl "http://127.0.0.1:8000/api/v1/geo-assets/within-bounds?min_lon=95&min_lat=15&max_lon=98&max_lat=18&page=1&page_size=20"
```

Bulk-import a prepared GeoJSON FeatureCollection:

```bash
python -m scripts.import_geojson data/processed/maubin_township_waterways.geojson
```

The endpoint is `POST /api/v1/geo-assets/import`. Each input Feature must use
the prepared properties structure shown below:

```json
{
  "type": "Feature",
  "geometry": {
    "type": "LineString",
    "coordinates": [[95.6, 16.7], [95.7, 16.8]]
  },
  "properties": {
    "source_key": "osm:waterway:way/123:segment:0001",
    "name": "Example river",
    "asset_type": "river_segment",
    "description": "Clipped to the project area.",
    "metadata": {
      "source": "OpenStreetMap",
      "osm_id": "way/123"
    }
  }
}
```

For the Maubin OSM preparation commands, local file layout, attribution, and
boundary publishing restriction, see [`data/README.md`](data/README.md).
Bulk import is atomic and limited to 1,000 features per request. It uses each
Feature's stable `source_key` as an upsert key, so re-importing the same prepared
file updates the matching assets instead of creating duplicates.

Read, patch, and delete:

```bash
curl http://127.0.0.1:8000/api/v1/geo-assets/ASSET_UUID
curl -X PATCH http://127.0.0.1:8000/api/v1/geo-assets/ASSET_UUID \
  -H "Content-Type: application/json" \
  -d '{"properties":{"review_priority":"high"}}'
curl -X DELETE http://127.0.0.1:8000/api/v1/geo-assets/ASSET_UUID
```

Incoming geometry must be a non-empty, valid GeoJSON geometry in EPSG:4326.
Longitudes must be from -180 to 180 and latitudes from -90 to 90. A GeoJSON
`Feature` is not accepted as the `geometry` field; submit its geometry object.
Invalid input returns a structured `422` response with specific validation
details and a request ID.

List and bounding-box responses are GeoJSON FeatureCollections with a `meta`
foreign member containing `page`, `page_size`, `total`, and `pages`.

## Tests

Tests do not require PostgreSQL:

```powershell
pytest
```

They cover health routes, docs availability, honest no-database behavior,
GeoJSON validation, flood ML and forecast logic, flood intelligence scenario
classification, SAR label filtering, and structured HTTP validation errors.
The current suite collects **125 tests**. Integration tests against PostGIS
should be added to CI once a dedicated test database is available.

## Phase 1 complete

- FastAPI application metadata, `/docs`, `/health`, and `/api/v1/health`
- Environment-driven configuration and CORS
- Structured client and server error envelopes with request IDs
- SQLAlchemy 2.x session and model setup
- Alembic migration enabling PostGIS
- Generic UUID-based `GeoAsset` with JSONB metadata, timestamps, WGS84 geometry,
  `asset_type` index, and GiST spatial index
- Create, list, read, patch, delete, filtering, pagination, and bounding-box API
- Atomic, idempotent prepared-GeoJSON bulk import and a repeatable OSM waterway
  clipping workflow that divides Maubin Township waterways into monitoring
  segments of at most 500 metres
- PostGIS raster storage and a repeatable Copernicus DEM workflow that creates
  500 m terrain screening cells with elevation statistics, local relief,
  elevation percentile, and waterway distance
- Repeatable ESA WorldCover 2021 workflow that clips the 10 m source raster,
  stores it in PostGIS, and enriches all terrain cells with land-cover shares
- Explainable relative terrain susceptibility API with factor contributions,
  band summaries, data provenance, and explicit non-prediction limitations
- Provenance-aware historical flood-label table, API, GeoJSON importer, Maubin
  clipping/dissolve workflow, and Google Earth Engine export template
- Auditable `DataLayer` catalog, quality/lifecycle filters, spatial coverage,
  API registration/update, and idempotent real-baseline registration
- GeoJSON Feature and FeatureCollection responses
- Pre-database GeoJSON validation with useful errors
- A prediction service boundary that requires risk score, confidence, model
  version, explanation, contributing factors, and human review state
- Unit/API tests for the non-database foundation

## Recommended Phase 2

Build an auditable observation-and-prediction module rather than adding model
fields directly to `GeoAsset`:

1. `DataLayer` for hazard/environmental rasters or vectors, with source,
   license, spatial/temporal coverage, resolution, quality, and provenance.
2. `Observation` for time-stamped network KPIs or environmental measurements
   linked to a GeoAsset, including units and quality flags.
3. Immutable `Prediction` records containing risk score, confidence, model
   version, input snapshot/provenance, explanation, and contributing factors.
4. `PredictionReview` with reviewer identity, pending/accepted/overridden
   status, override reason, timestamp, and an appeal/correction channel.
5. Spatial/temporal integration tests and per-area data-quality monitoring.

This structure supports telecommunications outage/coverage risk, flood risk,
and spatial suitability without locking the platform to one domain. It also
implements the source materials' key safety rule: confidence and explanations
must be visible, and consequential action must remain subject to named human
review.
