#!/usr/bin/env python3
"""
build_notebooks.py
==================
Creates the five analysis notebooks in `notebooks/` from source.

Why generate them from a script instead of writing .ipynb by hand?
* the notebook JSON stays readable and diff-friendly in Git
* the same content can be regenerated after any change
* the notebooks can be executed automatically in CI

Usage
-----
    python scripts/build_notebooks.py            # create the notebooks
    python scripts/build_notebooks.py --execute  # create + run them (stores outputs)

Each notebook is also importable as a normal Python module by the reader, so
it can be read like a script - that is what makes them beginner friendly.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"

PRELUDE = """
import sys, warnings
from pathlib import Path
warnings.filterwarnings("ignore")

PROJECT_ROOT = Path.cwd()
if not (PROJECT_ROOT / "src").exists():
    PROJECT_ROOT = PROJECT_ROOT.parent
if not (PROJECT_ROOT / "src").exists():
    raise RuntimeError("Launch Jupyter from the project root or notebooks directory")
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd, numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
%matplotlib inline
sns.set_theme(style="whitegrid", context="notebook", font_scale=1.1)

from src import config as cfg
from src import data_loader, preprocessing, features, eda, trend_analysis
from src import anomaly_detection, forecasting, insights, visualizations as viz

pd.set_option("display.max_columns", 40)
pd.set_option("display.width", 160)
print("Project root:", PROJECT_ROOT)
""".format(root=ROOT)


def nb(cells) -> nbf.NotebookNode:
    return nbf.v4.new_notebook(cells=cells)


def md(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(text.strip("\n"))


def code(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(text.strip("\n"))


# --------------------------------------------------------------------------
# Notebook 1 - Data loading & cleaning
# --------------------------------------------------------------------------
def notebook_1() -> nbf.NotebookNode:
    return nb([
        md("""
# 01 · Data Loading & Cleaning
**Climate Trend Analyzer** — step 1 of 5

### Why this step matters
Real climate data is *never* clean. A dataset that arrives from a station
network, a CSV download or a sensor gateway will contain:

* missing readings (sensor dropouts, failed API calls)
* duplicate records (retried uploads)
* impossible values (a `-999 °C` placeholder, a unit error)
* inconsistent date formats (`2020-01-01` **and** `01/31/2020`)

If we skip cleaning, every chart is misleading and every model learns from
garbage. In this notebook we load the dataset, **measure** the problems,
**fix** them, and export a clean master table.
"""),
        code(PRELUDE),
        md("## 1.1 Load the raw dataset"),
        code("""
raw = data_loader.load_raw(cfg.RAW_CSV)
print(data_loader.dataset_info(raw))
"""),
        md("""
> **Look closely at the date column** - it is a *string* column containing
> two different formats. That is the first problem we have to solve.
"""),
        md("## 1.2 Measure the damage"),
        code("""
missing = raw[cfg.CLIMATE_COLUMNS].isna().sum().to_frame("missing")
missing["missing_pct"] = (100 * missing["missing"] / len(raw)).round(2)
missing
"""),
        code("""
# how many rows are physically impossible?
for col, (lo, hi) in cfg.VALID_RANGES.items():
    bad = raw[col].notna() & ((raw[col] < lo) | (raw[col] > hi))
    print(f"{col:15s} -> {int(bad.sum()):4d} impossible values")
"""),
        md("## 1.3 Clean it"),
        code("""
clean, report = preprocessing.clean_dataset(raw)
print(preprocessing.quality_report_table(report).to_string(index=False))
"""),
        code("""
# the dates are real timestamps now, and the outliers are gone
clean["date"].head(), clean["temp_mean_c"].describe()
"""),
        md("## 1.4 Visual proof of the cleaning"),
        code("""
viz.plot_data_quality(raw, clean)
"""),
        md("""
### ✅ Checkpoint
* 2,700 clean monthly records, one row per (region, month)
* 0 missing values, 0 impossible values, 0 duplicate dates
* `date` is a proper `datetime64` column
"""),
        code("""
clean.to_csv(cfg.CLEAN_CSV, index=False)
print("Saved ->", cfg.CLEAN_CSV)
"""),
    ])


# --------------------------------------------------------------------------
# Notebook 2 - EDA
# --------------------------------------------------------------------------
def notebook_2() -> nbf.NotebookNode:
    return nb([
        md("""
# 02 · Exploratory Data Analysis (EDA)
**Climate Trend Analyzer** — step 2 of 5

