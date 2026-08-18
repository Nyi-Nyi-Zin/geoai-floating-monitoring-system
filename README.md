# DeltaWatch — မြန်မာဘာသာ Setup နှင့် အသုံးပြုနည်း

DeltaWatch သည် မြန်မာနိုင်ငံ၊ ဧရာဝတီတိုင်းဒေသကြီး၊ **Maubin Township** အတွက် မြေပြင်အခြေအနေစစ်ဆေးခြင်း၊ အတိတ်ရေလွှမ်းမိုးမှု model replay နှင့် prospective input monitoring ကိုပေါင်းစပ်ထားသော web dashboard ဖြစ်သည်။ ဤ project ကို **Monitoring only** မူဝါဒဖြင့် ထိန်းသိမ်းထားပြီး public real-time flood probability၊ public warning သို့မဟုတ် life-safety alert မထုတ်ပါ။

> **အရေးကြီးသော သတ်မှတ်ချက်** — `Flood Risk` သည် static terrain screening ဖြစ်သည်။ `Historical HGB v7 heatmap` သည် ရွေးထားသော အတိတ် GFD event အတွက် model hindcast/replay ဖြစ်သည်။ Prospective rainfall၊ soil-moisture နှင့် discharge input များသည် validation အတွက်သာ စုဆောင်းထားခြင်းဖြစ်ပြီး လက်ရှိ/အနာဂတ် flood probability အဖြစ် မဖော်ပြပါ။

## ၁။ အခြားစက်တစ်လုံးတွင် လိုအပ်သော software

အောက်ပါ version များ သို့မဟုတ် ထိုထက်အသစ်များကို install လုပ်ထားရမည်။

| လိုအပ်ချက် | ရည်ရွယ်ချက် |
|---|---|
| Git | Repository နှင့် branch ရယူရန် |
| Node.js 22 | React၊ Vite၊ Express နှင့် build process အတွက် |
| pnpm 10 | Dependency installation နှင့် scripts run ရန် |
| Python 3.12 | Colocated FastAPI spatial service နှင့် deployment workflow အတွက် |
| MySQL/TiDB-compatible database | Rainfall history၊ prospective snapshot နှင့် schedule state သိမ်းရန် |
| Docker (optional) | Production container ပုံစံအတိုင်း local စမ်းသပ်ရန် |

Node.js နှင့် pnpm version စစ်ရန်မှာ—

```bash
node --version
pnpm --version
python3 --version
```

## ၂။ Repository ရယူခြင်း

GitHub repository ကို clone ပြီး Maubin presentation အတွက်အသုံးပြုမည့် branch ကို checkout လုပ်ပါ။

```bash
git clone https://github.com/Nyi-Nyi-Zin/geoai-floating-monitoring-system.git
cd geoai-floating-monitoring-system
git fetch --all --prune
git checkout feat/maubin
git pull --ff-only origin feat/maubin
```

လက်ရှိ Maubin release branch နှင့် commit ကို စစ်ရန်—

```bash
git branch --show-current
git log -1 --oneline
```

`feat/myanmar` သည် nationwide expansion development branch ဖြစ်သဖြင့် Maubin presentation အတွက် `feat/maubin` ကိုသာ အသုံးပြုပါ။

## ၃။ Dependency install လုပ်ခြင်း

Project root directory အတွင်းတွင်—

```bash
pnpm install --frozen-lockfile
```

`pnpm-lock.yaml` နှင့် `package.json` မကိုက်ညီလျှင် `--frozen-lockfile` error ဖြစ်နိုင်သည်။ ထိုအခြေအနေတွင် branch ကိုမှန်ကန်စွာ checkout ထားကြောင်း စစ်ပြီး နောက်ဆုံးအခြေအနေကို pull လုပ်ပါ။ Dependency ကို ကိုယ်တိုင်ပြောင်းပြီး lockfile မပြောင်းဘဲ commit မလုပ်ပါနှင့်။

## ၄။ Environment variables ပြင်ဆင်ခြင်း

