# Nationwide scope source notes

- The Myanmar Information Management Unit country-overview page was access-blocked during retrieval and was not used as direct evidence.
- Northwestern Pritzker Legal Research Center's Administrative Structure & Maps page states that Myanmar is divided into seven States, seven Regions, and one Union Territory under the 2008 Constitution. It also links MIMU geospatial data covering State/Region, District, Township, Village Tract, Village, and special-region levels, along with administrative boundaries, roads, waterways/physical maps, land use/land cover, and related layers.
- Source URL: https://library.law.northwestern.edu/myanmar/maps
- The administrative count is a scope reference, not a claim that every listed boundary or source is current for operational use. Current boundary data and licensing/provenance must be verified before production ingestion.

## Additional sizing and access findings

UNdata lists Myanmar’s surface area as **676,577 km²**. This is suitable only for transparent, order-of-magnitude grid sizing; a nationwide analysis must use a verified land/water mask and valid boundary geometry rather than filling this entire surface area with cells.

The MIMU GeoNode layers endpoint was access-blocked during retrieval. Search discovery describes a nationwide administrative-boundary layer covering Admin 1, 2, 3, international, and sea boundaries, but this statement is not treated as an ingestible source until the actual dataset, its provenance, vintage, licence, and download endpoint are verified.

Source URLs:

- https://data.un.org/en/iso/mm.html
- https://geonode.themimu.info/layers/

## Vetted nationwide boundary acquisition

The OCHA Humanitarian Data Exchange (HDX) Myanmar Subnational Administrative Boundaries (COD-AB) dataset was directly accessible and identifies MIMU as its source. Its dataset page reports version 01, review for accuracy on 30 October 2025, annual expected updates, and a GeoJSON archive modified on 14 August 2026. It documents one Admin 0 boundary, 18 Admin 1 State/Region records, 80 Admin 2 districts, and 330 Admin 3 townships. The package was downloaded without executing any code and reduced only to Admin 0 and Admin 1 features for the nationwide monitoring index.

The prepared Admin 1 seed preserved each source feature’s P-code, English and Myanmar names, version, validity date, area, and representative center. The first source record reports `valid_on: 2024-02-15`; the seed’s source metadata retains this date and does not present it as a current flood-data timestamp.

Source URL: https://data.humdata.org/dataset/cod-ab-mmr

## Nationwide waterways sources

HydroRIVERS version 1 is a global vector river network extracted from HydroSHEDS core layers at 15 arc-second resolution. It represents rivers meeting a catchment-area threshold of at least 10 km² or an average-flow threshold of at least 0.1 m³/s, and provides reach length, upstream and outlet distance, stream order, and an estimated long-term average discharge. Its Asia download is 91 MB in shapefile form and 103 MB in geodatabase form; the source states that the database is available for scientific, educational, and commercial use under the HydroSHEDS terms. It is the preferred source for a stable, nationwide analytical river-network feature because it is consistent across borders, but it is not a real-time hydrometric feed and omits smaller waterways below its inclusion threshold.

The HOT OpenStreetMap Waterways of Myanmar dataset is a complementary local map-context source. Its HDX page identifies OpenStreetMap contributors as the source, lists a 6 August 2026 time period and monthly expected updates, and provides a 38.2 MB GeoJSON download. The dataset’s interactive report records 69,562 mixed-geometry features. It is appropriate for contextual map display and possible local feature enrichment after geometry/attribute quality checks, but contributor completeness is spatially variable and it must not be treated as calibrated discharge, channel capacity, or flood-outcome data.

Source URLs:

- https://www.hydrosheds.org/products/hydrorivers
- https://data.humdata.org/dataset/hotosm_mmr_waterways

## Nationwide land-cover source (pending technical extract)

The official ESA WorldCover data-access page exposes WorldCover 2020 v100 and WorldCover 2021 v200 products, product-user manuals and validation reports, viewer and OGC service routes, AWS Open Data access, and a Creative Commons Attribution 4.0 International License link. The full technical description will be retained with the assessment before the layer is ingested; this note does not yet claim a model-ready Myanmar land-cover feature.

Source URL: https://esa-worldcover.org/en/data-access

ESA WorldCover is a global 10 m land-cover product for 2020 and 2021 based on Sentinel-1 and Sentinel-2 data. The official access documentation states that the annual composites use different algorithm versions in 2020 and 2021, provides Cloud-Optimized GeoTIFF tiles in 1° by 1° WGS84 grid cells, and makes the products available free of charge under CC BY 4.0. It is suitable as a static historical baseline after tile-level provenance and resampling are documented, but it is not an operational land-use update feed or direct flood label.

## HydroRIVERS Admin 1 static aggregation (verified)

The documented 91 MB HydroRIVERS Asia version 1 shapefile archive was downloaded from the official HydroSHEDS delivery endpoint and inspected before use. Its source layer contains 1,428,959 Asia reaches and retains source reach length, catchment area, estimated long-term average discharge, and Strahler stream-order attributes. The archived download and expanded source remain outside the deployed web project under `/home/ubuntu/nationwide-data/hydrorivers/`.