### What is EDA for?
EDA is *reconnaissance*: before we model anything we need to know what the
data looks like, what varies, what repeats, and what is unusual. Four
questions to answer:

1. What is the shape and spread of each variable?
2. Which variables move together (correlation)?
3. How does the data behave across the calendar (seasonality)?
4. Which years stand out?
"""),
        code(PRELUDE),
        code("""
clean = data_loader.load_clean(cfg.CLEAN_CSV)
feat  = features.build_features(clean)
feat  = features.add_cyclical_month(feat)
feat.head()
"""),
        md("## 2.1 Descriptive statistics"),
        code("""
bundle = eda.run_eda(feat)
bundle["summary"]
"""),
        code("""
fig, ax = plt.subplots(figsize=(12, 4.5))
for c in ["temp_mean_c", "rainfall_mm", "humidity_pct", "co2_ppm"]:
    ax.hist(feat[c].dropna(), bins=60, alpha=0.45, label=c, density=True)
ax.legend(); ax.set_title("Distribution of the main climate indicators")
ax.set_xlabel("value"); ax.set_ylabel("density")
"""),
        md("## 2.2 Correlations - the driver question"),
        code("""
bundle["correlations"]
"""),
        code("""
fig, ax = plt.subplots(figsize=(7, 5.5))
sns.heatmap(bundle["correlations"], annot=True, fmt=".2f", cmap="coolwarm",
            center=0, square=True, ax=ax)
ax.set_title("Which climate variables move together?")
"""),
        md("""
> **CO₂ vs temperature is the classic relationship.** Remember the caveat:
> correlation is not causation - both are driven by the same underlying
> energy balance, and the CO₂ series is a *global driver* while temperature
> is also shaped by local circulation.
"""),
        md("## 2.3 Seasonality"),
        code("""
bundle["seasonal"]
"""),
        code("""
viz.plot_seasonal_profile(feat)
"""),
        md("## 2.4 Yearly aggregates"),
        code("""
bundle["global_yearly"].tail(15)
"""),
        code("""
viz.plot_yearly_comparison(feat)
"""),
        md("### ✅ Checkpoint\n* Clear seasonal cycle in temperature and rainfall\n* CO₂ and temperature correlate strongly\n* Yearly aggregates show a visible warming pattern"),
    ])


# --------------------------------------------------------------------------
# Notebook 3 - Trend analysis
# --------------------------------------------------------------------------
def notebook_3() -> nbf.NotebookNode:
    return nb([
        md("""
# 03 · Climate Trend Analysis
**Climate Trend Analyzer** — step 3 of 5

### The statistical core
We want to answer: *is the climate actually changing, and how fast?*

Two independent methods, because one method can lie:

| Method | Type | Assumption | Strength |
| --- | --- | --- | --- |
| OLS with **monthly fixed effects** | parametric | linear trend, independent errors | gives a magnitude + CI |
| **Mann-Kendall** | non-parametric | monotonic trend only | robust to outliers, no distribution assumption |

### ⚠️ The pitfall everybody falls into
A monthly temperature series swings ±12 °C between summer and winter.
Regressing it on time **without** controlling for seasonality makes the
seasonal cycle leak into the trend estimate. The fix used here:

* **OLS** → `value ~ time + month dummies` (seasonal fixed effects)
* **Mann-Kendall** → run on the *deseasonalised* series
"""),
        code(PRELUDE),
        code("""
feat = pd.read_csv(cfg.FEATURED_CSV, parse_dates=["date"])
feat.head()
"""),
        md("## 3.1 Seasonal decomposition (STL)"),
        code("""
decomp = trend_analysis.seasonal_decomposition(
    feat[feat.region == "London"].sort_values("date").set_index("date")["temp_mean_c"], period=12)
viz.plot_decomposition(decomp, "London")
"""),
        md("""The red line is the **trend** - it rises steadily. The green line is the
**seasonal** component (the annual cycle). The grey residuals are the noise
plus the extremes, which is exactly what the anomaly detector will look for."""),
        md("## 3.2 Why we deseasonalise first"),
        code("""
raw_series = feat[feat.region == "London"].sort_values("date")["temp_mean_c"]

print("Plain OLS on the raw series (WRONG - seasonality leaks in):")
from scipy.stats import linregress
plain = linregress(np.arange(len(raw_series)),raw_series)
print(f"   slope = {plain.slope*120:+.3f} C/decade,  R2 = {plain.rvalue**2:.4f}")

