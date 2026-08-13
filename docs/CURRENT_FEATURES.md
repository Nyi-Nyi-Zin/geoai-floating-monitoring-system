# FloodGuard Myanmar — လက်ရှိအသုံးပြုနိုင်သော Features

နောက်ဆုံးစစ်ဆေးထားသည့်ရက်: **2026-07-31**

ဤစာတမ်းသည် Maubin Township project တွင် အမှန်တကယ် implement လုပ်ပြီး
အသုံးပြုနိုင်သော feature များကို စုစည်းထားသည်။ Flood prediction မပြီးသေးခြင်းကို
ရှင်းလင်းစေရန် dashboard-ready၊ API-ready နှင့် not-yet-available ဟူ၍ ခွဲထားသည်။

## 1. Feature Status

| အပိုင်း | Status | လက်ရှိလုပ်ဆောင်နိုင်မှု |
|---|---|---|
| PostgreSQL + PostGIS | အသုံးပြုနိုင် | Boundary၊ waterways၊ terrain cells၊ observations နှင့် metadata သိမ်းဆည်းခြင်း |
| Dashboard | အသုံးပြုနိုင် | Maubin terrain၊ waterways၊ land cover နှင့် susceptibility ကြည့်ခြင်း |
| 2D map | အသုံးပြုနိုင် | Zoom၊ pan၊ layer switching နှင့် feature inspection |
| MapLibre 3D map | အသုံးပြုနိုင် | Regional terrain pitch၊ rotate၊ zoom၊ fullscreen နှင့် visual exaggeration |
| CesiumJS globe | အသုံးပြုနိုင် | Satellite/Streets basemap၊ WGS84 globe၊ streamed terrain၊ camera orbit နှင့် GeoAI overlays |
| Terrain screening | အသုံးပြုနိုင် | Elevation၊ water proximity နှင့် flatness အလိုက် relative score တွက်ခြင်း |
| Rainfall forecast | အသုံးပြုနိုင် | Open-Meteo 1–7 day forecast |
| Historical rainfall | အသုံးပြုနိုင် | 2015–2025 ERA5 daily history API နှင့် dashboard 30/90/366-day chart |
| Historical flood labels | အသုံးပြုနိုင် | GFD 2000–2018 frequency 1–8၊ 473.488 km²၊ PostGIS/API နှင့် 2D/3D/Cesium color layer |
| Historical ML susceptibility | အသုံးပြုနိုင် | 5,549 cells၊ spatial test ROC-AUC 0.7782၊ PR-AUC 0.8111၊ F1 0.7462 နှင့် versioned probability API/map layer |
| Sensor ingestion | API-ready | Station register နှင့် ESP32/MQTT/HTTP reading လက်ခံခြင်း |
| Live chart | UI-ready, data မရှိသေး | Real reading ရှိလာလျှင် WebSocket ဖြင့် update |
| Threshold alerts | API-ready, sensor မရှိသေး | Real observation နှင့် configured thresholds ကိုနှိုင်းယှဉ်ခြင်း |
| Flood prediction | **မရသေး** | Probability၊ depth၊ extent နှင့် arrival time prediction မရှိသေး |

## 2. Dashboard Features

Dashboard: <http://127.0.0.1:3000>

### Overview cards

- Backend/PostGIS connection status
- Terrain-cell count နှင့် elevation range
- River/canal network summary
- `VERY HIGH` screening-cell count
- Rainfall forecast၊ station နှင့် alert status

### 2D map

- Leaflet + OpenStreetMap basemap
- Mouse wheel/control zoom၊ drag/touch pan နှင့် reset
- Cursor coordinates နှင့် zoom-level readout
- Terrain cell/waterway ကိုနှိပ်ပြီး spatial inspector ကြည့်ခြင်း
- လမ်း၊ ရွာနှင့် နေရာအမည်များအပေါ် GeoAI overlays တင်ကြည့်ခြင်း

### 3D map

- MapLibre GL JS terrain rendering
- Zoom၊ pan၊ rotate၊ tilt၊ compass နှင့် fullscreen
- Maubin camera view သို့ reset
- Vertical exaggeration `1×–8×`
- Elevation၊ susceptibility၊ land-cover နှင့် waterways overlays
- Terrain cell/waterway click inspection

