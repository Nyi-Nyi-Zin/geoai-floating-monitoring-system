# DeltaWatch `feat/maubin` — Features၊ Data Flow နှင့် Dataset များ

ဤစာတမ်းသည် `feat/maubin` branch တွင် လက်ရှိပါဝင်နေသော feature များ၊ feature တစ်ခုချင်းစီတွင် ပေါင်းစပ်အသုံးပြုထားသော data/model/service များ၊ dataset တစ်ခုချင်းစီ၏ မူလရင်းမြစ်နှင့် အသုံးပြုရာ limitation များကို မြန်မာဘာသာဖြင့်ရှင်းပြထားခြင်းဖြစ်သည်။ ဤ branch ၏ presentation scope သည် **Maubin Township** ဖြစ်ပြီး nationwide `feat/myanmar` development scope နှင့် မတူပါ။

## ၁။ System ၏ အဓိကရည်ရွယ်ချက်

DeltaWatch သည် ရေလွှမ်းမိုးမှုနှင့်ပတ်သက်သော **analytical context** ကို map ပေါ်တွင် စုစည်းပြသသည့် system ဖြစ်သည်။ ၎င်းတွင် terrain screening၊ historical flood event replay၊ rainfall watch၊ prospective input monitoring နှင့် field evidence collection ပါဝင်သည်။ ထို feature များကို အတူကြည့်နိုင်သော်လည်း ၎င်းတို့၏ အဓိပ္ပါယ်များမှာ မတူညီပါ။

> **Monitoring only** — လက်ရှိ public dashboard သည် real-time flood probability၊ future flood forecast၊ public alert၊ SMS/notification သို့မဟုတ် life-safety decision မပေးပါ။ Input data များကို prospective validation နှင့် operational monitoring အတွက်သာ သိမ်းဆည်းထားသည်။

## ၂။ Feature နှင့် ပေါင်းစပ်အသုံးပြုသော data များ

| Feature | Map/UI တွင် မြင်ရသည့်အရာ | ပေါင်းစပ်အသုံးပြုသည့် data/model | အဓိပ္ပါယ်နှင့် limitation |
|---|---|---|---|
| **Flood Risk · terrain screening** | Blue၊ yellow၊ orange၊ red band များဖြင့် cell များ | Copernicus DEM terrain metrics၊ local relief၊ mapped waterway distance၊ ESA WorldCover land-cover context၊ drainage/levee distance နှင့် durable static seed | မြေပြင်အနေအထားအရ ရေဘေးဖြစ်လွယ်နိုင်မှု screening ဖြစ်သည်။ လက်ရှိမိုးရွာမှု၊ gauge water level သို့မဟုတ် live probability မဟုတ်ပါ။ |
| **Grid Cells** | 500 m အခြေပြု terrain cell များနှင့် cell click interaction | Static terrain cell seed၊ cell ID၊ elevation၊ relief၊ land cover၊ waterway/drainage/levee distances | Cell တစ်ခုချင်းစီ၏ တွက်ချက်ထားသော context ကိုကြည့်ရန်ဖြစ်သည်။ Cell detail ထဲတွင် public warning မပါပါ။ |
| **Historical Flood** | အတိတ် GFD flood event polygon layer | Official Global Flood Database event GeoTIFF များ၏ native flood နှင့် permanent-water bands | အတိတ် satellite-derived event extent ကိုပြသည်။ လက်ရှိရေလွှမ်းမိုးမှုအဖြစ် မယူဆရပါ။ |
| **Historical HGB v7 heatmap** | ရွေးထားသော event အပေါ် model band အရောင်များ | HGB v7 trained model ၏ per-cell historical predictions နှင့် ရွေးထားသော GFD event | အတိတ် event replay/hindcast ဖြစ်သည်။ model သုံးထားသော်လည်း current/future forecast မဟုတ်ပါ။ |
| **Experimental event hindcast** | Historical event dropdown၊ observed extent၊ precision၊ recall | GFD labels၊ v7 hydrologic/static features၊ chronological holdout evaluation | Model ၏ historical performance ကိုလေ့လာရန်ဖြစ်သည်။ Current public probability သို့မဟုတ် alert readiness မဟုတ်ပါ။ |
| **Rainfall watch** | နောက် ၇ ရက် rainfall bar chart | Open-Meteo forecast API၊ Maubin coordinate `16.7247, 95.6687` | Forecast rainfall ကို ပြသသည်။ ၎င်းသည် တစ်ခုတည်းဖြင့် flood forecast သို့မဟုတ် alert မဖြစ်ပါ။ |
| **ERA5 rainfall history** | ၃၀ ရက် rainfall history sparkline၊ freshness state | Open-Meteo archive API မှ ERA5-derived completed daily precipitation | Historical rainfall context ဖြစ်သည်။ Refresh မအောင်မြင်လျှင် `Late`/`Unavailable` ကို ဖော်ပြပြီး current ဟု မယူဆပါ။ |
| **Prospective input monitoring** | Six-hour issue time၊ target date၊ freshness နှင့် job health | Open-Meteo hourly precipitation၊ soil moisture၊ flood API river discharge နှင့် p25/p75၊ static v7 seed | Future-time features ကိုသိမ်းပြီး validation အတွက်သာအသုံးပြုသည်။ public probability၊ predicted label၊ alert field မထုတ်ပေးပါ။ |
| **Field evidence** | Login မလိုသော evidence form၊ photo reference upload | Browser-scoped anonymous contributor token၊ user-entered observation၊ managed object storage၊ database metadata | လူထုထံမှ validation evidence စုဆောင်းရန်ဖြစ်သည်။ Public reviewer decision မပြပါ။ Evidence သည် အလိုအလျောက် ground truth မဖြစ်ပါ။ |
| **Operational status** | Spatial DB၊ data refresh၊ prospective job၊ open alerts၊ alert mode | Database schedule state၊ rainfall history freshness၊ prospective snapshot state၊ server health | System ၏ data freshness နှင့် job health ကို ပြသသည်။ `Open alerts 0` သည် alert engine အလုပ်လုပ်နေသည်ဟု မဆိုလိုပါ။ |
| **Methodology** | About/Methodology modal | Data provenance၊ model limitation နှင့် safety boundary documentation | System ကို public warning system အဖြစ် အထင်မမှားရန် သတ်မှတ်ချက်များကို ဖော်ပြသည်။ |

