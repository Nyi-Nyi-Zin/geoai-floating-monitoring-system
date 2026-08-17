import { useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { Activity, BarChart3, Camera, CloudRain, Database, Eye, Info, Layers3, LoaderCircle, MapPinned, ShieldAlert, X } from "lucide-react";
import { trpc } from "@/lib/trpc";
import { FieldObservationModal } from "@/components/FieldObservationModal";
import "leaflet/dist/leaflet.css";

type LayerKey = "floodRisk" | "gridCells" | "historicalFlood" | "rivers" | "canals" | "boundary" | "labels";
type SpatialFeature = Feature<Geometry, Record<string, unknown>>;
type SpatialCollection = FeatureCollection<Geometry, Record<string, unknown>>;
type FloodEvent = { id: string; name: string; start_date: string; end_date: string; area_km2: number; geometry: Geometry };
type Hindcast = { event: FloodEvent; model: { version: string; threshold?: number; metrics?: { precision?: number; recall?: number; f1?: number; roc_auc?: number; pr_auc?: number }; predictors?: { tide?: string } }; predictions: Array<{ cell_id: string; probability: number; predicted_label: boolean }> };
type NationalAdminMetadata = { source?: { boundary_valid_on?: string; dataset?: string }; coverage?: { admin1_feature_count?: number; status?: string } };
type NationalEvidenceReadiness = { region_count?: number; regions?: Array<{ admin1_pcode: string; admin1_name: string; evidence_readiness: string }>; static_context?: { status?: string; interpretation?: string }; candidate_gate?: { status?: string; model_status?: string; reason?: string }; interpretation?: string; limits?: string[] };
type NationalCoverageFilter = "all" | "historical" | "limited" | "insufficient";

const satelliteTiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const terrainTiles = "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png";
const maubinCenter: [number, number] = [16.7247, 95.6687];
const myanmarCenter: [number, number] = [21.9162, 95.9560];
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

function CoverageViewport({ nationwide }: { nationwide: boolean }) {
  const map = useMap();
  useEffect(() => { map.setView(nationwide ? myanmarCenter : maubinCenter, nationwide ? 5 : 10, { animate: false }); }, [map, nationwide]);
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

function freshnessLabel(state?: "current" | "late" | "not_yet_available" | "unavailable") {
  if (state === "current") return "Current";
  if (state === "late") return "Needs refresh";
  if (state === "not_yet_available") return "Awaiting first refresh";
  return "Status unavailable";
}

function jobLabel(state?: "healthy" | "late" | "failed" | "not_yet_run" | "not_configured" | "unavailable") {
  if (state === "healthy") return "Healthy";
  if (state === "late") return "Late";
  if (state === "failed") return "Last run failed";
  if (state === "not_yet_run") return "Awaiting first run";
  if (state === "not_configured") return "Not configured";
  return "Unavailable";
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
  const [observationOpen, setObservationOpen] = useState(false);
  const [mobileControlsOpen, setMobileControlsOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [nationwideMode, setNationwideMode] = useState(false);
  const [nationalRegions, setNationalRegions] = useState<SpatialCollection | null>(null);
  const [nationalMetadata, setNationalMetadata] = useState<NationalAdminMetadata | null>(null);
  const [nationalEvidence, setNationalEvidence] = useState<NationalEvidenceReadiness | null>(null);
  const [nationalLoading, setNationalLoading] = useState(false);
  const [nationalCoverageFilter, setNationalCoverageFilter] = useState<NationalCoverageFilter>("all");
  const weather = trpc.monitoring.weather.useQuery(undefined, { retry: 1 });
  const status = trpc.monitoring.status.useQuery();
  const prospective = trpc.monitoring.prospective.useQuery(undefined, { retry: 1 });
  const operational = trpc.monitoring.operationalStatus.useQuery(undefined, { retry: 1, refetchInterval: 300_000 });

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
        const initialEvent = eventData.events?.find((event: FloodEvent) => new Date(event.start_date).getFullYear() >= 2004) ?? eventData.events?.[0];
        if (initialEvent) setSelectedEvent(String(initialEvent.id));
      } finally { setLoading(false); }
    };
    void load();
  }, []);

  useEffect(() => {
    if (!nationwideMode || nationalRegions) return;
    let active = true;
    setNationalLoading(true);
    Promise.all([
      fetch("/api/spatial/national-admin/metadata").then(response => response.ok ? response.json() : null),
      fetch("/api/spatial/national-admin/regions").then(response => response.ok ? response.json() : null),
      fetch("/api/spatial/national-admin/evidence-readiness").then(response => response.ok ? response.json() : null),
    ]).then(([metadata, regions, evidence]) => {
      if (!active) return;
      setNationalMetadata(metadata); setNationalRegions(regions); setNationalEvidence(evidence);
    }).catch(() => { if (active) { setNationalRegions(null); setNationalEvidence(null); } }).finally(() => { if (active) setNationalLoading(false); });
    return () => { active = false; };
  }, [nationalRegions, nationwideMode]);

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
    if (prediction) return { color: "#0f172a", weight: 0.15, fillColor: prediction.probability >= (hindcast?.model.threshold ?? 0.53) ? "#f43f5e" : "#60a5fa", fillOpacity: 0.18 + prediction.probability * 0.58 };
    const band = String(properties.screening_band ?? "LOWER"); return { color: "#0f172a", weight: layers.gridCells ? 0.3 : 0, fillColor: bandColor[band] ?? bandColor.LOWER, fillOpacity: layers.floodRisk ? 0.38 : 0 };
  };
  const overlayTerrain = (layers.floodRisk || layers.gridCells) ? terrain : null;
  const historicalFeatures: SpatialCollection | null = layers.historicalFlood ? { type: "FeatureCollection", features: events.map(event => ({ type: "Feature", properties: { id: event.id, name: event.name }, geometry: event.geometry })) } : null;
  const forecast = weather.data?.forecast ?? [];
  const precision = hindcast?.model.metrics?.precision ?? 0.1574;
  const recall = hindcast?.model.metrics?.recall ?? 0.2346;
  const alertReadiness = status.data?.alertReadiness;
  const prospectiveState = prospective.data;
  const prospectiveIssue = prospectiveState?.latestIssueTime ? new Date(prospectiveState.latestIssueTime).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "Awaiting first refresh";
  const rainfallHealth = operational.data?.rainfallHistory;
  const rainfallJob = operational.data?.jobs.find(job => job.key === "nightly-rainfall-refresh");
  const prospectiveJob = operational.data?.jobs.find(job => job.key === "six-hour-prospective-monitoring-refresh");
  const overallRefreshState = prospectiveJob?.state === "failed" || rainfallJob?.state === "failed" ? "Attention needed" : prospectiveState?.freshness === "late" || rainfallHealth?.state === "late" ? "Refresh late" : "Monitoring";
  const historicalOnlyRegions = nationalEvidence?.regions?.filter(region => region.evidence_readiness === "historical_source_coverage_only_not_validated_for_prediction").length ?? 0;
  const filteredNationalRegions = useMemo<SpatialCollection | null>(() => {
    if (!nationalRegions || nationalCoverageFilter === "all") return nationalRegions;
    const statusFor = (pcode: unknown) => nationalEvidence?.regions?.find(region => region.admin1_pcode === pcode)?.evidence_readiness;
    const requiredStatus = nationalCoverageFilter === "historical" ? "historical_source_coverage_only_not_validated_for_prediction" : nationalCoverageFilter === "limited" ? "limited_observed_flood_examples" : "insufficient_historical_source_coverage";
    return { type: "FeatureCollection", features: nationalRegions.features.filter(feature => statusFor(feature.properties?.adm1_pcode) === requiredStatus) };
  }, [nationalCoverageFilter, nationalEvidence?.regions, nationalRegions]);

  return <div className="dashboard-shell">
    <main className="map-stage">
      <MapContainer center={maubinCenter} zoom={10} minZoom={5} maxZoom={18} className="maubin-map" preferCanvas zoomControl={false}>
        <TileLayer url={basemap === "satellite" ? satelliteTiles : terrainTiles} attribution={basemap === "satellite" ? "Tiles © Esri" : "Map data © OpenTopoMap"} />
        <CoverageViewport nationwide={nationwideMode} />
        {!nationwideMode && <FitBounds data={spatial} />}
        {!nationwideMode && overlayTerrain && <GeoJSON data={overlayTerrain} style={riskStyle} />}
        {!nationwideMode && layers.boundary && boundaryLayer && <GeoJSON data={boundaryLayer} style={{ color: "#e2e8f0", weight: 1.6, dashArray: "6 5", fillOpacity: 0 }} />}
        {!nationwideMode && layers.labels && boundaryLayer && <GeoJSON data={boundaryLayer} style={{ color: "transparent", weight: 0, fillOpacity: 0 }} onEachFeature={(_, layer) => { layer.bindTooltip("Maubin Township", { permanent: true, direction: "center", className: "map-label" }); }} />}
        {!nationwideMode && layers.rivers && riverLayer && <GeoJSON data={riverLayer} style={{ color: "#38bdf8", weight: 2.2, opacity: 0.92 }} />}
        {!nationwideMode && layers.canals && canalLayer && <GeoJSON data={canalLayer} style={{ color: "#65a30d", weight: 1.4, opacity: 0.88 }} />}
        {!nationwideMode && historicalFeatures && <GeoJSON data={historicalFeatures} style={{ color: "#a78bfa", weight: 1.4, fillColor: "#7c3aed", fillOpacity: 0.28 }} />}
        {nationwideMode && filteredNationalRegions && <GeoJSON data={filteredNationalRegions} style={{ color: "#86efac", weight: 0.8, fillColor: "#334155", fillOpacity: 0.22 }} onEachFeature={(feature, layer) => { const name = String(feature.properties?.adm1_name ?? "Myanmar region"); const region = nationalEvidence?.regions?.find(item => item.admin1_pcode === feature.properties?.adm1_pcode); const evidence = region?.evidence_readiness === "historical_source_coverage_only_not_validated_for_prediction" ? "historical source coverage only" : region?.evidence_readiness === "limited_observed_flood_examples" ? "limited historical examples" : "historical source coverage insufficient"; layer.bindTooltip(`${name} · ${evidence} · not a forecast`, { sticky: true, className: "map-label" }); }} />}
      </MapContainer>
      <div className="map-gradient" />
      <header className="topbar">
        <div className="brand"><span className="brand-mark"><MapPinned size={17} /></span><div><strong>DeltaWatch</strong><small>{nationwideMode ? "Myanmar coverage index · monitoring only" : "Maubin Township · GeoAI flood intelligence"}</small></div></div>
        <div className="top-actions"><div className="basemap-switch" aria-label="Basemap selector"><button type="button" className={basemap === "satellite" ? "active" : ""} aria-pressed={basemap === "satellite"} onClick={() => setBasemap("satellite")}>Satellite</button><button type="button" className={basemap === "terrain" ? "active" : ""} aria-pressed={basemap === "terrain"} onClick={() => setBasemap("terrain")}>Terrain</button></div><button className={`nationwide-button ${nationwideMode ? "active" : ""}`} type="button" aria-pressed={nationwideMode} onClick={() => setNationwideMode(current => !current)}><MapPinned size={15} /> Myanmar coverage</button><button className="mobile-layers-button" type="button" aria-label="Open map layers" aria-expanded={mobileControlsOpen} onClick={() => setMobileControlsOpen(true)}><Layers3 size={16} /></button><div className="status-pill"><span className={spatialOnline ? "status-dot online" : "status-dot"} />{spatialOnline ? "Spatial DB online" : "Spatial API connecting"}</div><button className="evidence-button" type="button" onClick={() => setObservationOpen(true)}><Camera size={15} /> Evidence</button><button className="ghost-button" onClick={() => setAboutOpen(true)}><Info size={16} /> Methodology</button></div>
      </header>

      {nationwideMode && <section className="national-coverage-panel" aria-live="polite"><span className="eyebrow">Nationwide coverage index</span><strong>{nationalLoading ? "Loading Admin 1 boundaries" : `${nationalMetadata?.coverage?.admin1_feature_count ?? 0} Admin 1 regions indexed`}</strong><p>Source geometry is available. Flood prediction, probability, and regional accuracy are not yet assessed.</p><label className="national-filter-label">Region source coverage<select value={nationalCoverageFilter} onChange={event => setNationalCoverageFilter(event.target.value as NationalCoverageFilter)}><option value="all">All Admin 1 regions</option><option value="historical">Historical source coverage only</option><option value="limited">Limited historical examples</option><option value="insufficient">Insufficient historical coverage</option></select></label><small>{filteredNationalRegions ? `${filteredNationalRegions.features.length} region${filteredNationalRegions.features.length === 1 ? "" : "s"} displayed; source coverage is not a risk category.` : "Loading regional source coverage."}</small><div className="national-evidence-readiness"><span>Historical source evidence</span><strong>{nationalEvidence ? `${historicalOnlyRegions} regions with historical coverage only` : "Loading historical coverage summary"}</strong><small>{nationalEvidence?.interpretation ?? "Observed-history summary only; not a forecast."}</small></div><div className="national-evidence-readiness"><span>Static context & candidate gate</span><strong>{nationalEvidence?.candidate_gate?.status === "no_fit_authorized" ? "No nationwide candidate fitted" : nationalLoading ? "Loading candidate gate" : "Candidate gate unavailable"}</strong><small>{nationalEvidence?.candidate_gate?.reason ?? nationalEvidence?.static_context?.interpretation ?? "Static source context is not a prediction result."}</small></div><small>{nationalMetadata?.source?.dataset ?? "Boundary source unavailable"}{nationalMetadata?.source?.boundary_valid_on ? ` · valid from ${nationalMetadata.source.boundary_valid_on}` : ""}</small></section>}

      <section className={`side-panel controls-panel ${mobileControlsOpen ? "mobile-controls-open" : ""}`} aria-hidden={!mobileControlsOpen && undefined}><div className="panel-heading"><Layers3 size={16} /><span>Layer control</span><button className="mobile-control-close" type="button" aria-label="Close map layers" onClick={() => setMobileControlsOpen(false)}><X size={16} /></button></div>{([ ["floodRisk", "Flood Risk"], ["gridCells", "Grid Cells"], ["historicalFlood", "Historical Flood"], ["rivers", "Rivers"], ["canals", "Canals"], ["boundary", "Township Boundary"], ["labels", "Labels"] ] as Array<[LayerKey, string]>).map(([key, label]) => <label className="layer-row" key={key}><span>{label}</span><button role="switch" aria-checked={layers[key]} className={`toggle ${layers[key] ? "enabled" : ""}`} onClick={() => setLayers(current => ({ ...current, [key]: !current[key] }))}><i /></button></label>)}</section>

      <section className="side-panel rainfall-panel"><div className="panel-heading"><CloudRain size={16} /><span>Rainfall watch</span></div><div className="rain-title"><strong>{forecast.reduce((sum, point) => sum + point.precipitationMm, 0).toFixed(1)} mm</strong><span>next 7 days · Open-Meteo</span></div>{weather.isLoading ? <div className="loading-inline"><LoaderCircle size={16} />Loading forecast</div> : <RainBars points={forecast} />}<div className="history-header"><span>30-day ERA5 rainfall history</span><small>mm/day</small></div>{rainHistory.length ? <RainSparkline points={rainHistory} /> : <p className="empty-note">Historical rainfall will populate after the first nightly ERA5 refresh.</p>}<div className={`source-freshness ${rainfallHealth?.state ?? "unavailable"}`} role="status"><div><span>{rainfallHealth?.latestObservedDate ? `ERA5 through ${rainfallHealth.latestObservedDate}` : "ERA5 archive refresh"} · {jobLabel(rainfallJob?.state)}</span><strong>{freshnessLabel(rainfallHealth?.state)}</strong></div></div></section>

      <section className="side-panel hindcast-panel"><div className="panel-heading"><BarChart3 size={16} /><span>Experimental event hindcast</span></div><label className="select-label">Historical GFD event<select value={selectedEvent} onChange={event => setSelectedEvent(event.target.value)}>{events.map(event => <option key={event.id} value={event.id}>{event.start_date} · {event.name}</option>)}</select></label><div className="model-card"><div><span>{hindcast?.model.version ? "HGB v7 · 2018 holdout" : "v7 hydrologic model"}</span><strong>{hindcast?.event.area_km2?.toFixed(1) ?? "—"} km² observed extent</strong></div><div className="metric-pair"><span>Precision <b>{(precision * 100).toFixed(1)}%</b></span><span>Recall <b>{(recall * 100).toFixed(1)}%</b></span></div></div><div className="alert-readiness" aria-label="Alert and prospective monitoring readiness"><div><span>Alert workflow</span><strong>{alertReadiness?.label ?? "Monitoring only"}</strong></div><p>No public alert. Six-hour forecast inputs are logged for prospective validation only.</p><small>{prospectiveState?.label ?? "Prospective input monitoring"} · latest: {prospectiveIssue}{prospectiveState?.targetDate ? ` · target: ${prospectiveState.targetDate}` : ""}</small></div><div className="disclaimer"><ShieldAlert size={15} /><p>Historical hindcast only — 2018 holdout precision {(precision * 100).toFixed(1)}%, recall {(recall * 100).toFixed(1)}%. Not a public warning or life-safety decision.</p></div></section>

      <section className="status-bar"><div><Database size={15} /><span>Spatial DB</span><strong>{spatialOnline ? "connected" : "checking"}</strong></div><div><Activity size={15} /><span>Data refresh</span><strong>{overallRefreshState}</strong></div><div><Activity size={15} /><span>Prospective job</span><strong>{freshnessLabel(prospectiveState?.freshness)} · {jobLabel(prospectiveJob?.state)}</strong></div><div><ShieldAlert size={15} /><span>Open alerts</span><strong>{status.data?.openAlerts ?? 0}</strong></div><div><ShieldAlert size={15} /><span>Alert mode</span><strong>{alertReadiness?.label ?? "Monitoring only"}</strong></div><div><Eye size={15} /><span>Risk basis</span><strong>{status.data?.riskBasis ?? "terrain_screening"}</strong></div></section>
      {loading && <div className="map-loader"><LoaderCircle size={24} /><span>Loading 5,549 terrain screening cells</span></div>}
    </main>
    <FieldObservationModal open={observationOpen} onClose={() => setObservationOpen(false)} />
    {aboutOpen && <div className="modal-backdrop" role="presentation"><section className="methodology-modal" role="dialog" aria-modal="true" aria-labelledby="methodology-title"><button className="close-button" onClick={() => setAboutOpen(false)} aria-label="Close methodology"><X size={18} /></button><span className="eyebrow">Methods & limits</span><h1 id="methodology-title">Maubin flood intelligence is a screening and hindcast system.</h1><p>Terrain screening combines relative elevation, mapped waterways, and terrain flatness. The event panel shows an experimental v7 hydrologic hindcast, evaluated against native GFD flood pixels after permanent water is excluded. It is not a real-time hydrologic forecast.</p><div className="source-grid"><div><strong>Copernicus DEM</strong><span>Relative terrain and low-elevation screening</span></div><div><strong>ESA WorldCover</strong><span>Land-cover context for terrain cells</span></div><div><strong>GFD event maps</strong><span>Native flood and permanent-water pixels for historical labels</span></div><div><strong>ERA5</strong><span>Historical rainfall lags and nightly rainfall upserts</span></div><div><strong>GloFAS</strong><span>Modelled river-discharge proxy for upstream inflow</span></div><div><strong>OpenStreetMap</strong><span>Mapped drainage, canal, levee, and embankment distance</span></div></div><p className="limit-note">Alert status: monitoring only. No public warning, notification, or life-safety alert is enabled. Any future analyst-review workflow requires a validated local-stage or calibrated coastal-water record, complete timestamped inputs, and a new chronological holdout evaluation.</p><p className="limit-note">Limitations: local river-stage observations, a Maubin-relevant tide and surge record spanning the full validation interval, drainage capacity, levee condition, and verified field observations are not represented. Treat all outputs as experimental analytical context.</p></section></div>}
  </div>;
}
