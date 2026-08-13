// Maubin Sentinel-1 SAR flood event export — HYDRAFloods-inspired pipeline.
//
// Workflow:
//   Sentinel-1 GRD (VH+VV) → speckle reduction → pre/during composites
//   → multi-method water detection → permanent-water mask → morphology
//   → temporary flood mask → vector export
//
// Run in https://code.earthengine.google.com, download GeoJSON from Drive, then:
//   python -m scripts.import_flood_sar_events data/raw/maubin-sar-flood-events.geojson
//
// Detection methods (combined with OR, then masked):
//   A — VH change ratio: VH_during / VH_pre < ratio threshold
//   B — VH absolute threshold: VH_during < db threshold
//   C — VH delta: (VH_pre - VH_during) > delta threshold

var maubinSearchArea = ee.Geometry.Rectangle(
  [95.35, 16.35, 96.05, 17.05],
  null,
  false
);

// --- Detection parameters ---
var VH_RATIO_THRESHOLD = 0.5;       // Method A: during/pre ratio (linear, ~-3 dB)
var VH_ABS_THRESHOLD_DB = -17.0;      // Method B: absolute VH backscatter
var VH_DELTA_THRESHOLD_DB = 3.0;      // Method C: pre - during (dB)
var SPECKLE_RADIUS = 1;               // focal median radius (pixels)
var MORPH_RADIUS = 1;                 // connectivity cleanup
var BASELINE_DAYS_BEFORE = 21;
var BASELINE_END_OFFSET_DAYS = 1;
var EVENT_BUFFER_DAYS = 3;
var VECTOR_SCALE = 30;
var MIN_POLYGON_PIXELS = 20;
var HAND_MAX_M = 15;                  // terrain constraint: exclude high HAND

// JRC Global Surface Water — permanent water (occurrence >= 50%)
var jrcPermWater = ee
  .Image('JRC/GSW1_4/GlobalSurfaceWater')
  .select('occurrence')
  .gte(50)
  .clip(maubinSearchArea);

// HAND terrain constraint (optional — masks cells unlikely to flood)
var hand = ee
  .Image('MERIT/Hydro/v1_0_1')
  .select('hnd')
  .clip(maubinSearchArea);
var lowHandMask = hand.lte(HAND_MAX_M);

var gfdEvents = ee.ImageCollection('GLOBAL_FLOOD_DB/MODIS_EVENTS/V1')
  .filterBounds(maubinSearchArea)
  .filterDate('2015-01-01', '2026-12-31')
  .sort('system:time_start');

print('Valid SAR-era GFD events', gfdEvents.size());

var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(maubinSearchArea)
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
  .filter(ee.Filter.eq('instrumentMode', 'IW'))
  .select(['VH', 'VV']);

print('Sentinel-1 images', s1.size());

function speckleReducedVH(start, end) {
  var collection = s1.filterDate(start, end);
  return collection
    .map(function (img) {
      return img.select('VH').focal_median(SPECKLE_RADIUS, 'square', 'pixels');
    })
    .median()
    .rename('VH');
}

