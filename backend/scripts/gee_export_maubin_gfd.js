// Run in the Google Earth Engine Code Editor after signing in.
// Source: GLOBAL_FLOOD_DB/MODIS_EVENTS/V1 (CC BY-NC 4.0).
// Output is a sensor-independent historical label candidate, not ground truth.

var maubinSearchArea = ee.Geometry.Rectangle(
  [95.35, 16.45, 95.95, 16.98],
  'EPSG:4326',
  false
);

var collection = ee.ImageCollection('GLOBAL_FLOOD_DB/MODIS_EVENTS/V1')
  .filterBounds(maubinSearchArea)
  .filterDate('2000-01-01', '2019-01-01');

print('Candidate flood event count', collection.size());
print('Candidate Dartmouth event IDs', collection.aggregate_array('id'));
print('Candidate event start dates', collection.aggregate_array('system:time_start'));

// Remove JRC permanent water from every event before counting flood frequency.
var floodOnly = collection.map(function (image) {
  return image.select('flooded').eq(1)
    .and(image.select('jrc_perm_water').neq(1))
    .rename('flood_frequency');
});

var frequency = floodOnly.sum().toInt16().selfMask().clip(maubinSearchArea);
Map.setOptions('SATELLITE');
Map.centerObject(maubinSearchArea, 10);
Map.addLayer(
  frequency,
  {min: 1, max: 5, palette: ['8be6ff', '4298e8', '6d45c7', 'd72f8a']},
  'Observed flood frequency'
);

var vectors = frequency.reduceToVectors({
  geometry: maubinSearchArea,
  scale: 250,
  geometryType: 'polygon',
  eightConnected: true,
  labelProperty: 'event_count',
  // The first (and only) band supplies polygon labels, so use a reducer that
  // does not require an additional value band.
  reducer: ee.Reducer.countEvery(),
  maxPixels: 1e10
}).map(function (feature) {
  return feature.set({
    source_dataset: 'GLOBAL_FLOOD_DB/MODIS_EVENTS/V1',
    permanent_water_excluded: true,
    processing_scale_m: 250,
    training_label_candidate: true
  });
});

Export.table.toDrive({
  collection: vectors,
  description: 'maubin_global_flood_database_history',
  fileNamePrefix: 'maubin-gfd-flood-history-2000-2018',
  fileFormat: 'GeoJSON'
});