Local development တွင် database နှင့် platform integration အတွက် environment variables လိုအပ်သည်။ `.env` ဖိုင်ကို Git ထဲသို့ မထည့်ရပါ။ Project template နှင့် deployment platform မှ အောက်ပါ variable များကို ပေးနိုင်သည်။

| Variable | အသုံးပြုသည့်နေရာ |
|---|---|
| `DATABASE_URL` | MySQL/TiDB database connection |
| `JWT_SECRET` | Session နှင့် server-side signing |
| `BUILT_IN_FORGE_API_URL`၊ `BUILT_IN_FORGE_API_KEY` | Managed storage နှင့် platform APIs |
| `VITE_FRONTEND_FORGE_API_URL`၊ `VITE_FRONTEND_FORGE_API_KEY` | Frontend platform API access |
| `OAUTH_SERVER_URL`၊ `VITE_OAUTH_PORTAL_URL`၊ `VITE_APP_ID` | Framework OAuth infrastructure; public evidence submission အတွက် login မလို |
| `OWNER_OPEN_ID`၊ `OWNER_NAME` | Owner/admin context |
| `CDS_API_KEY` | ခွင့်ပြုထားသော C3S/CDS data acquisition workflow ရှိလျှင်သာ |

Local machine တွင် `.env` အသုံးပြုမည်ဆိုပါက platform မှရရှိသော တန်ဖိုးများကိုသာထည့်ပါ။ API key၊ database password၊ JWT secret သို့မဟုတ် user data ကို source code ထဲတွင် hard-code မလုပ်ရပါ။ Production secret များကို repository တွင် commit မလုပ်ရပါ။

## ၅။ Database schema နှင့် local run

Schema ကိုပြောင်းလဲထားပါက Drizzle migration workflow ကို သုံးပါ။ Database URL သည် local သို့မဟုတ် authorized development database ဖြစ်ရမည်။

```bash
pnpm db:push
```

Development server စတင်ရန်—

```bash
pnpm dev
```

Server သည် ပုံမှန်အားဖြင့် local port ကိုအသုံးပြုမည်။ Terminal မှာ ပြသော URL ကို browser ဖြင့်ဖွင့်ပါ။ Port ကို source code ထဲတွင် hard-code မလုပ်ထားရပါ။

Production-style build စမ်းသပ်ရန်—

```bash
pnpm build
pnpm start
```

## ၆။ စစ်ဆေးရန် command များ

Code နှင့် test စစ်ဆေးမှုများကို commit မလုပ်မီ run ပါ။

```bash
pnpm check
pnpm test
pnpm build
```

လက်ရှိ Maubin branch တွင် authentication၊ anonymous evidence၊ monitoring status၊ prospective snapshot၊ terrain screening၊ cell detail နှင့် HGB v7 heatmap ဆိုင်ရာ regression tests များပါဝင်သည်။ Test failure ကို မဖုံးကွယ်ဘဲ error log နှင့်အတူ ပြင်ဆင်ရမည်။

## ၇။ Production deployment အကြောင်း