function sarFloodForEvent(element) {
  var image = ee.Image(element);
  var start = ee.Date(image.get('system:time_start'));
  var end = ee.Date(
    ee.Algorithms.If(
      image.propertyNames().contains('system:time_end'),
      image.get('system:time_end'),
      image.get('system:time_start')
    )
  );
  var gfdEventId = ee.Number(image.get('id')).format('%d');
  var baseline = speckleReducedVH(
    start.advance(-BASELINE_DAYS_BEFORE, 'day'),
    start.advance(-BASELINE_END_OFFSET_DAYS, 'day')
  );
  var during = speckleReducedVH(start, end.advance(EVENT_BUFFER_DAYS, 'day'));
  var hasSAR = baseline.bandNames().size().gt(0).and(
    during.bandNames().size().gt(0)
  );

  return ee.FeatureCollection(
    ee.Algorithms.If(
      hasSAR,
      (function () {
        // Method A: VH ratio (linear scale)
        var ratio = during.divide(baseline.max(1e-6));
        var methodA = ratio.lt(VH_RATIO_THRESHOLD);

        // Method B: absolute VH threshold
        var methodB = during.lt(VH_ABS_THRESHOLD_DB);

        // Method C: VH decrease (change detection in dB space)
        var delta = baseline.subtract(during);
        var methodC = delta.gt(VH_DELTA_THRESHOLD_DB);

        // Combine methods — any signal counts as candidate water
        var detectedWater = methodA.or(methodB).or(methodC);

        // Permanent water mask: detected - permanent = temporary flood
        var permanentWater = jrcPermWater.selfMask();
        var temporaryFlood = detectedWater
          .and(permanentWater.not())
          .and(lowHandMask)
          .focal_max(MORPH_RADIUS)
          .focal_min(MORPH_RADIUS)
          .selfMask()
          .clip(maubinSearchArea);

        return temporaryFlood
          .reduceToVectors({
            geometry: maubinSearchArea,
            scale: VECTOR_SCALE,
            geometryType: 'polygon',
            eightConnected: false,
            labelProperty: 'flooded',
            reducer: ee.Reducer.countEvery(),
            maxPixels: 1e9
          })
          .filter(ee.Filter.gt('count', MIN_POLYGON_PIXELS))
          .map(function (feature) {
            return feature.set({
              event_id: ee.String('sar-').cat(gfdEventId),
              reference_gfd_event_id: gfdEventId,
              event_start_date: start.format('YYYY-MM-dd'),
              event_end_date: end.format('YYYY-MM-dd'),
              event_year: start.get('year'),
              source_dataset: 'COPERNICUS/S1_GRD',
              label_method: 'multi_method_sar_hydrafloods_inspired',
              sar_polarization: 'VH',
              sar_detection_methods: 'vh_ratio,vh_threshold,vh_delta',
              sar_vh_ratio_threshold: VH_RATIO_THRESHOLD,
              sar_vh_abs_threshold_db: VH_ABS_THRESHOLD_DB,
              sar_vh_delta_threshold_db: VH_DELTA_THRESHOLD_DB,
              baseline_window_days: BASELINE_DAYS_BEFORE,
              speckle_filter: 'focal_median',
              speckle_radius_px: SPECKLE_RADIUS,
              permanent_water_mask: 'JRC/GSW1_4 occurrence>=50',
              hand_constraint_max_m: HAND_MAX_M,
              processing_scale_m: VECTOR_SCALE,
              permanent_water_excluded: true,
              dfo_country: image.get('dfo_country'),
              dfo_main_cause: image.get('dfo_main_cause')
            });
          });
      })(),
      ee.FeatureCollection([])
    )
  );
}

var sarEventVectors = ee.FeatureCollection(
  gfdEvents.toList(gfdEvents.size()).map(sarFloodForEvent)
).flatten();

print('Distinct SAR event IDs', sarEventVectors.distinct('event_id').size());
print('Raw polygon fragments (dissolved on import)', sarEventVectors.size());

Map.setOptions('SATELLITE');
Map.centerObject(maubinSearchArea, 10);
Map.addLayer(maubinSearchArea, {color: 'yellow'}, 'Maubin area');
Map.addLayer(jrcPermWater.selfMask(), {palette: ['0066cc']}, 'JRC permanent water');
Map.addLayer(
  sarEventVectors.style({color: '00ffff', fillColor: '00ffff55', width: 1}),
  {},
  'Sentinel-1 temporary flood (SAR)'
);

Export.table.toDrive({
  collection: sarEventVectors,
  description: 'maubin_sar_flood_events',
  fileNamePrefix: 'maubin-sar-flood-events',
  fileFormat: 'GeoJSON'
});