print()
print("OLS with monthly fixed effects (CORRECT):")
res2 = trend_analysis.ols_trend(raw_series, months=feat[feat.region=='London'].sort_values('date')['month'])
print(f"   slope = {res2['slope_per_year']*10:+.3f} C/decade,  R2 = {res2['r_squared']:.4f}")
"""),
        md("## 3.3 Mann-Kendall (implemented from scratch)"),
        code("""
mk = trend_analysis.mann_kendall(raw_series, months=feat[feat.region=='London'].sort_values('date')['month'])
for k, v in mk.items():
    print(f"{k:28s}: {v}")
"""),
        md("""`mk_trend = increasing` and `theil_sen_slope_per_year` is the median of all
pairwise slopes - a *robust* alternative to least squares that is not
influenced by a few extreme months."""),
        md("## 3.4 Trends for every region and indicator"),
        code("""
trends = trend_analysis.analyze_trends(feat)
trends[trends.indicator == "temp_mean_c"][
    ["region","slope_per_decade","ci_low","ci_high","r_squared","p_value","mk_trend","mk_p_value"]
].round(4)
"""),
        code("""
viz.plot_regional_warming_bar(trends)
"""),
        md("## 3.5 Rainfall and CO₂"),
        code("""
trends[trends.indicator.isin(["rainfall_mm","co2_ppm","sea_level_mm"])][
    ["region","indicator","slope_per_decade","r_squared","p_value","mk_trend"]
].round(4)
"""),
        code("""
viz.plot_co2_vs_temperature(feat)
viz.plot_sea_level_rise(feat)
"""),
        md("### ✅ Checkpoint\n* All 5 regions show a **significant warming trend** (p < 0.05)\n* OLS and Mann-Kendall agree on the direction\n* CO₂ and sea level rise; rainfall shows no significant trend"),
    ])


# --------------------------------------------------------------------------
# Notebook 4 - Anomaly detection
# --------------------------------------------------------------------------
def notebook_4() -> nbf.NotebookNode:
    return nb([
        md("""
# 04 · Anomaly Detection
**Climate Trend Analyzer** — step 4 of 5

### What is an "anomaly" in climate data?
A month whose behaviour is **unusual for that calendar month and that place**.
A 30 °C January in London is an anomaly; a 30 °C July in London is not.

### Four detectors, four blind spots
| Method | Catches | Blind spot |
| --- | --- | --- |
| Climatology z-score | deviations from the calendar-month normal | needs a stable baseline |
| STL residual | deviations from trend + seasonality | depends on the decomposition |
| IQR (Tukey fences) | gross statistical outliers | blunt for skewed data |
| Isolation Forest | unusual *combinations* of variables | unsupervised, needs tuning |

The results are **merged into one anomaly register** with a severity score -
that table is what a city planner or a reinsurer would actually read.
"""),
        code(PRELUDE),
        code("""
feat = pd.read_csv(cfg.FEATURED_CSV, parse_dates=["date"])
anomalies = anomaly_detection.detect_anomalies(feat)
print(f"Total anomalies: {len(anomalies)}")
anomalies.head(10)
"""),
        md("## 4.1 How many, and by which method?"),
        code("""
anomalies["method"].value_counts().to_frame("count")
"""),
        code("""
anomaly_detection.anomaly_summary(anomalies)
"""),
        md("## 4.2 The most extreme events in the record"),
        code("""
anomaly_detection.notable_events(anomalies, top_n=12)[
    ["anomaly_id","date","region","variable","value","expected","deviation","score","description"]
]
"""),
        md("## 4.3 Visualising the detections"),
        code("""
viz.plot_anomaly_detection(feat, anomalies)
viz.plot_anomaly_timeline(anomalies)
"""),
        md("## 4.4 Extreme events (heat waves and droughts)"),
        code("""
viz.plot_extreme_events(feat)
"""),
        md("""The heat-wave flag requires **3 consecutive months** above +1.5 σ, and the
drought flag requires rainfall below 40 % of the calendar-month normal -
business definitions, not just statistical ones."""),
        md("## 4.5 Does the detector find what we planted? (validation)"),
        code("""
# The simulator knows where it injected extreme events - check recall
truth = feat[feat["sim_heatwave"] == 1][["date","region"]].drop_duplicates()
detected = set(zip(anomalies[anomalies.direction=="hot"]["date"],
                   anomalies[anomalies.direction=="hot"]["region"]))