## ၃။ Flood Risk နှင့် Historical HGB v7 ကွာခြားချက်

**Flood Risk · terrain screening** layer သည် မြေပြင်အချက်အလက်အပေါ် အဓိကထားသည်။ မြေပြင်နိမ့်မှု၊ elevation၊ local relief၊ ရေလမ်းနှင့်အကွာအဝေး၊ land cover၊ drainage/levee map context စသည့် static feature များကိုပေါင်းစပ်ပြီး terrain screening band ခွဲထားသည်။ ထို layer သည် မိုးရွာနေခြင်း၊ မြစ်ရေတက်နေခြင်း သို့မဟုတ် လာမည့်အပတ်တွင် ရေလွှမ်းမိုးမည်ကို မပြောပါ။

**Historical HGB v7 heatmap** သည် trained Histogram Gradient Boosting model ၏ past-event result ကို ပြန်လည်ဖော်ပြသည်။ User က GFD historical event တစ်ခုရွေးသောအခါ ထို event အတွက် cell-by-cell model output ကို heatmap band များဖြင့်မြင်ရသည်။ ထိုအရောင်များသည် ရွေးထားသော အတိတ် event ၏ replay ဖြစ်ပြီး ယနေ့ သို့မဟုတ် အနာဂတ် probability မဟုတ်ပါ။

ထို့ကြောင့် map ပေါ်တွင် နှစ်ခုလုံးကို ON ထားလျှင် static terrain layer နှင့် historical model replay layer ကို တစ်ပြိုင်နက်နှိုင်းယှဉ်နိုင်သည်။ `Grid Cells` ကို ON ထားပြီး cell ကိုနှိပ်လျှင် static context နှင့် ရွေးထားသော event ၏ historical classification ကို ပိုမိုအသေးစိတ်ဖတ်နိုင်သည်။

## ၄။ HGB v7 model ၏ feature များ

v7 model ၏ static/land context တွင် အောက်ပါ feature များပါဝင်သည်။

| Feature family | ဥပမာ feature | အသုံးပြုသည့်အကြောင်း |
|---|---|---|
| Terrain | Mean elevation၊ elevation percentile၊ local relief | ရေစုပုံနိုင်မှုနှင့် မြေပြင်အနိမ့်အမြင့် context |
| Hydrology proximity | Nearest mapped waterway distance | ရေလမ်းနှင့် နီးကပ်မှု context |
| Land cover | Dominant ESA WorldCover class | မြေမျက်နှာပြင်အမျိုးအစားနှင့် runoff context |
| Drainage/levee map context | OpenStreetMap drainage distance၊ levee distance | Mapped drainage/embankment infrastructure proximity |
| Rainfall dynamics | ERA5 rainfall lag 1၊ 3၊ 7၊ 14၊ 30 days | အတိတ်စိုစွတ်မှု/မိုးရေစုဆောင်းမှု proxy |
| Upstream hydrology proxy | GloFAS discharge lag 1၊ 3၊ 7၊ 14၊ 30 days | Upstream inflow/wetness proxy |
| Tide/surge candidate | GTSM/FES/other coastal proxy experiments | စမ်းသပ်ခဲ့သော်လည်း production v7 ထဲမထည့်ထားပါ |

