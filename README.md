# FloodGuard Myanmar

GeoAI + IoT flood monitoring for **Maubin Township, Ayeyarwady Region, Myanmar**.

This README summarizes the current repository state: what is implemented, what you
can run locally, what remains incomplete, and how to start the MVP.

## Project Snapshot

FloodGuard combines:

- Spatial data in PostgreSQL + PostGIS
- Terrain screening from Copernicus DEM GLO-30
- Waterway layers from OpenStreetMap
- Historical flood evidence from the Global Flood Database (GFD)
- Independent Sentinel-1 SAR validation labels
- Historical rainfall from ERA5 and live forecast from Open-Meteo
- Historical susceptibility and rainfall-aligned event ML models (v5)
- Experimental live flood forecast runs
- Flood intelligence API fusing ML, SAR, exposure, and early-warning levels
- A Next.js dashboard with 2D, 3D MapLibre, and Cesium globe views
- Sensor station, MQTT, WebSocket, and threshold-alert plumbing

The codebase is a hackathon MVP and local demonstration platform. It is **not**
a production emergency-warning system.

## Repository Layout

```text
geo-ai-floating-predection/
├── backend/          FastAPI + PostGIS API, ML scripts, Alembic migrations
├── frontend/         Next.js 16 dashboard (FloodGuard / DeltaWatch UI)
├── iot/simulator/    MQTT sensor simulator for local demos
├── docs/             Model cards, SAR workflow, feature status
└── outputs/          Hackathon submission artifacts
```

Docker is not used. See `backend/README.md`, `frontend/README.md`, and
`backend/data/README.md` for detailed setup.

## Three Distinct Flood Products

The platform exposes three separate outputs. Do not treat them as interchangeable:

| Product | What it is | Operational use |
|---|---|---|
| **Terrain screening** | Relative 0–100 index from elevation, waterway proximity, and flatness | Prioritize cells for inspection before sensors exist |
| **Historical susceptibility** | Static ML baseline trained on GFD frequency labels | Explain past flood-prone areas, not live warnings |
| **Event hindcast / forecast** | Rainfall-aligned v5 model on historical events or live Open-Meteo input | Experimental analysis only until calibrated |

The **flood intelligence** layer combines these with SAR validation, building
exposure estimates, and early-warning classification — always with explicit
limitations in the API response.

## What Is Already Done

### Backend foundation

- FastAPI app with `/health`, `/api/v1/health`, Swagger, CORS, request IDs
- PostgreSQL/PostGIS models, Alembic migrations, and GeoJSON validation
- Generic `GeoAsset` CRUD with filtering, pagination, bbox search, and bulk import
- Auditable `DataLayer` catalog for source, licence, quality, and provenance
- Flood extent storage and GFD/SAR import pipelines
- Terrain screening API for relative flood-priority scoring
- Land-cover summary API from ESA WorldCover 2021
- Weather forecast and ERA5 rainfall history APIs
- Sensor station registration and ESP32/MQTT reading ingestion
- Deterministic threshold alerts and acknowledgement API
- Live WebSocket updates for new readings
- Historical susceptibility ML (`maubin-flood-susceptibility-logistic-v1`)
- Rainfall-aligned event model v5 with three threshold modes
- Experimental flood forecast run endpoints
- **Flood intelligence** endpoints (ML + SAR fusion, exposure, early warning)

### Frontend dashboard

- Server-rendered dashboard wired to ~15 backend endpoints
- 2D Leaflet, 3D MapLibre terrain, and Cesium globe views
- Terrain screening panel with factor breakdown
- Historical flood (GFD), ML susceptibility, event hindcast, and forecast layers
- Situation overview with flood intelligence risk cards and exposure estimates
- Validation panel for event hindcast metrics and Sentinel-1 SAR comparison
- Live water-level chart, rainfall forecast/history, data provenance cards

### Data and ML assets

- Maubin township boundary, OSM waterways, 500 m terrain grid, WorldCover enrichment
- ERA5 rainfall history (2015–2025) and 17 individual GFD events
- Optional Sentinel-1 SAR labels for independent validation
- Event catalog with HAND, rainfall, and terrain metadata
- Trained spatial susceptibility and v5 event model artifacts

## What Can Be Used Right Now

