# Sentinel-1 SAR independent flood labels

Independent validation labels derived from Copernicus Sentinel-1 GRD VH change
detection. These are **not** MODIS/GFD training labels and should be used to
measure label noise and model generalization without mixing sensors in training.

## Workflow

### 1. Export from Google Earth Engine

Open `backend/scripts/gee_export_maubin_sar_events.js` in the
[Earth Engine Code Editor](https://code.earthengine.google.com), run it with an
authorized project, and download the completed GeoJSON task from Google Drive into:

```text
backend/data/raw/maubin-sar-individual-events.geojson
```

The script implements a HYDRAFloods-inspired multi-method pipeline:

- Speckle reduction via focal median on VH composites
- **Method A:** VH ratio (during/pre) threshold
- **Method B:** Absolute VH backscatter threshold
- **Method C:** VH delta (pre − during) change detection
- **Permanent water mask:** JRC Global Surface Water (occurrence ≥ 50%)
- **Terrain constraint:** MERIT HAND ≤ 15 m
- Detected water − permanent water = **temporary flood**

Each export row uses `event_id = sar-{gfd_event_id}` and
`reference_gfd_event_id` for GFD pairing. `permanent_water_excluded: true`.

### 2. Import into PostGIS

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m scripts.import_flood_sar_events `
  data/raw/maubin-sar-individual-events.geojson
```

Dry-run first if needed:

```powershell
.\.venv\Scripts\python.exe -m scripts.import_flood_sar_events `
  data/raw/maubin-sar-individual-events.geojson --dry-run
```

Imported rows use:

- `source_key`: `maubin:sar:event:{event_id}`
- `sensor`: `Sentinel-1`
- `properties.label_source`: `sar`

GFD training labels remain under `maubin:gfd:event:*` and are unchanged.

### 3. Check readiness

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/flood-ml/event-readiness
```

Look for:

- `sar_event_count` > 0
- `sar_validation_ready`: true (SAR events aligned with ERA5 rainfall)

### 4. Run independent validation

Compare GFD vs SAR label agreement and score the existing v5 model on SAR
targets **without retraining**:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_sar_label_validation
```

Output: `artifacts/maubin_sar_label_validation.json`

## Label source filtering

Training and dataset export default to GFD labels only:

```powershell
# Default — GFD training labels (unchanged behavior)
.\.venv\Scripts\python.exe -m scripts.build_flood_event_dataset

# SAR-only dataset (for analysis, not default training)
.\.venv\Scripts\python.exe -m scripts.build_flood_event_dataset --label-source sar
```

Do **not** use `--label-source all` for training; it mixes independent sensors.

## Interpretation

| Metric | Meaning |
|---|---|
| GFD vs SAR label agreement | How much label noise exists between sensors |
| Model vs SAR precision/recall | Generalization estimate on independent targets |
| Low agreement | Expected — MODIS 250 m vs SAR 10 m, different methods |

SAR labels improve **evaluation honesty**, not automatic precision gains. If
agreement is low, the bottleneck is label quality/signal, consistent with the
model comparison results in `docs/MODEL_CARD_FLOOD_EVENT.md`.

## Licensing

Sentinel-1 data is subject to Copernicus Data Space Ecosystem / ESA terms.
Confirm attribution and usage before any public deployment.