Each Myanmar Admin 1 source polygon was intersected with candidate river-reach geometry, and geodesic lengths were calculated only for the clipped portions of those reaches. The resulting, reproducible output is `/home/ubuntu/deltawatch-model-outputs/myanmar_admin1_hydrorivers_static.json`. It contains 18 regional static summaries, with no zero-reach regions, and a countrywide total of 248,300.802 km of clipped HydroRIVERS linework. The apparently high total reflects the source's broad, static network coverage and its inclusion threshold; it is not a measurement of navigable channel length or drainage capacity.

The regional descriptors are **intersecting reach count**, **clipped river length**, **longest clipped reach**, **maximum Strahler order**, and **length-weighted mean source discharge estimate**. They are retained as static geographical context only. The process did not fit a model, create a risk score or probability, generate a forecast, or issue an alert. HydroRIVERS does not provide current river stage, observed flood extent, local drainage capacity, levee condition, or small-channel completeness; those limits remain binding for nationwide monitoring.

## Copernicus DEM Admin 1 static aggregation (verified)

The Copernicus DEM GLO-30 Public 2021 release provides public Cloud-Optimized GeoTIFF assets in one-degree EPSG:4326 tiles. A direct remote-COG diagnostic confirmed a 3,600 by 3,600 source tile and its orthometric-height data description. The extractor then identified tiles from the real Admin 1 envelope, streamed only 100 by 100 average-resampled overviews, and assigned overview-cell centres to true Admin 1 polygons. It does not retain raster assets in the web project.

The resulting output is `/home/ubuntu/deltawatch-model-outputs/myanmar_admin1_copernicus_dem_static.json`. It provides all 18 regions with between 6,089 and 83,224 static overview samples and records the full tile audit. It attempted 127 intersecting-envelope public COGs, read 118 successfully, and retained nine unavailable COG URLs explicitly rather than substituting values. Every region still received terrain samples; mean elevation ranged from 16.122 m to 1,039.866 m and the regional P90–P10 relief range was 43.385 m to 2,387.847 m.

The terrain fields are static **mean**, **median**, **P10**, **P90**, **minimum**, and **maximum** elevation, plus P90–P10 regional relief. This is a coarse overview aggregation, not a full-resolution terrain, hydraulic, drainage, or bare-earth survey. Copernicus describes GLO-30 as a digital surface model, so buildings and vegetation can affect values. The output does not provide current flood extent, rainfall, river stage, probability, forecast, risk score, or alert.

Source URLs:

- https://registry.opendata.aws/copernicus-dem/
- https://copernicus-dem-30m-stac.s3.eu-central-1.amazonaws.com/

## ESA WorldCover Admin 1 static aggregation (verified)

The official ESA WorldCover repository documents the 2021 v200 map bucket and its country/bounding-box downloader. The official tile-grid GeoJSON was retrieved and used to select only 19 true-grid tiles intersecting Myanmar. Each public v200 map COG was streamed as a 120 by 120 **categorical mode-resampled** overview and its sample-cell centres were assigned to true Admin 1 polygons. The source COGs are not retained in the web project.

The resulting output is `/home/ubuntu/deltawatch-model-outputs/myanmar_admin1_worldcover_static.json`. All 19 selected COGs were available, each of the 18 regions received static overview samples, and per-region sample counts ranged from 974 to 13,305. The output retains counts and shares for all documented WorldCover classes, as well as the dominant class and its share. Dominant class share spans 0.426617 to 0.979006 across regions; a dominant static class is not a land-use update, impact assessment, or flood label.

WorldCover 2021 v200 is a 10 m static land-cover source under CC BY 4.0. The extracted regional context does not provide rainfall, river stage, current flood extent, flood probability, forecast, risk score, or alert. No model was fitted in any static-source extraction stage.

Source URLs:

- https://github.com/ESA-WorldCover/esa-worldcover-datasets
- https://esa-worldcover.org/en/data-access
- https://doi.org/10.5281/zenodo.7254221

## Global Flood Database metadata for nationwide validation planning

The public Cloud to Street Global Flood Database repository documents its quality-control metadata file at `data/gfd_qcdatabase_2019_08_01.csv`, the Dartmouth Flood Observatory polygons used in its analyses, and a Google Cloud Storage bucket containing the flood GeoTIFF archives. The quality-control file was downloaded and used only to build a metadata catalog; archive downloads, raster labels, model scores, probabilities, and alerts were deliberately excluded from this stage.

The resulting reproducible Myanmar catalog selected records where the source country was `Myanmar` or `Burma`, or the GLIDE identifier ended with `-MMR`. It produced 12 historical records: 2041, 2276, 2859, 3068, 3125, 3169, 3302, 3662, 4283, 4365, 4632, and 4666. This is a source-metadata selection, not a complete census of Myanmar floods and not a validation result. Cross-border geometries and source coverage must be assessed before any later regional training or temporal evaluation.

Sources:

- https://github.com/cloudtostreet/MODIS_GlobalFloodDatabase
- https://www.hydroshare.org/resource/6461528501c14f7c9d6b10d20dd4f657/