Dynamic feature များကို target observation မတိုင်မီရက်များမှသာ ယူရန် leakage-safe date rule သုံးထားသည်။ Tide/surge သည် Maubin-local gauge မဟုတ်သည့် modelled coastal proxy ဖြစ်ပြီး complete 2002–2018 holdout နှင့် calibration မပြည့်စုံသေးသောကြောင့် production v7 ထဲ မထည့်ထားပါ။

## ၅။ Dataset provenance နှင့် အသုံးပြုပုံ

| Dataset | မူလရင်းမြစ် | Project ထဲတွင် အသုံးပြုသည့်နေရာ | အရေးကြီးသော limitation |
|---|---|---|---|
| **Copernicus DEM** | Copernicus data ecosystem | Elevation၊ elevation percentile၊ local terrain screening | DEM သည် local gauge မဟုတ်ပါ။ Terrain representation နှင့် resolution limitation ရှိသည်။ |
| **ESA WorldCover** | ESA WorldCover | Dominant land-cover context | Land cover သည် flood observation သို့မဟုတ် water level တိုင်းတာချက် မဟုတ်ပါ။ |
| **GFD event maps** | Cloud to Street / MODIS Global Flood Database public archive | Maubin-relevant historical flood labels၊ observed event polygons | Satellite-derived event-scale label ဖြစ်ပြီး cloud၊ mapping error နှင့် permanent-water exclusion limitation ရှိသည်။ |
| **ERA5 rainfall** | Copernicus/ECMWF climate reanalysis ကို Open-Meteo archive မှ access | Historical rainfall lags၊ 30-day dashboard history | Reanalysis ဖြစ်၍ Maubin local rain gauge မဟုတ်ပါ။ |
| **Open-Meteo forecast** | Open-Meteo API | 7-day rainfall watch နှင့် prospective hourly precipitation | Forecast source ဖြစ်ပြီး flood impact model တစ်ခုတည်း မဟုတ်ပါ။ |
| **GloFAS** | Copernicus CEMS GloFAS | Upstream discharge/wetness proxy၊ prospective river-discharge input | Modelled global hydrology ဖြစ်၍ Maubin local river gauge မဟုတ်ပါ။ |
| **OpenStreetMap** | OpenStreetMap community mapping | Waterway၊ drainage၊ canal၊ levee/embankment distance context | Mapped feature မပြည့်စုံနိုင်ပြီး infrastructure condition ကို မအာမခံပါ။ |
| **GTSM-ERA5-E** | Global tide and surge reanalysis / C3S-authorized acquisition workflow | v8 coastal proxy experiment အတွက်သာ စမ်းသပ် | Modelled coastal water level ဖြစ်၍ local Maubin tide gauge မဟုတ်ပါ။ v8 သည် v7 ထက် မတိုးတက်သဖြင့် deploy မလုပ်ထားပါ။ |
| **FES2022** | AVISO/FES tide atlas | Tide candidate source assessment | Tidal constituent atlas ဖြစ်၍ total water level/surge သို့မဟုတ် local gauge substitute မဟုတ်ပါ။ |
| **DAHITI** | DGFI-TUM satellite water-level altimetry | Local/upstream stage candidate assessment | Observation interval မမှန်နိုင်၊ station distance/datum coverage မပြည့်စုံနိုင်၊ 2018 holdout မဖုံးနိုင်ပါ။ Production v7 ထဲ မထည့်ထားပါ။ |
| **Field observations** | Public contributors မှ တင်သွင်းသော observation နှင့် photo reference | Prospective validation/evidence readiness | Synthetic evidence မဖန်တီးပါ။ User report တစ်ခုသည် independent verified label မဟုတ်ပါ။ |

## ၆။ Spatial data flow

```text
Managed storage static seeds
        │
        ▼
Colocated FastAPI spatial service
  /api/spatial/health
  /api/spatial/terrain
  /api/spatial/waterways
  /api/spatial/flood-events
  /api/spatial/hindcast/:eventId
  /api/spatial/rainfall-history
        │
        ▼
React + Leaflet client
  Flood Risk / Grid Cells / Historical Flood / HGB heatmap
```

