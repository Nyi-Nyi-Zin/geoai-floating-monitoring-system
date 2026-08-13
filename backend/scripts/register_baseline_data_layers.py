"""Idempotently register the real data sources already used by FloodGuard."""

from __future__ import annotations

from geoalchemy2.shape import to_shape
from shapely.geometry import Point, mapping
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.geo_asset import GeoAsset
from app.schemas.data_layer import DataLayerCreate
from app.services.data_layer import DataLayerService


def baseline_payloads(boundary: dict) -> list[DataLayerCreate]:
    return [
        DataLayerCreate(
            layer_key="maubin:osm-waterways:500m-v1",
            name="Maubin OpenStreetMap waterways",
            category="hydrography",
            data_kind="vector",
            provider="OpenStreetMap contributors",
            source_url="https://www.openstreetmap.org/",
            license_name="Open Data Commons Open Database License (ODbL)",
            license_url="https://www.openstreetmap.org/copyright",
            attribution="© OpenStreetMap contributors",
            usage_constraints=(
                "Attribution is required. ODbL share-alike obligations may apply "
                "when publicly using or distributing a derived database."
            ),
            coverage=boundary,
            update_frequency="Static local snapshot; refresh manually",
            quality_status="limited",
            quality_notes=(
                "Community-contributed waterways may be incomplete, outdated, "
                "misclassified, or missing local drainage channels. Field and "
                "local-authority verification is required."
            ),
            provenance={
                "asset_types": ["river_segment", "canal_segment"],
                "local_dataset_id": "maubin-osm-waterways-500m-v1",
                "processing": (
                    "Clipped to Maubin Township and divided into segments no "
                    "longer than 500 m."
                ),
            },
        ),
        DataLayerCreate(
            layer_key="maubin:copdem-glo30:2021",
            name="Copernicus DEM GLO-30 terrain",
            category="elevation",
            data_kind="raster",
            provider="European Union and European Space Agency",
            source_url=(
                "https://dataspace.copernicus.eu/explore-data/data-collections/"
                "copernicus-contributing-missions/collections-description/COP-DEM"
            ),
            license_name="Copernicus DEM GLO-30 free licence",
            license_url=(
                "https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/"
                "Data/DEM/resources/license/License-COPDEM-30.pdf"
            ),
            attribution=(
                "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 "
                "and © Airbus Defence and Space GmbH 2014-2018 provided under "
                "COPERNICUS by the European Union and ESA; all rights reserved"
            ),
            coverage=boundary,
            spatial_resolution_m=30,
            update_frequency="Static source tile",
            quality_status="verified",
            quality_notes=(
                "Source identity, resolution, and attribution were reviewed. "
                "This is a digital surface model, not a bare-earth survey; "
                "FloodGuard summarizes it into 500 m screening cells."
            ),
            provenance={
                "raster_source_key": "copdem:glo30:n16e095:2021",
                "terrain_dataset_id": "maubin-copdem-glo30-500m-v1",
                "source_tile": "N16E095",
                "derived_cell_size_m": 500,
                "citation_doi": "https://doi.org/10.5270/ESA-c5d3d65",
            },
        ),
        DataLayerCreate(
            layer_key="maubin:esa-worldcover:2021-v200",
            name="ESA WorldCover 10 m 2021 land cover",
            category="land_cover",
            data_kind="raster",
            provider="ESA WorldCover Consortium",
            source_url="https://esa-worldcover.org/en/data-access",
            license_name="Creative Commons Attribution 4.0 International",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            attribution=(
                "© ESA WorldCover project / Contains modified Copernicus "
                "Sentinel data (2021) processed by ESA WorldCover consortium"
            ),
            usage_constraints=(
                "Attribution is required when publishing the layer or derived "
                "products under CC BY 4.0."
            ),
            coverage=boundary,
            spatial_resolution_m=10,
            temporal_coverage_start="2021-01-01T00:00:00Z",
            temporal_coverage_end="2021-12-31T23:59:59Z",
            update_frequency="Static 2021 classification",
            quality_status="limited",
            quality_notes=(
                "Official global 10 m classification derived from Sentinel-1 "
                "and Sentinel-2. ESA reports 76.7% overall global accuracy for "
                "v200; class accuracy can vary locally and requires field or "
                "higher-resolution validation."
            ),
            provenance={
                "raster_source_key": "esa:worldcover:10m:2021:v200:maubin",
                "land_cover_dataset_id": (
                    "maubin-esa-worldcover-10m-2021-v200"
                ),
                "source_tile": "N15E093",
                "source_product": "ESA WorldCover 2021 v200",
                "derived_processing": (
                    "Cloud-Optimized GeoTIFF clipped to Maubin Township; class "
                    "shares summarized into existing 500 m terrain cells."
                ),
                "citation_doi": "https://doi.org/10.5281/zenodo.7254221",
            },
        ),
        DataLayerCreate(
            layer_key="maubin:copernicus-era5:2015-2025",
            name="Maubin Copernicus ERA5 daily rainfall history",
            category="historical_rainfall",
            data_kind="timeseries",
            provider=(
                "ECMWF Copernicus Climate Change Service; "
                "API delivery by Open-Meteo"
            ),
            source_url="https://open-meteo.com/en/docs/historical-weather-api",
            license_name="Copernicus C3S data licence and CC BY 4.0 API data",
            license_url="https://open-meteo.com/en/terms",
            attribution=(
                "ERA5 data by ECMWF/Copernicus; API delivery by Open-Meteo"
            ),
            usage_constraints=(
                "Retain provider attribution. Review Open-Meteo commercial "
                "terms and the Copernicus licence before production use."
            ),
            coverage=boundary,
            spatial_resolution_m=25_000,
            temporal_coverage_start="2015-01-01T00:00:00Z",
            temporal_coverage_end="2025-12-31T23:59:59Z",
            update_frequency="Static imported daily history; refresh manually",
            quality_status="limited",
            quality_notes=(
                "ERA5 is spatially complete model reanalysis, not local gauge "
                "measurement. Eight approximately 25 km grid cells are "
                "combined using township-intersection area weights."
            ),
            provenance={
                "rainfall_source_key": "copernicus:era5:maubin:daily-v1",
                "api_endpoint": (
                    "https://archive-api.open-meteo.com/v1/archive"
                ),
                "model": "era5",
                "daily_variable": "precipitation_sum",
                "grid_cell_count": 8,
                "aggregation": (
                    "Township-intersection area-weighted daily mean, maximum, "
                    "P90, and rolling 3/7/30-day totals."
                ),
                "source_doi": "https://doi.org/10.24381/cds.adbb2d47",
            },
        ),
        DataLayerCreate(
            layer_key="maubin:mimu-township-boundary:2020",
            name="Maubin Township boundary (MIMU 2020 via UNOSAT)",
            category="administrative_boundary",
            data_kind="vector",
            provider="Myanmar Information Management Unit; hosted by UNOSAT",
            source_url=(
                "https://unosat-geodrr.cern.ch/data/rest/services/Hosted/"
                "Township_Boundary_MIMU2020/FeatureServer"
            ),
            license_name="MIMU Data License",
            license_url="https://themimu.info/mimu-terms-conditions",
            attribution="Township boundary © MIMU; accessed via UNOSAT GeoDRR",
            usage_constraints=(
                "MIMU states that its geospatial datasets cannot be used on an "
                "online platform without prior written agreement. Keep this "
                "development deployment local unless permission is confirmed."
            ),
            coverage=boundary,
            update_frequency="Static 2020 snapshot",
            quality_status="limited",
            quality_notes=(
                "Reference-purpose Admin3 boundary, mainly digitized at "
                "1:250,000 scale. Boundaries and names do not imply UN "
                "endorsement; detailed use requires field validation."
            ),
            provenance={
                "asset_type": "township_boundary",
                "pcode": "MMR017019",
                "local_source_label": "MIMU Township Boundary 2020 via UNOSAT",
                "upstream_pcode_version": "9.3",
            },
        ),
        DataLayerCreate(
            layer_key="maubin:open-meteo:forecast",
            name="Maubin Open-Meteo rainfall forecast",
            category="weather_forecast",
            data_kind="service",
            provider="Open-Meteo",
            source_url="https://open-meteo.com/en/docs",
            license_name="CC BY 4.0 data; Open-Meteo free API terms",
            license_url="https://open-meteo.com/en/terms",
            attribution="Weather data by Open-Meteo.com",
            usage_constraints=(
                "The free API is for non-commercial use, is rate-limited, and "
                "has no uptime guarantee. Commercial use requires an "
                "appropriate subscription."
            ),
            coverage=mapping(Point(95.643, 16.712)),
            update_frequency="Provider-dependent model updates; cached 10 minutes",
            quality_status="limited",
            quality_notes=(
                "Model forecast for a representative Maubin coordinate. It is "
                "not observed rainfall and may differ across the township or "
                "change between model runs."
            ),
            provenance={
                "api_endpoint": "https://api.open-meteo.com/v1/forecast",
                "forecast_days": 7,
                "latitude": 16.712,
                "longitude": 95.643,
                "application_cache_ttl_seconds": 600,
            },
        ),
    ]


def register_baseline_layers() -> list[dict[str, str]]:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is required")

    db = SessionLocal()
    try:
        boundary_asset = db.scalar(
            select(GeoAsset)
            .where(GeoAsset.asset_type == "township_boundary")
            .order_by(GeoAsset.updated_at.desc())
            .limit(1)
        )
        if boundary_asset is None:
            raise RuntimeError(
                "Register the Maubin township boundary before data layers"
            )
        boundary = mapping(to_shape(boundary_asset.geometry))
        service = DataLayerService(db)
        registered = [
            service.upsert(payload)
            for payload in baseline_payloads(boundary)
        ]
        return [
            {
                "layer_key": feature.properties.layer_key,
                "quality_status": feature.properties.quality_status,
            }
            for feature in registered
        ]
    finally:
        db.close()


def main() -> None:
    registered = register_baseline_layers()
    print(f"Registered {len(registered)} baseline data layers.")
    for layer in registered:
        print(f"- {layer['layer_key']}: {layer['quality_status']}")


if __name__ == "__main__":
    main()
