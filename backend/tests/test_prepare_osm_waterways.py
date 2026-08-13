from scripts.prepare_osm_waterways import prepare_waterways


def test_prepare_waterways_clips_and_normalizes():
    source = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[95.59, 16.7], [95.62, 16.7]],
                },
                "properties": {
                    "@id": "way/123",
                    "waterway": "river",
                    "name": "Test River",
                },
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[95.6, 16.7], [95.61, 16.71]],
                },
                "properties": {"highway": "road"},
            },
        ],
    }
    boundary = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [95.6, 16.69],
                            [95.61, 16.69],
                            [95.61, 16.71],
                            [95.6, 16.71],
                            [95.6, 16.69],
                        ],
                    ],
                },
                "properties": {
                    "pcode": "MMR017019",
                    "township": "Maubin",
                },
            }
        ],
    }

    result = prepare_waterways(source, boundary, segment_length_m=500)

    assert result["features"][0]["properties"]["asset_type"] == "township_boundary"
    segments = result["features"][1:]
    assert len(segments) >= 2
    assert all(
        feature["properties"]["asset_type"] == "river_segment"
        for feature in segments
    )
    assert all(
        feature["properties"]["metadata"]["osm_id"] == "way/123"
        for feature in segments
    )
    assert all(
        feature["properties"]["metadata"]["segment_length_m"] <= 500
        for feature in segments
    )
    assert len(
        {feature["properties"]["source_key"] for feature in segments}
    ) == len(segments)
