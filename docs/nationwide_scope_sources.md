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
