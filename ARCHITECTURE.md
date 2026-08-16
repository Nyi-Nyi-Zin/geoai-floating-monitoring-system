# DeltaWatch permanent architecture

DeltaWatch is a public Maubin Township flood-intelligence dashboard designed for autoscaling deployment. It is an analytical screening and historical-hindcast product rather than a life-safety forecasting system. The browser receives the interactive Leaflet interface from the React client, while the Express server owns the tRPC monitoring endpoints, the spatial proxy, and the scheduled rainfall-refresh handler.

| Component | Responsibility | Durable dependency |
|---|---|---|
| React and Leaflet client | Renders map layers, rainfall cards, historical events, model metrics, controls, and methodology content. | Managed web-storage seed files and server APIs. |
| Express and tRPC server | Serves the web app, exposes weather status, proxies spatial data, and receives the scheduled rainfall-refresh request. | Managed MySQL/TiDB database and built-in platform services. |
| Colocated FastAPI service | Reads compact spatial seeds and delivers terrain cells, waterways, flood events, hindcast cells, and rainfall history through `/api/spatial/*`. | Managed web storage. |
| Managed MySQL/TiDB | Stores idempotently upserted rainfall history and one schedule configuration record. | Platform database. |
| Heartbeat job | Calls `/api/scheduled/rainfall-refresh` nightly after the site is published. | Deployed HTTP endpoint and schedule configuration table. |

The spatial service runs within the same deployment container as the Node application because the map requires a lightweight geographic-data endpoint rather than a separately managed GIS cluster. Its JSON inputs remain in managed storage rather than in the application image, avoiding large static-file deployments. The custom Dockerfile packages the Node runtime, Python 3.12, FastAPI, and required PostGIS client libraries to keep this colocated pattern deployable under the platform’s autoscaling model.

The nightly refresh handler obtains current-month precipitation from Open-Meteo, computes seven-day accumulations, and upserts records using the unique `source_key` and `observed_date` pair. It is safe to invoke more than once because existing dates are updated rather than duplicated. The scheduled job must be created only after publication, when the public deployment endpoint is available; its returned task identifier is then persisted in `schedule_configs`.

> **Operational limitation:** autoscaling instances are transient. The service does not rely on local files written at runtime, background daemons, or in-memory schedule state. Persisted rainfall data lives in the managed database, while immutable geographic seeds live in managed storage.