Spatial JSON seed များကို application image ထဲတွင် အမြဲတမ်းဖိုင်အဖြစ် မထည့်ဘဲ managed storage မှ ဖတ်သည်။ ထိုပုံစံသည် autoscale instance များတွင် local disk မတည်မြဲသည့် limitation ကို လျှော့ချပေးသည်။

## ၇။ Prospective monitoring flow

Six-hour monitoring refresh သည် Open-Meteo hourly weather/soil-moisture endpoint နှင့် Open-Meteo flood endpoint မှ input များကိုရယူသည်။ ထို့နောက် rainfall lag၊ discharge lag နှင့် static 5,549-cell seed ကို ပေါင်းပြီး target date အတွက် future-time feature projection ကို database ထဲတွင် သိမ်းသည်။

Projection record တွင် issue time၊ source coverage၊ target date၊ quality flag နှင့် model version ပါဝင်သည်။ သို့သော် public probability၊ predicted label၊ warning level သို့မဟုတ် alert action မပါဝင်ပါ။ ထို design သည် automation ကိုစမ်းသပ်နိုင်စေပြီး validation outcome မရသေးခင် unsupported public prediction မထုတ်စေရန် ရည်ရွယ်သည်။

## ၈။ Login-free evidence flow

Public user သည် login မဝင်ဘဲ Evidence form ကိုအသုံးပြုနိုင်သည်။ Browser-scoped opaque contributor token သည် contributor တစ်ဦး၏ throttling နှင့် duplicate control ကို ကူညီပေးသည်။ Token ထဲတွင် user name သို့မဟုတ် password မထည့်ပါ။ Observation metadata နှင့် photo reference ကို server-side validation ပြီးမှ managed storage/database တွင်သိမ်းသည်။

Public user သည် အခြားသူ၏ evidence ကို verify/reject မလုပ်နိုင်ပါ။ Review state transition သည် protected analyst workflow အောက်တွင် တစ်ကြိမ်သာလုပ်နိုင်ပြီး observation မရှိပါက controlled error ပြန်ပေးသည်။ Evidence workflow သည် alert workflow မဟုတ်ပါ။

## ၉။ လက်ရှိ data gap နှင့် မလုပ်သင့်သည့်အရာများ

Maubin/Nyaungdon local river-stage၊ local tide/surge၊ drainage capacity၊ levee condition နှင့် complete verified field labels များသည် production-grade real-time flood prediction အတွက် အရေးကြီးသည်။ လက်ရှိတွင် အချို့ candidate source များသည် modelled proxy သာဖြစ်ပြီး local gauge မဟုတ်ပါ။ Missing data ကို interpolate၊ fabricate သို့မဟုတ် fake evidence ဖြင့် မဖြည့်ရပါ။

အောက်ပါအရာများကို public release တွင် မလုပ်ရပါ။

1. Static terrain band ကို real-time probability ဟု မရေးရပါ။
2. Historical HGB v7 heatmap ကို current/future forecast ဟု မရေးရပါ။
3. Prospective feature projection မှ probability သို့မဟုတ် public alert မထုတ်ရပါ။
4. Unverified tide၊ gauge၊ field observation ကို validated input ဟု မသတ်မှတ်ရပါ။
5. Customer review၊ rating၊ testimonial သို့မဟုတ် fabricated field evidence မထည့်ရပါ။

## ၁၀။ Source links

[1]: https://github.com/cloudtostreet/MODIS_GlobalFloodDatabase "MODIS Global Flood Database"
[2]: https://ewds.climate.copernicus.eu/datasets/cems-glofas-historical "CEMS GloFAS historical"
[3]: https://www.aviso.altimetry.fr/en/data/products/auxiliary-products/global-tide-fes.html "FES2022"
[4]: https://research.vu.nl/en/datasets/daily-maxima-of-total-water-levels-from-the-global-tide-and-surge/ "Global Tide and Surge Reanalysis"
[5]: https://zenodo.org/records/10671284 "GTSM-ERA5-E"
[6]: https://dahiti.dgfi.tum.de/en/products/water-level-altimetry/ "DAHITI water-level altimetry"
[7]: https://open-meteo.com/ "Open-Meteo"
[8]: https://esa-worldcover.org/en "ESA WorldCover"
[9]: https://www.openstreetmap.org/ "OpenStreetMap"
[10]: https://www.copernicus.eu/en/access-data/copernicus-services-catalogue "Copernicus services"
