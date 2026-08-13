// Export individual Global Flood Database events intersecting Maubin Township.
// Run this in https://code.earthengine.google.com, then download the completed
// GeoJSON task from Google Drive. This preserves event identity and dates so
// rainfall can be aligned without leaking future events into evaluation.

var maubinSearchArea = ee.Geometry.Rectangle(
  [95.35, 16.35, 96.05, 17.05],
  null,
  false
);

var events = ee.ImageCollection('GLOBAL_FLOOD_DB/MODIS_EVENTS/V1')
  .filterBounds(maubinSearchArea)
  .sort('system:time_start');

print('Candidate GFD events', events.size());
print('Candidate DFO event IDs', events.aggregate_array('id'));

var eventCollections = events.toList(events.size()).map(function (item) {
  var image = ee.Image(item);
  var propertyNames = image.propertyNames();
  var start = ee.Date(image.get('system:time_start'));
  var endMillis = ee.Algorithms.If(
    propertyNames.contains('system:time_end'),
    image.get('system:time_end'),
    image.get('system:time_start')
  );
  var end = ee.Date(endMillis);
  var floodOnly = image.select('flooded').eq(1)
    .and(image.select('jrc_perm_water').neq(1))
    .selfMask()
    .clip(maubinSearchArea)
    .toInt8();

  return floodOnly.reduceToVectors({
    geometry: maubinSearchArea,
    scale: 250,
    geometryType: 'polygon',
    eightConnected: true,
    labelProperty: 'flooded',
    reducer: ee.Reducer.countEvery(),
    maxPixels: 1e10
  }).map(function (feature) {
    return feature.set({
      event_id: ee.Number(image.get('id')).format('%d'),
      event_start_date: start.format('YYYY-MM-dd'),
      event_end_date: end.format('YYYY-MM-dd'),
      event_year: start.get('year'),
      dfo_country: image.get('dfo_country'),
      dfo_main_cause: image.get('dfo_main_cause'),
      dfo_severity: image.get('dfo_severity'),
      dfo_dead: image.get('dfo_dead'),
      dfo_displaced: image.get('dfo_displaced'),
      source_dataset: 'GLOBAL_FLOOD_DB/MODIS_EVENTS/V1',
      permanent_water_excluded: true,
      processing_scale_m: 250
    });
  });
});

var eventVectors = ee.FeatureCollection(eventCollections).flatten();
print('Export polygon count', eventVectors.size());

Map.setOptions('SATELLITE');
Map.centerObject(maubinSearchArea, 10);
Map.addLayer(maubinSearchArea, {color: 'f5ff62'}, 'Maubin export search area');
Map.addLayer(
  eventVectors.style({color: 'ff2c7d', fillColor: 'ff2c7d55', width: 1}),
  {},
  'Individual GFD event polygons'
);

Export.table.toDrive({
  collection: eventVectors,
  description: 'maubin_gfd_individual_events_2000_2018',
  fileNamePrefix: 'maubin-gfd-individual-events-2000-2018',
  fileFormat: 'GeoJSON'
});