ဤ project သည် managed autoscale hosting အတွက်ဖန်တီးထားသည်။ Local machine မှ `pnpm start` လုပ်ခြင်းသည် production deployment မဟုတ်ပါ။ Deployment နှင့် public domain ကို project management environment မှ ပြုလုပ်ရသည်။ လက်ရှိ public site သည် [deltawatch-jayyutyh.manus.space](https://deltawatch-jayyutyh.manus.space/) ဖြစ်သည်။

Scheduled rainfall နှင့် six-hour prospective refresh များသည် public deployment endpoint ရှိမှသာ အလုပ်လုပ်နိုင်သည်။ Local server သည် schedule state ကို production နှင့်မမျှဝေသင့်ပါ။ Runtime အတွင်း local disk သို့ရေးပြီး data တည်မြဲမည်ဟု မယူဆပါနှင့်။ Durable data ကို database သို့မဟုတ် managed storage တွင် သိမ်းရမည်။

## ၈။ အသုံးပြုနည်း အကျဉ်း

Dashboard ဖွင့်ပြီး satellite/terrain basemap ရွေးနိုင်သည်။ `Flood Risk` ကိုဖွင့်ထားလျှင် blue၊ yellow၊ orange၊ red terrain-screening bands ကိုမြင်ရမည်။ `Grid Cells` ဖွင့်ပြီး cell တစ်ခုကိုနှိပ်လျှင် elevation၊ relief၊ mapped waterway distance၊ land cover နှင့် static screening context ကိုကြည့်နိုင်သည်။

`Historical HGB v7 heatmap` ဖွင့်ရန်အတွက် historical GFD event dropdown မှ event တစ်ခုရွေးပါ။ ထို layer သည် ရွေးထားသော past event အတွက် model replay ကိုသာပြပြီး current/future prediction မဟုတ်ပါ။ Field evidence ကို login မလိုဘဲ browser-scoped anonymous contributor token ဖြင့်တင်နိုင်သည်။ Analyst review controls သည် public user များအတွက် မဖွင့်ထားပါ။

## ၉။ ပြဿနာဖြေရှင်းခြင်း

Map မပေါ်လျှင် spatial API health၊ database availability နှင့် managed seed storage access ကိုစစ်ပါ။ Rainfall history မပေါ်လျှင် nightly ERA5 refresh သည် မပြေးရသေးခြင်း သို့မဟုတ် source unavailable ဖြစ်နိုင်သည်။ Dashboard တွင် `Awaiting first refresh`၊ `Late` သို့မဟုတ် `Unavailable` ကို အမှန်အတိုင်းပြထားပြီး missing data ကို current ဟု မယူဆပါ။

`pnpm install` ပြီးနောက် TypeScript error ဖြစ်လျှင် Node/pnpm version၊ branch၊ lockfile နှင့် `.env` ကို အရင်စစ်ပါ။ API key များကို terminal history သို့မဟုတ် screenshot ဖြင့် မမျှဝေပါနှင့်။

## ၁၀။ အသေးစိတ် documentation

Feature တစ်ခုချင်းစီ၏ data flow၊ model input၊ dataset source၊ limitation နှင့် Monitoring-only boundary ကို [`docs/FEATURES_AND_DATA_MM.md`](docs/FEATURES_AND_DATA_MM.md) တွင်ဖတ်ပါ။ Operator runbook ကို [`docs/operator_runbook.md`](docs/operator_runbook.md)၊ architecture ကို [`ARCHITECTURE.md`](ARCHITECTURE.md) နှင့် model source assessment ကို [`model-data-sources.md`](model-data-sources.md) တွင်ကြည့်နိုင်သည်။

## References

[1]: https://github.com/Nyi-Nyi-Zin/geoai-floating-monitoring-system "DeltaWatch GitHub repository"
[2]: https://open-meteo.com/ "Open-Meteo weather and climate APIs"
[3]: https://github.com/cloudtostreet/MODIS_GlobalFloodDatabase "MODIS Global Flood Database archive"
[4]: https://www.copernicus.eu/en/access-data/copernicus-services-catalogue "Copernicus data and services"
[5]: https://esa-worldcover.org/en "ESA WorldCover"
[6]: https://www.openstreetmap.org/ "OpenStreetMap"
[7]: https://ewds.climate.copernicus.eu/datasets/cems-glofas-historical "Copernicus CEMS GloFAS historical dataset"
[8]: https://www.aviso.altimetry.fr/en/data/products/auxiliary-products/global-tide-fes.html "AVISO FES2022 tide product"
[9]: https://dahiti.dgfi.tum.de/en/products/water-level-altimetry/ "DAHITI water-level altimetry"
[10]: https://research.vu.nl/en/datasets/daily-maxima-of-total-water-levels-from-the-global-tide-and-surge/ "Global Tide and Surge Reanalysis"
[11]: https://zenodo.org/records/10671284 "GTSM-ERA5-E archive"
[12]: https://leafletjs.com/ "Leaflet mapping library"
[13]: https://orm.drizzle.team/ "Drizzle ORM documentation"
[14]: https://fastapi.tiangolo.com/ "FastAPI documentation"
[15]: https://nodejs.org/ "Node.js"
[16]: https://pnpm.io/ "pnpm"