Default 3D terrain tiles သည် Mapterhorn TileJSON ကိုအသုံးပြုသဖြင့် internet
connection လိုအပ်သည်။ Exaggeration သည် Maubin ၏ နည်းပါးသော elevation
difference ကို ထင်ရှားစေရန်သာဖြစ်ပြီး flood depth/simulation မဟုတ်ပါ။

### CesiumJS globe

- Dashboard map switch မှ `Cesium` ကိုရွေးပြီး WGS84 globe view သုံးနိုင်သည်။
- Default အနေဖြင့် Esri World Imagery satellite basemap ကိုပြပြီး `Satellite / Streets` ခလုတ်ဖြင့် OpenStreetMap သို့ပြောင်းနိုင်သည်။
- Default အနေဖြင့် token မလိုသော ArcGIS World Elevation terrain ကို stream လုပ်သည်။
- `NEXT_PUBLIC_CESIUM_ION_TOKEN` ထည့်ထားလျှင် Cesium World Terrain သုံးသည်။
- Terrain service မရပါက ellipsoid fallback ဖြင့် overlays ဆက်ကြည့်နိုင်သည်။
- Elevation၊ susceptibility၊ land cover၊ township boundary နှင့် waterways ကို တူညီသော API data ဖြင့်ပြသည်။
- Cell/segment selection သည် dashboard spatial inspector နှင့်ချိတ်ထားသည်။
- Orbit၊ zoom၊ tilt၊ fullscreen၊ Maubin reset နှင့် `1×–8×` vertical exaggeration ပါသည်။

Cesium terrain သည် visualization context ဖြစ်ပြီး project ၏ Copernicus 30 m
screening inputs ကိုအစားထိုးခြင်းမဟုတ်ပါ။ Cesium exaggeration သည်လည်း flood
depth သို့မဟုတ် water simulation မဟုတ်ပါ။

### Map layers

#### Elevation

- Copernicus DEM GLO-30 30 m source ကို township-clipped 500 m analysis/display cells အဖြစ် summary လုပ်ထားသည်။
- Cell တစ်ခုစီတွင် minimum/mean/maximum elevation၊ percentile၊ local relief နှင့် DEM sample count ပါသည်။

#### Susceptibility

Relative screening score `0–100` ကို အောက်ပါ explainable factors ဖြင့်တွက်သည်။

| Factor | Weight | အဓိပ္ပာယ် |
|---|---:|---|
| Low relative elevation | 55% | Township အတွင်း အခြား cell များထက်နိမ့်ပါက contribution ပိုမြင့် |
| Waterway proximity | 30% | OSM mapped river/canal နှင့်နီးပါက contribution ပိုမြင့် |
| Local flatness | 15% | Local relief နည်းပြီး မြေပြန့်ပါက contribution ပိုမြင့် |

Score bands:

- `LOWER`: 25 အောက်
- `MODERATE`: 25 မှ 50 အောက်
- `HIGH`: 50 မှ 75 အောက်
- `VERY HIGH`: 75 နှင့်အထက်

Cell ကိုနှိပ်လျှင် observed value၊ normalized score၊ weight နှင့် contribution
တစ်ခုစီကို inspector တွင်ကြည့်နိုင်သည်။ ဤ result သည် **relative terrain
screening** သာဖြစ်ပြီး flood probability၊ depth သို့မဟုတ် arrival sequence မဟုတ်ပါ။

#### Land cover

- ESA WorldCover 2021 v200 10 m classification ကို terrain cells အားလုံးနှင့်ချိတ်ထားသည်။
- Dominant class နှင့် class-percentage composition ကြည့်နိုင်သည်။
- Tree cover၊ cropland၊ built-up၊ permanent water၊ wetland၊ mangrove စသည့် classes ပါဝင်သည်။
- လက်ရှိ susceptibility formula တွင် land cover ကို weight မထည့်ရသေးပါ။

#### Waterways

- OpenStreetMap river/canal network
- River/canal filter နှင့် name/OSM-ID search
- Segment name၊ type၊ length နှင့် source metadata inspection
- Community mapping ဖြစ်သဖြင့် local drainage channels အချို့ မပါနိုင်ပါ။

