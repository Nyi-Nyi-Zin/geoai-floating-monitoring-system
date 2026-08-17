import json
import os
from functools import lru_cache
from urllib.request import urlopen

from fastapi import FastAPI, HTTPException

app = FastAPI(title="DeltaWatch Spatial API", version="1.0.0")

SEED_BASE_URL = os.getenv("SPATIAL_SEED_BASE_URL", "http://127.0.0.1:3000")
SPATIAL_SEED_PATH = "/manus-storage/maubin_spatial_seed_08a16481.json"
HINDCAST_SEED_PATH = "/manus-storage/maubin_hindcast_seed_v7_e80e6338.json"
RAINFALL_SEED_PATH = "/manus-storage/maubin_rainfall_seed_b7223d86.json"
MYANMAR_ADMIN_SEED_PATH = "/manus-storage/myanmar_admin_seed_v1_ff8b1711.json"
MYANMAR_ADMIN_DISPLAY_PATH = "/manus-storage/myanmar_admin1_display_v1_bbe6a3f3.json"
MYANMAR_ADMIN_PARTITIONS_PATH = "/manus-storage/myanmar_admin1_partitions_v1_a330f15d.json"


def load_json(path: str) -> dict:
    with urlopen(f"{SEED_BASE_URL}{path}", timeout=45) as response:
        return json.load(response)


@lru_cache(maxsize=3)
def spatial_seed() -> dict:
    return load_json(SPATIAL_SEED_PATH)


@lru_cache(maxsize=1)
def hindcast_seed() -> dict:
    return load_json(HINDCAST_SEED_PATH)


@lru_cache(maxsize=1)
def rainfall_seed() -> dict:
    return load_json(RAINFALL_SEED_PATH)


@lru_cache(maxsize=1)
def myanmar_admin_seed() -> dict:
    return load_json(MYANMAR_ADMIN_SEED_PATH)


@lru_cache(maxsize=1)
def myanmar_admin_display_seed() -> dict:
    return load_json(MYANMAR_ADMIN_DISPLAY_PATH)


@lru_cache(maxsize=1)
def myanmar_admin_partition_seed() -> dict:
    return load_json(MYANMAR_ADMIN_PARTITIONS_PATH)


def feature_type(feature: dict) -> str:
    return str(feature.get("properties", {}).get("asset_type", ""))


@app.get("/health")
def health() -> dict:
    try:
        features = spatial_seed().get("features", [])
        return {"ok": True, "spatial_db": "seeded_postgis_export", "feature_count": len(features)}
    except Exception as error:
        return {"ok": False, "error": str(error)}


@app.get("/metadata")
def metadata() -> dict:
    features = spatial_seed().get("features", [])
    terrain = [f for f in features if feature_type(f) == "terrain_cell"]
    bands = {"LOWER": 0, "MODERATE": 0, "HIGH": 0, "VERY_HIGH": 0}
    for feature in terrain:
        band = str(feature.get("properties", {}).get("screening_band", "LOWER"))
        if band in bands:
            bands[band] += 1
    model = hindcast_seed().get("model", {})
    return {
        "terrain_cell_count": len(terrain),
        "band_counts": bands,
        "event_count": len(hindcast_seed().get("events", [])),
        "model": model,
        "risk_basis": "terrain_screening",
    }


@app.get("/terrain")
def terrain() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            feature
            for feature in spatial_seed().get("features", [])
            if feature_type(feature) == "terrain_cell"
        ],
    }


@app.get("/waterways")
def waterways() -> dict:
    allowed = {"township_boundary", "river_segment", "canal_segment"}
    return {
        "type": "FeatureCollection",
        "features": [
            feature
            for feature in spatial_seed().get("features", [])
            if feature_type(feature) in allowed
        ],
    }


@app.get("/flood-events")
def flood_events() -> dict:
    return {"events": hindcast_seed().get("events", []), "model": hindcast_seed().get("model", {})}


@app.get("/hindcast/{event_id}")
def hindcast(event_id: str) -> dict:
    seed = hindcast_seed()
    event = next((item for item in seed.get("events", []) if str(item.get("id")) == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Unknown GFD event")
    predictions = [item for item in seed.get("predictions", []) if str(item.get("event_id")) == event_id]
    return {"event": event, "model": seed.get("model", {}), "predictions": predictions}


@app.get("/rainfall-history")
def rainfall_history() -> dict:
    return rainfall_seed()


@app.get("/national-admin/metadata")
def national_admin_metadata() -> dict:
    seed = myanmar_admin_seed()
    return {
        "schema": seed.get("schema"),
        "source": seed.get("source"),
        "coverage": seed.get("coverage"),
    }


@app.get("/national-admin/boundary")
def national_admin_boundary() -> dict:
    return myanmar_admin_seed().get("admin0", {"type": "FeatureCollection", "features": []})


@app.get("/national-admin/regions")
def national_admin_regions() -> dict:
    return myanmar_admin_display_seed().get("admin1", {"type": "FeatureCollection", "features": []})


@app.get("/national-admin/partitions")
def national_admin_partitions() -> dict:
    seed = myanmar_admin_partition_seed()
    return {
        "schema": seed.get("schema"),
        "source": seed.get("source"),
        "status": seed.get("status"),
        "partitions": seed.get("partitions", []),
    }