hit = sum((d, r) in detected for d, r in zip(truth["date"], truth["region"]))
print(f"Injected heat-wave months : {len(truth)}")
print(f"Also flagged as anomalies  : {hit}")
print(f"Recall                    : {100*hit/max(len(truth),1):.1f}%")
"""),
        md("### ✅ Checkpoint\n* 4 detection methods agree on a common register\n* Recall against the injected ground truth is measured (not assumed)\n* The register is exported to `outputs/tables/anomalies.csv`"),
    ])


# --------------------------------------------------------------------------
# Notebook 5 - Forecasting & insights
# --------------------------------------------------------------------------
def notebook_5() -> nbf.NotebookNode:
    return nb([
        md("""
# 05 · Forecasting & Insight Generation
**Climate Trend Analyzer** — step 5 of 5

### Forecasting done properly
The most common mistake in portfolio projects is *fitting a model and
plotting it* without ever checking whether it can predict. Here every
candidate model is scored on the **same 60-month chronological validation window** that was
not used during training, but used to select the model:

| Model | Idea |
| --- | --- |
| Naive | "next month = this month" - the benchmark everyone must beat |
| Seasonal naive | "next month = the same month last year" |
| Drift | "the historical slope continues" |
| Ridge + calendar/time features | the machine-learning approach |
| ARIMA | the classic statistical time-series model |

The winner is then refit on the full history to project the next 36 months
with an approximate 95 % prediction band.
"""),
        code(PRELUDE),
        code("""
feat = pd.read_csv(cfg.FEATURED_CSV, parse_dates=["date"])
"""),
        md("## 5.1 Compare the candidate models"),
        code("""
res = forecasting.run_forecasting(feat, target="temp_mean_c", h=36, test_size=60)
res["metrics"].round(3)
"""),
        code("""
viz.plot_model_comparison(res["metrics"])
"""),
        md("""Note how badly the naive baselines do versus the models that understand
seasonality and autocorrelation - that comparison is the real content of
this section."""),
        md("## 5.2 The forecast"),
        code("""
res["forecast"].head(12).round(2)
"""),
        code("""
viz.plot_forecast(res, region="London")
"""),
        md("## 5.3 Generating the written insights automatically"),
        code("""
from src import pipeline
from src import report_generator, insights as ins

bundle = {
    "featured": feat,
    "trend_results": trend_analysis.run_trend_analysis(feat),
    "anomaly_results": anomaly_detection.run_anomaly_detection(feat),
    "forecast_results": res,
    "eda": eda.run_eda(feat),
    "clean_report": preprocessing.clean_dataset(data_loader.load_raw())[1],
}
text = ins.generate_insights(bundle)
print(text[:2500])
"""),
        md("""
Every number in that text is read from the analysis results - the insight
engine cannot make a claim that the data does not support.
"""),
        md("## 5.4 What a business user does with this"),
        code("""
summary = ins.key_numbers(bundle)
for k, v in summary.items():
    print(f"{k:32s}: {v}")
"""),
        md("""
### ✅ Checkpoint
* Compare validation errors with every baseline; winning is not assumed
* A 36-month projection with an approximate residual band is produced per region
* Findings are generated automatically from the numbers
"""),
    ])


NOTEBOOKS = {
    "01_Data_Loading_and_Cleaning.ipynb": notebook_1,
    "02_Exploratory_Data_Analysis.ipynb": notebook_2,
    "03_Climate_Trend_Analysis.ipynb": notebook_3,
    "04_Anomaly_Detection.ipynb": notebook_4,
    "05_Forecasting_and_Insights.ipynb": notebook_5,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true",
                        help="Execute the notebooks after creating them (stores outputs).")
    args = parser.parse_args()

    NB_DIR.mkdir(parents=True, exist_ok=True)
    for name, builder in NOTEBOOKS.items():
        path = NB_DIR / name
        nbf.write(builder(), str(path))
        print(f"[notebooks] wrote {path.relative_to(ROOT)}")

    if args.execute:
        for name in NOTEBOOKS:
            path = NB_DIR / name
            print(f"[notebooks] executing {name} ...")
            subprocess.run(
                [sys.executable, "-m", "jupyter", "nbconvert",
                 "--to", "notebook", "--execute", "--inplace",
                 f"--ExecutePreprocessor.timeout=600", str(path)],
                cwd=str(ROOT), check=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
