# Colab — Flood Event Model Comparison (Priority 4)

Train **logistic / Random Forest / HistGradientBoosting (+ optional XGBoost)** on
the exported Maubin event CSV. No PostGIS required.

## 0) Local file you already have

```
D:\geo-ai-floating-predection\backend\data\derived\maubin_flood_event_dataset_v1.csv
```

(~94k rows, flood_excess labels, temporal splits already in the file)

## 1) Open Colab

1. Go to https://colab.research.google.com
2. Runtime → **CPU is enough** (trees do not need GPU for this size)
3. Upload the CSV (Files panel) **or** put it on Google Drive

## 2) Install deps

```python
!pip -q install scikit-learn xgboost
```

## 3) Get the comparison script into Colab

**Easiest:** upload these files from your PC into `/content/`:

- `backend/scripts/compare_flood_event_models.py`
- `backend/scripts/train_flood_event_model.py`
- `backend/scripts/train_flood_susceptibility.py`
- `backend/scripts/build_flood_event_dataset.py`

Then:

```python
import sys
from pathlib import Path

# If you uploaded into /content/scripts/
sys.path.insert(0, "/content")
Path("/content/scripts").mkdir(exist_ok=True)
# move/upload py files under /content/scripts/ so `import scripts.*` works:
#   /content/scripts/__init__.py  (empty)
#   /content/scripts/compare_flood_event_models.py
#   ...
Path("/content/scripts/__init__.py").write_text("", encoding="utf-8")
```

**Alternative:** clone the repo if it is on GitHub and private access is set up.

## 4) Upload dataset

```python
from google.colab import files
uploaded = files.upload()  # choose maubin_flood_event_dataset_v1.csv
```

Or from Drive:

```python
from google.colab import drive
drive.mount("/content/drive")
# then set DATASET to your Drive path
```

## 5) Run comparison

```python
from pathlib import Path
from scripts.compare_flood_event_models import run_comparison

DATASET = Path("/content/maubin_flood_event_dataset_v1.csv")
OUTPUT = Path("/content/maubin_flood_event_model_comparison.json")

report = run_comparison(
    dataset=DATASET,
    output=OUTPUT,
    include_xgboost=True,  # requires xgboost install
    minimum_screening_precision=0.10,
    minimum_conservative_recall=0.20,
)

print(report["winner"])
for name, model in report["models"].items():
    best = model["best_test"]
    print(
        name,
        "mode=", model["best_test_mode"],
        "precision=", best["precision"],
        "recall=", best["recall"],
        "f1=", best["f1"],
    )
```

Expected runtime on Colab CPU: roughly **5–20 minutes** (RF + HGB + XGB).

## 6) Download the report

```python
from google.colab import files
files.download("/content/maubin_flood_event_model_comparison.json")
```

Save locally as:

```
backend/artifacts/maubin_flood_event_model_comparison.json
```

## 7) Results ingested (2026-08-12)

Artifact present at `backend/artifacts/maubin_flood_event_model_comparison.json`.

| Algorithm | Best P | Notes |
|---|---:|---|
| random_forest | 0.108 | Suite winner vs sklearn logistic |
| logistic_sklearn | 0.093 | Same flood_excess CSV |
| xgboost | 0.072 | No gain |
| hist_gradient_boosting | 0.068 | No gain |

**Decision:** no inference swap (still below v5 12.9% and baseline 16.6%).

## Local (optional, no Colab)

```powershell
cd D:\geo-ai-floating-predection\backend
uv pip install -r requirements-ml.txt
uv run python -m scripts.compare_flood_event_models --include-xgboost
```

## Notes

- Uses CSV `temporal_split` + `target_label` (your flood_excess export).
- Does **not** write to Postgres by itself.
- `hist_gradient_boosting` is the sklearn stand-in; `--include-xgboost` adds real XGBoost.
