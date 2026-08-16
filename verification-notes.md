# Preview verification notes

Verified locally on 2026-08-16:

- The dashboard loads on the managed development preview with Leaflet satellite imagery.
- The terrain screening endpoint serves 5,549 color-coded terrain cells and the flood-risk layer renders on the map.
- The map includes waterways, township boundary, layer toggles, a 30-day ERA5 rainfall sparkline, the 7-day Open-Meteo forecast, and 17 selectable GFD v3 events.
- The v6 experimental hindcast panel displays its always-visible precision and recall disclaimer.
- The system status bar displays the exact risk-basis label `terrain_screening`.
- The methodology modal opens and names Copernicus DEM, ESA WorldCover, GFD v3, and ERA5.
- The visible basemap selector switches from Esri satellite imagery to OpenTopoMap terrain tiles; the map attribution changes accordingly.
- The Labels switch renders a permanent `Maubin Township` map label. The mobile breakpoint keeps the rainfall and hindcast panels visible without horizontal overflow.
- Production validation on 2026-08-16 confirmed that `https://deltawatch-jayyutyh.manus.space` completed its cold start and loaded the spatial terrain layer, 7-day Open-Meteo forecast, ERA5 sparkline, 17-event selector, and `terrain_screening` status label.