### Rainfall and observations

- Next-24-hour precipitation total
- Seven-day rainfall outlook
- Forecast timestamp/source status
- Registered-station၊ latest-observation နှင့် open-alert status

Forecast rainfall သည် weather-model output ဖြစ်ပြီး observed rainfall မဟုတ်ပါ။

### Live water-level chart

Physical sensor မရှိသေးသောကြောင့် လက်ရှိ chart တွင် real water-level data မရှိပါ။
Station register လုပ်ပြီး reading ပို့လာသည့်အခါ database တွင်သိမ်း၊ WebSocket မှ
dashboard သို့ push လုပ်ပြီး chart/latest-reading card update ဖြစ်မည်။ System သည်
missing readings ကို အလိုအလျောက် generate သို့မဟုတ် interpolate မလုပ်ပါ။

### Data provenance

Active layer တစ်ခုစီအတွက် provider၊ category၊ format၊ resolution၊ quality status၊
source/licence links၊ limitations နှင့် usage constraints ကို dashboard တွင်ပြသည်။
Catalog တွင် Maubin boundary၊ Copernicus DEM၊ OSM waterways၊ ESA WorldCover၊
Open-Meteo forecast နှင့် ERA5 historical rainfall ပါဝင်သည်။

## 3. API Features

Swagger UI: <http://127.0.0.1:8000/docs>

API base: `http://127.0.0.1:8000/api/v1`

### Health and live infrastructure

| Method | Endpoint | အသုံးပြုပုံ |
|---|---|---|
| GET | `/health` | API/database health စစ်ခြင်း |
| GET | `/mqtt/status` | Credentials မဖော်ပြဘဲ MQTT bridge status ကြည့်ခြင်း |
| WS | `/ws/live` | အသစ်ဝင်လာသော sensor readings ကို live receive လုပ်ခြင်း |

### Spatial assets

| Method | Endpoint | အသုံးပြုပုံ |
|---|---|---|
| POST / GET | `/geo-assets` | Spatial asset ဖန်တီးခြင်း/စာရင်းကြည့်ခြင်း |
| GET | `/geo-assets/within-bounds` | WGS84 bounding box နှင့် intersect ဖြစ်သော assets ရှာခြင်း |
| POST | `/geo-assets/import` | GeoJSON FeatureCollection bulk import |
| GET / PATCH / DELETE | `/geo-assets/{asset_id}` | Asset တစ်ခုကြည့်၊ ပြင်၊ ဖျက်ခြင်း |

### Screening evidence

| Method | Endpoint | အသုံးပြုပုံ |
|---|---|---|
| GET | `/flood-screening/terrain/index` | Map-ready compact terrain scores |
| GET | `/flood-screening/terrain` | Geometry၊ methodology နှင့် factor breakdown ပါသော results |
| GET | `/flood-screening/land-cover/summary` | WorldCover class summary |

### Weather and rainfall

| Method | Endpoint | အသုံးပြုပုံ |
|---|---|---|
| GET | `/weather/rainfall-forecast` | Maubin 1–7 day rainfall forecast |
| GET | `/weather/rainfall-history` | 2015–2025 ERA5 daily history ကို date range/limit ဖြင့် query |

Historical rainfall API နှင့် dashboard chart ကို ချိတ်ထားပြီး `30 days`,
`90 days`, `1 year` windows အလိုက် daily mean၊ rolling 7-day accumulation၊
wet days နှင့် latest 30-day accumulation ကိုကြည့်နိုင်သည်။ ERA5 သည်
approximately 25 km model reanalysis ဖြစ်ပြီး local gauge measurement သို့မဟုတ်
flood warning မဟုတ်ပါ။

### Sensor stations and observations

| Method | Endpoint | အသုံးပြုပုံ |
|---|---|---|
| POST / GET | `/stations` | Station register/list |
| GET | `/stations/{station_id}` | Station detail |
| GET | `/stations/{station_id}/readings` | Station readings |
| POST | `/readings` | Idempotent ESP32/HTTP reading ingest |
| POST / GET | `/hydro-observations` | Rainfall၊ river-level သို့မဟုတ် discharge observations create/list |
| GET | `/hydro-observations/latest` | Station တစ်ခုစီ၏ latest observation |
| GET / PATCH | `/hydro-observations/{observation_id}` | Observation detail/quality review |

