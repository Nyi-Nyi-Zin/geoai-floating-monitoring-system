import { useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { BarChart3, CloudRain, Database, Eye, Info, Layers3, LoaderCircle, MapPinned, ShieldAlert, X } from "lucide-react";
import { trpc } from "@/lib/trpc";
import "leaflet/dist/leaflet.css";

type LayerKey = "floodRisk" | "gridCells" | "historicalFlood" | "rivers" | "canals" | "boundary" | "labels";
type SpatialFeature = Feature<Geometry, Record<string, unknown>>;
type SpatialCollection = FeatureCollection<Geometry, Record<string, unknown>>;
type FloodEvent = { id: string; name: string; start_date: string; end_date: string; area_km2: number; geometry: Geometry };
type Hindcast = { event: FloodEvent; model: { version: string; metrics?: { precision?: number; recall?: number; f1?: number } }; predictions: Array<{ cell_id: string; probability: number; predicted_label: boolean }> };

const satelliteTiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const terrainTiles = "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png";
const maubinCenter: [number, number] = [16.7247, 95.6687];
const bandColor: Record<string, string> = { LOWER: "#60a5fa", MODERATE: "#facc15", HIGH: "#fb923c", VERY_HIGH: "#ef4444" };

function FitBounds({ data }: { data: SpatialCollection | null }) {
  const map = useMap();
  useEffect(() => {
    if (!data?.features.length) return;
    const boundary = data.features.find(feature => feature.properties.asset_type === "township_boundary");
    if (!boundary) return;
    if (!("coordinates" in boundary.geometry)) return;
    const coordinates = JSON.stringify(boundary.geometry.coordinates).match(/-?\d+\.\d+/g)?.map(Number) ?? [];
    const latitudes = coordinates.filter((_, index) => index % 2 === 1);
    const longitudes = coordinates.filter((_, index) => index % 2 === 0);
    if (latitudes.length && longitudes.length) map.fitBounds([[Math.min(...latitudes), Math.min(...longitudes)], [Math.max(...latitudes), Math.max(...longitudes)]], { padding: [28, 28] });
  }, [data, map]);
  return null;
}

function RainBars({ points }: { points: Array<{ date: string; precipitationMm: number }> }) {
  const max = Math.max(...points.map(point => point.precipitationMm), 1);
  return <div className="rain-bars" aria-label="Seven day rainfall forecast">{points.map(point => <div className="rain-bar" key={point.date}><span style={{ height: `${Math.max(8, (point.precipitationMm / max) * 86)}%` }} title={`${point.precipitationMm.toFixed(1)} mm`} /><small>{new Date(`${point.date}T00:00:00`).toLocaleDateString("en", { weekday: "short" }).slice(0, 2)}</small></div>)}</div>;
}

function RainSparkline({ points }: { points: Array<{ observed_date: string; precipitation_mm: number }> }) {
  const width = 296; const height = 68;
  const max = Math.max(...points.map(point => point.precipitation_mm), 1);
  const path = points.map((point, index) => `${index ? "L" : "M"}${(index / Math.max(points.length - 1, 1)) * width},${height - (point.precipitation_mm / max) * (height - 8)}`).join(" ");
  return <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Thirty-day ERA5 rainfall history"><path d={path} fill="none" stroke="#6ee7b7" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /><path d={`M0,${height} ${path.replace("M", "L")} L${width},${height} Z`} fill="url(#rainFill)" opacity="0.35" /><defs><linearGradient id="rainFill" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#6ee7b7" /><stop offset="1" stopColor="#6ee7b7" stopOpacity="0" /></linearGradient></defs></svg>;
}

export default function Home() {
  const [basemap, setBasemap] = useState<"satellite" | "terrain">("satellite");
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>({ floodRisk: true, gridCells: false, historicalFlood: false, rivers: true, canals: true, boundary: true, labels: false });
  const [spatial, setSpatial] = useState<SpatialCollection | null>(null);
  const [terrain, setTerrain] = useState<SpatialCollection | null>(null);
  const [events, setEvents] = useState<FloodEvent[]>([]);
  const [rainHistory, setRainHistory] = useState<Array<{ observed_date: string; precipitation_mm: number }>>([]);
  const [selectedEvent, setSelectedEvent] = useState<string>("");
  const [hindcast, setHindcast] = useState<Hindcast | null>(null);
  const [spatialOnline, setSpatialOnline] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const weather = trpc.monitoring.weather.useQuery(undefined, { retry: 1 });
  const status = trpc.monitoring.status.useQuery();

  useEffect(() => {
    const load = async () => {
      try {
        const [health, waterways, terrainData, eventData, history] = await Promise.all([
          fetch("/api/spatial/health").then(response => response.json()),
          fetch("/api/spatial/waterways").then(response => response.json()),
          fetch("/api/spatial/terrain").then(response => response.json()),
          fetch("/api/spatial/flood-events").then(response => response.json()),
          fetch("/api/spatial/rainfall-history").then(response => response.json()),
        ]);
        setSpatialOnline(Boolean(health.ok)); setSpatial(waterways); setTerrain(terrainData); setEvents(eventData.events ?? []); setRainHistory(history.history ?? []);
        if (eventData.events?.[0]) setSelectedEvent(String(eventData.events[0].id));
      } finally { setLoading(false); }
    };
    void load();
  }, []);

  useEffect(() => {
    if (!selectedEvent) return;
    fetch(`/api/spatial/hindcast/${encodeURIComponent(selectedEvent)}`).then(response => response.ok ? response.json() : null).then(data => setHindcast(data)).catch(() => setHindcast(null));
  }, [selectedEvent]);

  const predictionByCell = useMemo(() => new Map((hindcast?.predictions ?? []).map(row => [row.cell_id, row])), [hindcast]);
  const boundaryLayer = useMemo<SpatialCollection | null>(() => spatial ? { type: "FeatureCollection", features: spatial.features.filter((feature: SpatialFeature) => feature.properties.asset_type === "township_boundary") } : null, [spatial]);
  const riverLayer = useMemo<SpatialCollection | null>(() => spatial ? { type: "FeatureCollection", features: spatial.features.filter((feature: SpatialFeature) => feature.properties.asset_type === "river_segment") } : null, [spatial]);
  const canalLayer = useMemo<SpatialCollection | null>(() => spatial ? { type: "FeatureCollection", features: spatial.features.filter((feature: SpatialFeature) => feature.properties.asset_type === "canal_segment") } : null, [spatial]);
  const riskStyle = (feature?: SpatialFeature) => {
    const properties = feature?.properties ?? {}; const id = String(properties.id ?? feature?.id ?? ""); const prediction = predictionByCell.get(id);
    if (prediction) return { color: "#0f172a", weight: 0.15, fillColor: prediction.probability > 0.53 ? "#f43f5e" : "#60a5fa", fillOpacity: 0.18 + prediction.probability * 0.58 };
    const band = String(properties.screening_band ?? "LOWER"); return { color: "#0f172a", weight: layers.gridCells ? 0.3 : 0, fillColor: bandColor[band] ?? bandColor.LOWER, fillOpacity: layers.floodRisk ? 0.38 : 0 };
  };
  const overlayTerrain = (layers.floodRisk || layers.gridCells) ? terrain : null;
  const historicalFeatures: SpatialCollection | null = layers.historicalFlood ? { type: "FeatureCollection", features: events.map(event => ({ type: "Feature", properties: { id: event.id, name: event.name }, geometry: event.geometry })) } : null;
  const forecast = weather.data?.forecast ?? [];
  const precision = hindcast?.model.metrics?.precision ?? 0.1547;
  const recall = hindcast?.model.metrics?.recall ?? 0.4208;

  return <div className="dashboard-shell">
    <main className="map-stage">
      <MapContainer center={maubinCenter} zoom={10} minZoom={7} maxZoom={18} className="maubin-map" preferCanvas zoomControl={false}>
        <TileLayer url={basemap === "satellite" ? satelliteTiles : terrainTiles} attribution={basemap === "satellite" ? "Tiles © Esri" : "Map data © OpenTopoMap"} />
        <FitBounds data={spatial} />
        {overlayTerrain && <GeoJSON data={overlayTerrain} style={riskStyle} />}
        {layers.boundary && boundaryLayer && <GeoJSON data={boundaryLayer} style={{ color: "#e2e8f0", weight: 1.6, dashArray: "6 5", fillOpacity: 0 }} />}
        {layers.labels && boundaryLayer && <GeoJSON data={boundaryLayer} style={{ color: "transparent", weight: 0, fillOpacity: 0 }} onEachFeature={(_, layer) => { layer.bindTooltip("Maubin Township", { permanent: true, direction: "center", className: "map-label" }); }} />}
        {layers.rivers && riverLayer && <GeoJSON data={riverLayer} style={{ color: "#38bdf8", weight: 2.2, opacity: 0.92 }} />}
        {layers.canals && canalLayer && <GeoJSON data={canalLayer} style={{ color: "#65a30d", weight: 1.4, opacity: 0.88 }} />}
        {historicalFeatures && <GeoJSON data={historicalFeatures} style={{ color: "#a78bfa", weight: 1.4, fillColor: "#7c3aed", fillOpacity: 0.28 }} />}
      </MapContainer>
      <div className="map-gradient" />
      <header className="topbar">
        <div className="brand"><span className="brand-mark"><MapPinned size={17} /></span><div><strong>DeltaWatch</strong><small>Maubin Township · GeoAI flood intelligence</small></div></div>
        <div className="top-actions"><div className="basemap-switch" aria-label="Basemap selector"><button type="button" className={basemap === "satellite" ? "active" : ""} aria-pressed={basemap === "satellite"} onClick={() => setBasemap("satellite")}>Satellite</button><button type="button" className={basemap === "terrain" ? "active" : ""} aria-pressed={basemap === "terrain"} onClick={() => setBasemap("terrain")}>Terrain</button></div><div className="status-pill"><span className={spatialOnline ? "status-dot online" : "status-dot"} />{spatialOnline ? "Spatial DB online" : "Spatial API connecting"}</div><button className="ghost-button" onClick={() => setAboutOpen(true)}><Info size={16} /> Methodology</button></div>
      </header>

      <section className="side-panel controls-panel"><div className="panel-heading"><Layers3 size={16} /><span>Layer control</span></div>{([ ["floodRisk", "Flood Risk"], ["gridCells", "Grid Cells"], ["historicalFlood", "Historical Flood"], ["rivers", "Rivers"], ["canals", "Canals"], ["boundary", "Township Boundary"], ["labels", "Labels"] ] as Array<[LayerKey, string]>).map(([key, label]) => <label className="layer-row" key={key}><span>{label}</span><button role="switch" aria-checked={layers[key]} className={`toggle ${layers[key] ? "enabled" : ""}`} onClick={() => setLayers(current => ({ ...current, [key]: !current[key] }))}><i /></button></label>)}</section>

      <section className="side-panel rainfall-panel"><div className="panel-heading"><CloudRain size={16} /><span>Rainfall watch</span></div><div className="rain-title"><strong>{forecast.reduce((sum, point) => sum + point.precipitationMm, 0).toFixed(1)} mm</strong><span>next 7 days · Open-Meteo</span></div>{weather.isLoading ? <div className="loading-inline"><LoaderCircle size={16} />Loading forecast</div> : <RainBars points={forecast} />}<div className="history-header"><span>30-day ERA5 rainfall history</span><small>mm/day</small></div>{rainHistory.length ? <RainSparkline points={rainHistory} /> : <p className="empty-note">Historical rainfall will populate after the first nightly ERA5 refresh.</p>}</section>

      <section className="side-panel hindcast-panel"><div className="panel-heading"><BarChart3 size={16} /><span>Experimental event hindcast</span></div><label className="select-label">Historical GFD v3 event<select value={selectedEvent} onChange={event => setSelectedEvent(event.target.value)}>{events.map(event => <option key={event.id} value={event.id}>{event.start_date} · {event.name}</option>)}</select></label><div className="model-card"><div><span>v6 logistic model</span><strong>{hindcast?.event.area_km2?.toFixed(1) ?? "—"} km² observed extent</strong></div><div className="metric-pair"><span>Precision <b>{(precision * 100).toFixed(1)}%</b></span><span>Recall <b>{(recall * 100).toFixed(1)}%</b></span></div></div><div className="disclaimer"><ShieldAlert size={15} /><p>Experimental hindcast only. Precision and recall are evaluated on historical GFD v3 event cells; do not use this output as a public warning or life-safety decision.</p></div></section>

      <section className="status-bar"><div><Database size={15} /><span>Spatial DB</span><strong>{spatialOnline ? "connected" : "checking"}</strong></div><div><ShieldAlert size={15} /><span>Open alerts</span><strong>{status.data?.openAlerts ?? 0}</strong></div><div><Eye size={15} /><span>Risk basis</span><strong>{status.data?.riskBasis ?? "terrain_screening"}</strong></div></section>
      {loading && <div className="map-loader"><LoaderCircle size={24} /><span>Loading 5,549 terrain screening cells</span></div>}
    </main>
    {aboutOpen && <div className="modal-backdrop" role="presentation"><section className="methodology-modal" role="dialog" aria-modal="true" aria-labelledby="methodology-title"><button className="close-button" onClick={() => setAboutOpen(false)} aria-label="Close methodology"><X size={18} /></button><span className="eyebrow">Methods & limits</span><h1 id="methodology-title">Maubin flood intelligence is a screening and hindcast system.</h1><p>Terrain screening combines relative elevation, mapped waterways, and terrain flatness. The event panel shows an experimental v6 logistic hindcast model calibrated against historical flood observations, not a real-time hydrologic forecast.</p><div className="source-grid"><div><strong>Copernicus DEM</strong><span>Relative terrain and low-elevation screening</span></div><div><strong>ESA WorldCover</strong><span>Land-cover context for terrain cells</span></div><div><strong>GFD v3</strong><span>Pixel-level historical flood-event polygons</span></div><div><strong>ERA5</strong><span>Historical rainfall context and nightly upserts</span></div></div><p className="limit-note">Limitations: river stage, tide, upstream inflow, drainage capacity, levees, and verified field observations are not represented. Treat all model outputs as experimental analytical context.</p></section></div>}
  </div>;
}
