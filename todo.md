# Project TODO

- [x] Document the permanent hosting architecture, including the Node server, colocated FastAPI spatial API, persistent data model, and autoscale constraints.
- [x] Build a polished full-screen Maubin Leaflet map with satellite and terrain basemaps.
- [x] Add township-boundary, river, canal, terrain-risk, historical-flood, grid-cell, and label layer controls.
- [x] Persist and serve the 5,549 terrain-screening cells with LOWER, MODERATE, HIGH, and VERY_HIGH bands.
- [x] Add live seven-day Open-Meteo rainfall bars and a thirty-day rainfall-history sparkline.
- [x] Persist pixel-level GFD v3 event polygons for the 17 historical events and expose a historical-flood layer.
- [x] Add a v6 experimental event-hindcast panel with per-cell probabilities and an always-visible precision/recall disclaimer.
- [x] Add a system status bar with exact terrain_screening risk-basis label, spatial database status, and open-alert count.
- [x] Create an accessible About and methodology modal naming Copernicus DEM, ESA WorldCover, GFD v3, and ERA5 with model limitations.
- [x] Create deploy-compatible Python/FastAPI spatial-service integration and a custom Dockerfile with required client libraries.
- [x] Add an idempotent nightly /api/scheduled rainfall handler that upserts current-month Open-Meteo data into rainfall_history.
- [x] Add schema migrations, seed data, service tests, API tests, and UI tests for core monitoring flows.
- [x] Verify responsive visual rendering, create a final checkpoint, and prepare the site for user-initiated publishing.
- [ ] After publication, create and verify the project-level nightly Heartbeat job.