1. Open the dashboard and inspect Maubin map layers (2D / 3D / Cesium).
2. View terrain screening scores and factor contributions.
3. Browse river/canal segments and spatial assets.
4. Inspect land-cover shares per terrain cell.
5. See Open-Meteo rainfall forecast and ERA5 rainfall history.
6. Register a sensor station, ingest a reading, and watch the live chart update.
7. Trigger deterministic threshold alerts from station readings.
8. Inspect historical flood extents and ML susceptibility outputs.
9. Switch event hindcast layers and compare held-out GFD events.
10. Run an experimental flood forecast from the dashboard.
11. Review flood intelligence summary, SAR validation, and exposure estimates.

## What Is Still Missing

- Physical ESP32 field deployment and calibrated sensor hardware
- Strong authentication, authorization, and operator review workflow
- Production notification channels (SMS, WhatsApp, Telegram)
- Hydrologically calibrated flood depth and arrival-time forecasting
- Operational public warning certification
- Production deployment hardening, monitoring, backups, and incident handling

## Current Verification

Verified in this workspace:

- Backend test suite: **125 passed** (`pytest` from `backend/`)

Run frontend checks separately:

```powershell
cd frontend
pnpm lint
pnpm build
```

## Local Run

### Backend

```powershell
cd backend
.\start.ps1
# or:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

First-time setup: see `backend/README.md` for venv, `.env`, and `alembic upgrade head`.

### Frontend

```powershell
cd frontend
pnpm install   # first time only
pnpm dev
```

### Useful URLs

- Dashboard: `http://127.0.0.1:3000`
- Swagger: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`
- API health: `http://127.0.0.1:8000/api/v1/health`

## Main API Areas

- `/api/v1/geo-assets`
- `/api/v1/data-layers`
- `/api/v1/flood-extents`
- `/api/v1/flood-screening/terrain`
- `/api/v1/flood-screening/land-cover/summary`
- `/api/v1/weather/rainfall-forecast`
- `/api/v1/weather/rainfall-history`
- `/api/v1/stations` and `/api/v1/readings`
- `/api/v1/hydro-observations`
- `/api/v1/alerts`
- `/api/v1/ws/live`
- `/api/v1/mqtt/status`
- `/api/v1/flood-ml/*`
- `/api/v1/flood-forecast/*`
- `/api/v1/flood-intelligence/summary`
- `/api/v1/flood-intelligence/sar-validation`
- `/api/v1/flood-intelligence/exposure`

## Key Dataset Inventory

- Terrain cells: **5,549** (500 m grid)
- OSM river segments: **282**
- OSM canal segments: **21**
- ERA5 daily rainfall rows: **9,497**
- GFD individual Maubin flood events: **17**
- GFD aggregate frequency groups: **8** (473.488 km²)
- Event catalog: `backend/data/derived/maubin_flood_event_catalog.json`

## Documentation

| Document | Content |
|---|---|
| [`backend/README.md`](backend/README.md) | API setup, ML pipeline, MQTT, sensors |
| [`frontend/README.md`](frontend/README.md) | Dashboard layers, env vars, map views |
| [`backend/data/README.md`](backend/data/README.md) | Geospatial data preparation workflow |
| [`docs/SAR_FLOOD_LABELS.md`](docs/SAR_FLOOD_LABELS.md) | Sentinel-1 independent validation |
| [`docs/MODEL_CARD_FLOOD_EVENT.md`](docs/MODEL_CARD_FLOOD_EVENT.md) | v5 event model metrics |
| [`docs/CURRENT_FEATURES.md`](docs/CURRENT_FEATURES.md) | Feature status (Myanmar) |
| [`iot/simulator/README.md`](iot/simulator/README.md) | MQTT sensor simulator |

## Roadmap

### Priority 1

- Improve flood-model quality and reduce false alarms
- Expand SAR validation coverage and temporal calibration
- Compare more tabular models on the same splits

### Priority 2

- Version the experimental forecast pipeline with immutable input snapshots
- Show uncertainty and low-confidence zones more clearly in the dashboard

### Priority 3

- Add exposure layers (roads, villages, schools, hospitals, shelters)
- Operator review, override, alert deduplication, and escalation
- Authenticated notifications

### Priority 4

- Deploy real sensor stations with calibration and device security
- Upstream/downstream relationships and river-stage forecasting

### Priority 5

- Production deployment, backup/restore, monitoring, secrets, RBAC

## Notes

- The project is centered on Maubin Township.
- Historical flood labels are for training and validation, not live warnings.
- Forecast products and sensor readings must always show timestamps and source labels.
- The repository is organized as a modular monolith for the hackathon MVP.