### Threshold alerts

Configured station thresholds နှင့် observed water level ကို အောက်ပါအတိုင်း
deterministic rule ဖြင့်နှိုင်းယှဉ်သည်။

- Warning threshold: `MEDIUM`
- Danger threshold: `HIGH`
- Critical threshold: `CRITICAL`
- Warning အောက်: `LOW`

| Method | Endpoint | အသုံးပြုပုံ |
|---|---|---|
| GET | `/alerts` | Status/risk/station ဖြင့် alerts ရှာခြင်း |
| PATCH | `/alerts/{alert_id}/acknowledge` | Audit record မဖျက်ဘဲ acknowledge လုပ်ခြင်း |

ဤ alert သည် AI prediction မဟုတ်ပါ။ Sensor မရှိသေးသော လက်ရှိအခြေအနေတွင်
operational alert ထွက်မည်မဟုတ်ပါ။

### Data-layer catalog

| Method | Endpoint | အသုံးပြုပုံ |
|---|---|---|
| POST / GET | `/data-layers` | Provenance record register/list |
| GET / PATCH | `/data-layers/{layer_id}` | Provenance detail/update |

## 4. Run the Project

Backend:

```powershell
cd D:\geo-ai-floating-predection\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd D:\geo-ai-floating-predection\frontend
pnpm dev
```

ဖွင့်ရန်:

- Dashboard: <http://127.0.0.1:3000>
- Swagger: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/health>

## 5. မရသေးသော Features

- Flood probability percentage
- Predicted flood depth/extent
- ဘယ်နေရာအရင်ရေမြုပ်မည်ဆိုသည့် arrival time/sequence
- Rainfall-to-river-stage forecasting model
- Sentinel-1 near-real-time inundation pipeline
- Levee၊ drainage capacity၊ tide၊ soil ပါသော hydraulic model
- Calibrated confidence score
- Telegram/WhatsApp/SMS production alerts
- Human override/review workflow
- Physical sensor observations

## 6. Results ကို မှန်ကန်စွာဖတ်ခြင်း

- `VERY HIGH` cell သည် နိမ့်၊ ရေလမ်းနှင့်နီး၊ မြေပြန့်သောကြောင့် **အရင်စစ်ဆေးသင့်သောနေရာ** ဖြစ်သည်။
- ရေကြီးမည်ဟုအတည်ပြုခြင်း၊ flood probability သို့မဟုတ် arrival time မဟုတ်ပါ။
- 3D relief သည် visualization ဖြစ်ပြီး flood-water simulation မဟုတ်ပါ။
- WorldCover သည် 2021 snapshot ဖြစ်ပြီး OSM waterways တွင် local drains အချို့ကျန်နိုင်သည်။
- Operational ဆုံးဖြတ်ချက်အတွက် field verification၊ official warnings၊ sensors နှင့် historical-flood validation လိုအပ်သည်။

## 7. Demo Flow

1. Spatial DB online status ကိုပြပါ။
2. `Elevation` layer ဖြင့် terrain cells ကိုပြပါ။
3. `Susceptibility` သို့ပြောင်းပြီး `VERY HIGH` cell တစ်ခုကိုနှိပ်ပါ။
4. Inspector ရှိ 55% elevation၊ 30% water proximity၊ 15% flatness breakdown ကိုရှင်းပြပါ။
5. `Land cover` နှင့် `Waterways` layers ကိုပြပါ။
6. `3D` နှင့် `Cesium` views သို့ပြောင်းပြီး regional terrain နှင့် globe view ကိုနှိုင်းယှဉ်ပြပါ။
7. Rainfall forecast နှင့် data provenance ကိုပြပါ။
8. Sensor မရှိသေးခြင်းနှင့် output သည် prediction မဟုတ်ဘဲ explainable screening ဖြစ်ကြောင်းရှင်းပြပါ။
