# Full implementation — Climate Trend Analyzer

Every file below also exists as a runnable file in the repository. No placeholders replace analytical code. Filenames are relative to the project root. Notebook JSON is not pasted here: all five executed .ipynb files are included, and the complete builder below reproduces them.


## `main.py`

```python
#!/usr/bin/env python3
"""
main.py
=======
**Command-line entry point** for the Climate Trend Analyzer.

Examples
--------
    python main.py                      # run the complete pipeline
    python main.py --step all           # same, explicitly
    python main.py --step clean         # only clean the data
    python main.py --no-forecast        # skip the (slow) forecasting stage
    python main.py --regenerate         # rebuild the simulated raw dataset
    python main.py --summary            # print the headline numbers only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# make `src` importable when the script is run from any directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import config as cfg  # noqa: E402
from src import pipeline  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="Climate Trend Analyzer",
        description="Analyse climate time series: trends, anomalies and forecasts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--step",
        default="all",
        choices=["all", "simulate", "clean", "features", "eda", "trends",
                 "anomalies", "forecast", "visualize", "report", "summary"],
        help="Run a single stage instead of the whole pipeline (default: all).",
    )
    p.add_argument(
        "--regenerate",
        action="store_true",
        help="Force regeneration of the simulated raw dataset.",
    )
    p.add_argument(
        "--no-forecast",
        action="store_true",
        help="Skip the forecasting stage (faster, useful for a quick demo).",
    )
    p.add_argument(
        "--summary",
        action="store_true",
        help="Print the headline numbers from the last run and exit.",
    )
    return p


def print_summary() -> None:
    import json

    if cfg.RUN_SUMMARY_JSON.exists():
        data = json.loads(cfg.RUN_SUMMARY_JSON.read_text())
        print("=" * 62)
        print("CLIMATE TREND ANALYZER - LAST RUN SUMMARY")
        print("=" * 62)
        for k, v in data.items():
            if k in ("figures", "key_numbers"):
                continue
            print(f"{k:22s}: {v}")
        print("-" * 62)
        for k, v in data.get("key_numbers", {}).items():
            print(f"{k:22s}: {v}")
    else:
        print("No run summary found - execute `python main.py` first.")


def main() -> int:
    args = build_parser().parse_args()

    if args.summary or args.step == "summary":
        print_summary()
        return 0

    # ------------------------------------------------------------------
    # FULL PIPELINE (the default and the recommended way to run it)
    # ------------------------------------------------------------------
    if args.step == "all":
        bundle = pipeline.run_pipeline(
            do_forecast=not args.no_forecast,
            force_simulate=args.regenerate,
        )
        numbers = bundle["key_numbers"]
        print("\nHEADLINE NUMBERS")
        for k, v in numbers.items():
            print(f"  {k:32s}: {v}")
        return 0

    # ------------------------------------------------------------------
    # SINGLE STAGES (useful while learning / debugging)
    # ------------------------------------------------------------------
    if args.step == "simulate":
        pipeline.stage_simulate(force=args.regenerate)
        return 0

    if args.step == "clean":
        pipeline.stage_clean()
        return 0

    if args.step == "features":
        pipeline.stage_features()
        return 0

    # from here on we need the featured dataset
    from src import data_loader

    featured = data_loader.load_featured(cfg.FEATURED_CSV)

    if args.step == "eda":
        pipeline.stage_eda(featured)
        return 0

    if args.step == "trends":
        pipeline.stage_trends(featured)
        return 0

    if args.step == "anomalies":
        pipeline.stage_anomalies(featured)
        return 0

    if args.step == "forecast":
        pipeline.stage_forecast(featured, do_forecast=not args.no_forecast)
        return 0

    if args.step in ("visualize", "report"):
        raw = data_loader.load_raw(cfg.RAW_CSV)
        bundle = {
            "raw": raw,
            "clean": data_loader.load_clean(cfg.CLEAN_CSV),
            "featured": featured,
            "clean_report": pipeline.preprocessing.clean_dataset(raw)[1],
            "eda": pipeline.eda_mod.run_eda(featured),
            "trend_results": pipeline.trend_analysis.run_trend_analysis(featured),
            "anomaly_results": pipeline.anomaly_detection.run_anomaly_detection(featured),
            "forecast_results": (
                pipeline.fc_mod.run_forecasting(featured)
                if not args.no_forecast
                else {"metrics": pd.DataFrame(), "forecast": pd.DataFrame(), "results": []}
            ),
        }
        bundle["figures"] = pipeline.stage_visualize(bundle)
        pipeline.stage_insights(bundle)
        pipeline.stage_report(bundle)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

**What this file does:** Command-line runner: full workflow or an individual named stage.


## `src/__init__.py`

```python
"""
Climate Trend Analyzer - source package
========================================
Modules
-------
config              : paths, thresholds, simulation parameters
data_generator      : virtual simulation of the climate collection system
data_loader         : dataset access layer
preprocessing       : cleaning & quality control
features            : feature engineering
eda                 : exploratory data analysis
trend_analysis      : OLS + Mann-Kendall trend statistics
anomaly_detection   : z-score / STL / IQR / Isolation Forest anomalies
forecasting         : baseline, ML and ARIMA forecasting
visualizations      : every figure used in the report
insights            : automatic natural-language insights
report_generator    : Markdown + HTML report builders
pipeline            : end-to-end orchestration
"""

__version__ = "1.0.0"
__all__ = [
    "config",
    "data_generator",
    "data_loader",
    "preprocessing",
    "features",
    "eda",
    "trend_analysis",
    "anomaly_detection",
    "forecasting",
    "visualizations",
    "insights",
    "report_generator",
    "pipeline",
]

```

**What this file does:** Project configuration, installation or recruiter-facing documentation. See the corresponding section in PROJECT_GUIDE.md.


## `src/anomaly_detection.py`

```python
"""
anomaly_detection.py
=====================
**Detecting unusual climate events** with four complementary techniques.

Why multiple techniques?
------------------------
Each method has a different blind spot, and using several is what a real
climate-analytics team does:

| Method                  | What it catches                          | Blind spot                    |
|-------------------------|------------------------------------------|-------------------------------|
| Climatology z-score     | months far from their own seasonal normal | needs a stable baseline       |
| STL residual            | deviations from trend+seasonality        | sensitive to the model choice |
| IQR (Tukey fences)     | gross statistical outliers                | blunt for skewed data         |
| Isolation Forest        | *multivariate* unusual combinations      | unsupervised, needs tuning     |

The four results are **merged into a single anomaly register** with a
severity score - that table is one of the most valuable outputs of the
project (it is what a city planner would actually read).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as cfg


# --------------------------------------------------------------------------
# 1. Climatology z-score anomalies
# --------------------------------------------------------------------------
def zscore_anomalies(
    df: pd.DataFrame,
    threshold: float = cfg.ANOMALY_Z_THRESHOLD,
) -> pd.DataFrame:
    """
    Flag months whose value deviates from the *calendar-month* normal by
    more than `threshold` standard deviations.

    Because the baseline is month-specific, a 30 °C July in Hyderabad is
    NOT an anomaly while a 30 °C January would be.
    """
    rows = []
    for region, grp in df.groupby("region"):
        grp = grp.sort_values("date")
        for _, r in grp.iterrows():
            z = r["temp_anomaly_z"]
            if pd.notna(z) and abs(z) >= threshold:
                direction = "hot" if z > 0 else "cold"
                rows.append(
                    {
                        "date": r["date"],
                        "region": region,
                        "variable": "temp_mean_c",
                        "method": "climatology_zscore",
                        "value": round(float(r["temp_mean_c"]), 2),
                        "expected": round(float(r["temp_clim"]), 2),
                        "deviation": round(float(r["temp_anomaly"]), 2),
                        "score": round(float(z), 3),
                        "severity": "high" if abs(z) >= threshold + 1 else "moderate",
                        "direction": direction,
                        "description": (
                            f"{direction.capitalize()} anomaly: {r['temp_mean_c']:.1f}°C vs "
                            f"normal {r['temp_clim']:.1f}°C ({z:+.1f}σ)"
                        ),
                    }
                )

        # rainfall anomalies (dry / wet) - same z-score logic, applied to the
        # calendar-month rainfall normal so seasonality does not create noise
        for _, r in grp.iterrows():
            z = r.get("rain_anomaly_z", np.nan)
            if pd.notna(z) and abs(z) >= threshold:
                direction = "drought" if z < 0 else "wet"
                rows.append(
                    {
                        "date": r["date"],
                        "region": region,
                        "variable": "rainfall_mm",
                        "method": "climatology_zscore",
                        "value": round(float(r["rainfall_mm"]), 1),
                        "expected": round(float(r["rain_normal"]), 1),
                        "deviation": round(float(r["rain_anomaly_pct"]), 1),
                        "score": round(float(z), 3),
                        "severity": "high" if abs(z) >= threshold + 1 else "moderate",
                        "direction": direction,
                        "description": (
                            f"{direction.capitalize()}: {r['rainfall_mm']:.0f} mm vs normal "
                            f"{r['rain_normal']:.0f} mm ({r['rain_pct_of_normal']:.0f}% of normal, {z:+.1f}σ)"
                        ),
                    }
                )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 2. STL residual anomalies
# --------------------------------------------------------------------------
def stl_anomalies(
    df: pd.DataFrame,
    threshold: float = cfg.ANOMALY_STL_THRESHOLD,
) -> pd.DataFrame:
    """
    Flag months whose residual (after removing trend + seasonality) is
    beyond `threshold` sigma of the residual distribution.
    """
    rows = []
    for region, grp in df.groupby("region"):
        grp = grp.sort_values("date").reset_index(drop=True)
        from .trend_analysis import seasonal_decomposition

        decomp = seasonal_decomposition(grp["temp_mean_c"], period=12)
        sigma = decomp["resid"].std()
        for i, r in grp.iterrows():
            resid = decomp.loc[i, "resid"]
            z = resid / sigma if sigma else np.nan
            if pd.notna(z) and abs(z) >= threshold:
                rows.append(
                    {
                        "date": r["date"],
                        "region": region,
                        "variable": "temp_mean_c",
                        "method": "stl_residual",
                        "value": round(float(r["temp_mean_c"]), 2),
                        "expected": round(float(r["temp_mean_c"] - resid), 2),
                        "deviation": round(float(resid), 2),
                        "score": round(float(z), 3),
                        "severity": "high" if abs(z) >= threshold + 1 else "moderate",
                        "direction": "hot" if resid > 0 else "cold",
                        "description": (
                            f"Unexpected {r['temp_mean_c']:.1f}°C month: residual {resid:+.1f}°C ({z:+.1f}σ)"
                        ),
                    }
                )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 3. IQR (Tukey fence) outliers
# --------------------------------------------------------------------------
def iqr_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classic box-plot outliers: below Q1-1.5*IQR or above Q3+1.5*IQR.

    Applied to temperature and humidity only - rainfall is already covered by
    the (seasonality-aware) z-score detector above.
    """
    rows = []
    for region, grp in df.groupby("region"):
        for ind in ("temp_mean_c", "humidity_pct"):
            s = grp[ind].dropna()
            if len(s) < 8:
                continue
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            bad = grp[(grp[ind] < lo) | (grp[ind] > hi)]
            for _, r in bad.iterrows():
                rows.append(
                    {
                        "date": r["date"],
                        "region": region,
                        "variable": ind,
                        "method": "iqr",
                        "value": round(float(r[ind]), 2),
                        "expected": round(float(grp[ind].median()), 2),
                        "deviation": round(float(r[ind] - grp[ind].median()), 2),
                        "score": round(float(abs(r[ind] - grp[ind].median()) / iqr), 3),
                        "severity": "moderate",
                        "direction": "high" if r[ind] > hi else "low",
                        "description": (
                            f"IQR outlier in {ind}: {r[ind]:.1f} (fences {lo:.1f} / {hi:.1f})"
                        ),
                    }
                )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 4. Isolation Forest (multivariate)
# --------------------------------------------------------------------------
def isolation_forest_anomalies(
    df: pd.DataFrame,
    contamination: float = cfg.ISOLATION_CONTAMINATION,
) -> pd.DataFrame:
    """
    Unsupervised multivariate anomaly detection.

    Isolation Forest isolates points that are "easy to separate" - the
    classic algorithm for this task.  We feed it temperature, rainfall and
    humidity *anomalies* (not raw values) so that the seasonal cycle does
    not dominate the geometry.
    """
    from sklearn.ensemble import IsolationForest

    feats = ["temp_anomaly_z", "rain_anomaly_pct", "humidity_pct"]
    data = df[["region"] + feats].dropna().copy()
    if data.empty:
        return pd.DataFrame()

    X = data[feats].to_numpy()
    model = IsolationForest(
        n_estimators=300,
        contamination=contamination,
        random_state=cfg.RANDOM_SEED,
    )
    labels = model.fit_predict(X)
    scores = -model.decision_function(X)  # higher = more anomalous
    data["is_anomaly"] = labels == -1
    data["score"] = scores

    flagged = data[data["is_anomaly"]].copy()
    rows = []
    for idx, r in flagged.iterrows():
        base = df.loc[idx]
        rows.append(
            {
                "date": base["date"],
                "region": base["region"],
                "variable": "multivariate",
                "method": "isolation_forest",
                "value": round(float(base["temp_mean_c"]), 2),
                "expected": round(float(base["temp_clim"]), 2),
                "deviation": round(float(base["temp_anomaly"]), 2),
                "score": round(float(r["score"]), 4),
                "severity": "high" if r["score"] > np.percentile(flagged["score"], 80) else "moderate",
                "direction": "hot" if base["temp_anomaly"] > 0 else "cold",
                "description": (
                    f"Unusual climate state (temp {base['temp_anomaly']:+.1f}°C, "
                    f"rain {base['rain_anomaly_pct']:+.0f}%)"
                ),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Run all four detectors and merge them into one anomaly register."""
    parts = [
        zscore_anomalies(df),
        stl_anomalies(df),
        iqr_outliers(df),
        isolation_forest_anomalies(df),
    ]
    parts = [p for p in parts if not p.empty]
    if not parts:
        return pd.DataFrame(
            columns=["date", "region", "variable", "method", "value", "expected",
                     "deviation", "score", "severity", "direction", "description"]
        )
    merged = pd.concat(parts, ignore_index=True)
    merged = merged.sort_values(["date", "region", "method"]).reset_index(drop=True)

    # a unique anomaly id for tracking
    merged["anomaly_id"] = [
        f"ANM-{i:04d}" for i in range(1, len(merged) + 1)
    ]
    return merged


def anomaly_summary(anomalies: pd.DataFrame) -> pd.DataFrame:
    """Counts of anomalies by region, variable and detection method."""
    if anomalies.empty:
        return pd.DataFrame()
    by_region = (
        anomalies.groupby("region")
        .agg(total=("anomaly_id", "count"),
             high=("severity", lambda s: (s == "high").sum()),
             hot=("direction", lambda s: (s == "hot").sum()),
             cold=("direction", lambda s: (s == "cold").sum()))
        .reset_index()
    )
    return by_region


def notable_events(anomalies: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """The most extreme anomalies in the whole record."""
    if anomalies.empty:
        return pd.DataFrame()
    return anomalies.reindex(anomalies["score"].abs().sort_values(ascending=False).index).head(top_n)


def run_anomaly_detection(df: pd.DataFrame) -> dict:
    """Full anomaly detection bundle."""
    anomalies = detect_anomalies(df)
    return {
        "anomalies": anomalies,
        "summary": anomaly_summary(anomalies),
        "notable": notable_events(anomalies),
        "counts_by_method": (
            anomalies["method"].value_counts().rename_axis("method").reset_index(name="count")
            if not anomalies.empty else pd.DataFrame()
        ),
    }


if __name__ == "__main__":
    from .data_loader import load_featured

    res = run_anomaly_detection(load_featured())
    print(f"Total anomalies detected: {len(res['anomalies'])}")
    print(res["summary"].to_string(index=False))

```

**What this file does:** Four complementary detectors; register rows are method flags, not unique events.


## `src/config.py`

```python
"""
config.py
=========
Central configuration for the **Climate Trend Analyzer** project.

Every path, constant, threshold and simulation parameter used anywhere in the
pipeline lives here.  This is a professional habit: change a number in ONE
place and the whole project follows.

Beginner note
-------------
Think of this file as the "settings page" of the application.  Nothing in
`config.py` performs analysis - it only *describes* how the analysis should
be performed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# 1. PATHS  (all paths are resolved relative to the project root)
# --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SYNTHETIC_DIR = DATA_DIR / "synthetic"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"
TABLES_DIR = OUTPUTS_DIR / "tables"
REPORTS_DIR = OUTPUTS_DIR / "reports"

MODELS_DIR = PROJECT_ROOT / "models"
IMAGES_DIR = PROJECT_ROOT / "images"
DOCS_DIR = PROJECT_ROOT / "docs"

for _d in (
    DATA_DIR, RAW_DIR, PROCESSED_DIR, SYNTHETIC_DIR,
    OUTPUTS_DIR, FIGURES_DIR, TABLES_DIR, REPORTS_DIR,
    MODELS_DIR, IMAGES_DIR, DOCS_DIR,
):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# 2. KEY FILE NAMES
# --------------------------------------------------------------------------
RAW_CSV = RAW_DIR / "climate_raw.csv"                  # messy, "as collected"
CLEAN_CSV = PROCESSED_DIR / "climate_clean.csv"        # cleaned master table
FEATURED_CSV = PROCESSED_DIR / "climate_featured.csv"  # + engineered features
ANOMALY_CSV = TABLES_DIR / "anomalies.csv"             # detected anomalies
TREND_CSV = TABLES_DIR / "trend_summary.csv"           # trend statistics
FORECAST_CSV = TABLES_DIR / "forecast_next_36m.csv"    # future projections
METRICS_CSV = TABLES_DIR / "model_metrics.csv"         # model comparison
YEARLY_CSV = TABLES_DIR / "yearly_summary.csv"         # annual aggregates
CORR_CSV = TABLES_DIR / "correlation_matrix.csv"
RUN_SUMMARY_JSON = OUTPUTS_DIR / "run_summary.json"

# --------------------------------------------------------------------------
# 3. SIMULATION PARAMETERS  (the "virtual simulation" settings)
# --------------------------------------------------------------------------
RANDOM_SEED = 42
START_DATE = "1980-01-01"
END_DATE = "2024-12-01"

#: Region metadata used by the simulator AND by the report.
#: `warming_slope` = °C per year (long term trend),
#: `seasonal_amp`  = °C difference between the hottest and coldest month,
#: `peak_month`    = calendar month with the highest temperature (1-12).
REGIONS = [
    # name,          country,      lat,    lon,   base_temp, amp, peak, slope, rain_base, humid
    ("Hyderabad",    "India",       17.4,  78.5,  27.5, 5.5,  4, 0.022,  75.0, 62.0),
    ("London",       "UnitedKingdom", 51.5, -0.12, 11.0, 7.5,  7, 0.028,  58.0, 74.0),
    ("New York",     "USA",         40.7, -74.0, 13.0, 12.0, 7, 0.026,  95.0, 64.0),
    ("Singapore",    "Singapore",    1.35, 103.8, 27.8, 1.6,  3, 0.020, 190.0, 82.0),
    ("Sydney",       "Australia",  -33.9, 151.2, 18.2, 6.0,  1, 0.024, 120.0, 66.0),
]
REGION_NAMES = [r[0] for r in REGIONS]

#: How much "dirty" the simulated raw data is (fractions of rows).
MISSING_RATE = 0.015          # 1.5 % random missing values
DUPLICATE_ROWS = 15           # exact duplicate records
OUTLIER_COUNT = 12            # impossible values (e.g. -999 °C)
MIXED_DATE_FORMAT_RATE = 0.10  # 10 % of dates written as MM/DD/YYYY

# --------------------------------------------------------------------------
# 4. ANALYSIS PARAMETERS
# --------------------------------------------------------------------------
ROLLING_WINDOW = 12            # months (1 year) for smoothing
CLIMATOLOGY_BASELINE = "full"  # "full" = whole record, "train" = first 80 %
ANOMALY_Z_THRESHOLD = 2.5      # |z| above this -> anomaly
ANOMALY_STL_THRESHOLD = 2.0    # |STL residual| in sigmas -> anomaly
ISOLATION_CONTAMINATION = 0.02  # expected share of multivariate anomalies
FORECAST_HORIZON = 36          # months to forecast
TEST_SIZE = 60                 # months held out for model evaluation
ARIMA_MAX_P = 2
ARIMA_MAX_Q = 2

#: Columns that are numeric climate indicators
CLIMATE_COLUMNS = [
    "temp_mean_c",
    "temp_min_c",
    "temp_max_c",
    "rainfall_mm",
    "humidity_pct",
    "co2_ppm",
    "sea_level_mm",
]

#: Physically impossible bounds used by the cleaning module.
VALID_RANGES = {
    "temp_mean_c": (-60.0, 60.0),
    "temp_min_c": (-70.0, 60.0),
    "temp_max_c": (-60.0, 80.0),
    "rainfall_mm": (0.0, 2000.0),
    "humidity_pct": (0.0, 100.0),
    "co2_ppm": (250.0, 700.0),
    "sea_level_mm": (-200.0, 1000.0),
}

# --------------------------------------------------------------------------
# 5. RUNTIME HELPERS
# --------------------------------------------------------------------------
def _running_in_notebook() -> bool:
    """True when the code is executed inside Jupyter/Colab."""
    return "ipykernel" in sys.modules or "IPython" in sys.modules


def use_headless_backend() -> None:
    """Use the non-interactive 'Agg' matplotlib backend (servers, CI, Colab)."""
    if not _running_in_notebook():
        import matplotlib
        matplotlib.use("Agg")


def describe() -> str:
    """Return a short human readable description of the configuration."""
    return (
        "Climate Trend Analyzer configuration\n"
        f"  project root : {PROJECT_ROOT}\n"
        f"  simulation   : {START_DATE} -> {END_DATE} across {len(REGIONS)} regions\n"
        f"  forecast     : {FORECAST_HORIZON} months\n"
        f"  anomaly z    : {ANOMALY_Z_THRESHOLD}\n"
        f"  random seed  : {RANDOM_SEED}"
    )


if __name__ == "__main__":
    print(describe())

```

**What this file does:** Centralized filesystem paths, thresholds and simulation parameters.


## `src/data_generator.py`

```python
"""
data_generator.py
=================
**Virtual simulation of a climate data collection system.**

This module fabricates a *realistic* monthly climate dataset (1980-2024) for
five regions, so that the whole project can be built, demonstrated
and evaluated **without access to any institutional or government system**.

What is simulated (and why it matters)
--------------------------------------
1. **Seasonal cycle** - a sinusoid whose peak month follows the hemisphere
   (Sydney peaks in January, London in July).  This is what makes the
   "seasonality" analysis meaningful.
2. **Long-term warming trend** - a region specific linear slope
   (0.020 - 0.028 °C / year), i.e. the signal we want to *discover* later
   with OLS / Mann-Kendall tests.
3. **Interannual variability (ENSO-like)** - a slow multi-year oscillation
   that also modulates rainfall (wet years vs. droughts).
4. **AR(1) autocorrelated noise** - weather is not white noise; consecutive
   months are correlated (rho = 0.25).  Models that ignore this will
   under-forecast.
5. **Extreme events** - heat waves (3+ months of high anomaly) and droughts
   (months with < 40 % of normal rainfall).
6. **Global drivers** - atmospheric CO2 concentration (accelerating growth)
   and global mean sea level rise (~3.3 mm / year).
7. **Realistic data-quality problems** - missing values, duplicated rows,
   physically impossible outliers and mixed date formats, so the cleaning
   module has something real to fix.

Everything is driven by a fixed random seed, therefore the project is
**100 % reproducible**: the same numbers appear on every machine.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as cfg

# --------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------
def _ar1_noise(n: int, rho: float, rng: np.random.Generator) -> np.ndarray:
    """Autoregressive (AR1) noise: x[t] = rho * x[t-1] + e[t]."""
    eps = rng.normal(0.0, 1.0, n)
    out = np.zeros(n)
    for i in range(1, n):
        out[i] = rho * out[i - 1] + eps[i]
    return out


def _seasonal_wave(months: np.ndarray, amp: float, peak_month: int) -> np.ndarray:
    """Cosine seasonal cycle peaking at `peak_month` (1-12)."""
    phase = 2.0 * np.pi * (months - peak_month) / 12.0
    return amp * np.cos(phase)


def _simulate_region(
    region: tuple,
    dates: pd.DatetimeIndex,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Simulate one region's full climate record."""
    (
        name, country, lat, lon, base_temp, amp, peak_month,
        slope_c_per_year, rain_base, humid_base,
    ) = region

    n = len(dates)
    years = dates.year.to_numpy()
    months = dates.month.to_numpy()
    t = np.arange(n)

    # --- 1. Seasonal cycle -------------------------------------------------
    seasonal = _seasonal_wave(months, amp, peak_month)

    # --- 2. Long-term linear warming trend --------------------------------
    trend = slope_c_per_year * (years - years.min())

    # --- 3. ENSO-like multi-year oscillation -------------------------------
    enso = 0.85 * np.sin(2.0 * np.pi * t / (12 * 4.3) + rng.uniform(0, 2 * np.pi))
    enso += 0.35 * np.sin(2.0 * np.pi * t / (12 * 2.1) + rng.uniform(0, 2 * np.pi))

    # --- 4. Autocorrelated weather noise ----------------------------------
    noise = 0.9 * _ar1_noise(n, 0.25, rng) + 0.6 * rng.normal(0, 1, n)

    # --- 5. Temperature ----------------------------------------------------
    temp_mean = base_temp + seasonal + trend + enso + noise
    # Explicit synthetic heat-stress injections: three non-overlapping runs.
    # These are monthly stress episodes, not daily WMO-defined heat waves.
    heatwave = np.zeros(n, dtype=int)
    for start in (120, 300, 480):
        heatwave[start:start+3] = 1
    temp_mean = temp_mean + 4.5 * heatwave
    # Southern hemisphere seasons are offset -> slightly different spread
    diurnal_spread = 3.2 + 2.5 * np.cos(2 * np.pi * (months - 6) / 12) ** 2
    temp_max = temp_mean + diurnal_spread + rng.normal(0, 0.6, n)
    temp_min = temp_mean - diurnal_spread - rng.normal(0, 0.6, n)

    # --- 6. Rainfall (gamma distributed, strongly seasonal) -----------------
    # wet-season factor: high where the seasonal cycle is at its minimum
    wet_factor = 1.0 - 0.55 * (seasonal / max(amp, 1e-6))
    if name == "Hyderabad":
        # Approximate monsoon rainfall peak in July, not a calibrated station model.
        wet_factor = 1.0 + 0.75 * np.cos(2*np.pi*(months-7)/12)
    wet_factor = np.clip(wet_factor, 0.25, 1.8)
    # ENSO modulates rainfall: positive ENSO -> wetter, negative -> drought
    wet_factor = wet_factor * (1.0 + 0.28 * enso)
    shape = 1.4
    scale = rain_base * wet_factor / shape
    rainfall = rng.gamma(shape=shape, scale=np.clip(scale, 1.0, None))

    drought = np.zeros(n, dtype=int)
    for start in (180, 360, 504):
        drought[start:start+3] = 1
    rainfall = np.where(drought == 1, rainfall * 0.15, rainfall)

    # --- 7. Humidity (inverse relation with temperature) -------------------
    humidity = humid_base - 1.15 * (temp_mean - base_temp) + rng.normal(0, 3.0, n)
    humidity = np.clip(humidity, 15, 100)

    # --- 8. Global drivers: CO2 and sea level ------------------------------
    co2_global = 338.0 + 2.10 * (years - 1980) + 0.0165 * (years - 1980) ** 2
    co2 = co2_global + 4.0 * (lat / 90.0) + rng.normal(0, 0.8, n)

    sea_level = 1.6 * (years - 1980) + 0.035 * (years - 1980) ** 2
    sea_level = sea_level + rng.normal(0, 1.2, n)

    # `sim_*` are explicit injected-event labels, never model predictors.

    return pd.DataFrame(
        {
            "date": dates,
            "region": name,
            "country": country.replace("UnitedKingdom", "United Kingdom"),
            "latitude": lat,
            "longitude": lon,
            "temp_mean_c": np.round(temp_mean, 2),
            "temp_min_c": np.round(temp_min, 2),
            "temp_max_c": np.round(temp_max, 2),
            "rainfall_mm": np.round(rainfall, 1),
            "humidity_pct": np.round(humidity, 1),
            "co2_ppm": np.round(co2, 2),
            "sea_level_mm": np.round(sea_level, 2),
            "sim_heatwave": heatwave,
            "sim_drought": drought,
        }
    )


def _inject_data_quality_issues(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Make the raw data 'dirty' the way real observational data is dirty."""
    df = df.copy()

    # (a) Missing values -------------------------------------------------
    for col in ("temp_mean_c", "rainfall_mm", "humidity_pct"):
        idx = rng.choice(df.index, size=int(len(df) * cfg.MISSING_RATE), replace=False)
        df.loc[idx, col] = np.nan

    # (b) Duplicate records ------------------------------------------------
    dup = df.sample(n=cfg.DUPLICATE_ROWS, random_state=cfg.RANDOM_SEED)
    df = pd.concat([df, dup], ignore_index=True)

    # (c) Impossible outliers ----------------------------------------------
    out_rows = rng.choice(df.index, size=cfg.OUTLIER_COUNT, replace=False)
    for i, r in enumerate(out_rows):
        df.loc[r, "temp_mean_c"] = -999.0 if i % 2 == 0 else 900.0

    # (d) Mixed date formats (MM/DD/YYYY written as text) -------------------
    df["date"] = df["date"].astype(str)
    n_mixed = int(len(df) * cfg.MIXED_DATE_FORMAT_RATE)
    mixed_idx = rng.choice(df.index, size=n_mixed, replace=False)
    for r in mixed_idx:
        d = pd.to_datetime(df.loc[r, "date"])
        df.loc[r, "date"] = d.strftime("%m/%d/%Y")

    return df


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------
def generate_climate_dataset(seed: int = cfg.RANDOM_SEED) -> pd.DataFrame:
    """Generate the full simulated (and intentionally imperfect) raw dataset."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(cfg.START_DATE, cfg.END_DATE, freq="MS")

    frames = [_simulate_region(r, dates, rng) for r in cfg.REGIONS]
    raw = pd.concat(frames, ignore_index=True)
    raw = raw.sort_values(["region", "date"]).reset_index(drop=True)
    raw = _inject_data_quality_issues(raw, rng)
    return raw


def write_raw_dataset(path=None, seed: int = cfg.RANDOM_SEED) -> pd.DataFrame:
    """Generate the raw dataset and persist it to `data/raw/climate_raw.csv`."""
    path = path or cfg.RAW_CSV
    raw = generate_climate_dataset(seed=seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw.to_csv(path, index=False)
    return raw


def summary(raw: pd.DataFrame) -> dict:
    """Quick facts about the simulated dataset (used by the report)."""
    return {
        "rows": int(len(raw)),
        "regions": int(raw["region"].nunique()),
        "date_min": str(raw["date"].min()),
        "date_max": str(raw["date"].max()),
        "columns": list(raw.columns),
    }


if __name__ == "__main__":
    raw = write_raw_dataset()
    print("Simulated raw climate dataset written to:", cfg.RAW_CSV)
    print(summary(raw))

```

**What this file does:** Reproducible synthetic measurement system, explicit injected episodes and dirty data.


## `src/data_loader.py`

```python
"""
data_loader.py
==============
Loads the climate dataset from disk (CSV) and provides small helpers.

Why a separate loader?
----------------------
In a real project the data source changes (a government portal, a sensor
gateway, an API).  If the rest of the code calls `pd.read_csv` everywhere,
that change becomes painful.  A single loader module isolates that concern -
this is the *separation of concerns* principle.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import config as cfg


def load_raw(path: Path | str | None = None) -> pd.DataFrame:
    """
    Load the RAW (messy) climate dataset.

    If the file does not exist yet it is created with the simulator, so the
    project is runnable on a fresh clone.
    """
    path = Path(path) if path else cfg.RAW_CSV
    if not path.exists():
        from .data_generator import write_raw_dataset
        write_raw_dataset(path)
    df = pd.read_csv(path)
    print(f"[data_loader] Loaded raw dataset: {path} -> shape {df.shape}")
    return df


def load_clean(path: Path | str | None = None) -> pd.DataFrame:
    """Load the cleaned dataset (produced by `preprocessing.clean_dataset`)."""
    path = Path(path) if path else cfg.CLEAN_CSV
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python main.py --step clean` first."
        )
    df = pd.read_csv(path, parse_dates=["date"])
    print(f"[data_loader] Loaded clean dataset: {path} -> shape {df.shape}")
    return df


def load_featured(path: Path | str | None = None) -> pd.DataFrame:
    """Load the feature-engineered dataset."""
    path = Path(path) if path else cfg.FEATURED_CSV
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python main.py --step features` first."
        )
    df = pd.read_csv(path, parse_dates=["date"])
    print(f"[data_loader] Loaded featured dataset: {path} -> shape {df.shape}")
    return df


def save_table(df: pd.DataFrame, path: Path | str) -> Path:
    """Persist any analysis table into `outputs/tables/` (or a given path)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"[data_loader] Saved table -> {path} ({len(df)} rows)")
    return path


def save_json(obj: dict, path: Path | str) -> Path:
    """Persist a JSON summary (used for the run manifest)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)
    print(f"[data_loader] Saved json  -> {path}")
    return path


def dataset_info(df: pd.DataFrame) -> str:
    """A printable profile of any dataframe."""
    lines = [
        "=" * 62,
        f"DATASET PROFILE  shape={df.shape}",
        "=" * 62,
        df.dtypes.to_string(),
        "-" * 62,
        f"Missing values:\n{df.isna().sum().to_string()}",
        "-" * 62,
        f"Duplicate rows: {int(df.duplicated().sum())}",
    ]
    return "\n".join(lines)

```

**What this file does:** CSV/JSON access layer and dataset-profile helper.


## `src/eda.py`

```python
"""
eda.py
======
**Exploratory Data Analysis (EDA)** for the climate dataset.

EDA is the "get to know your data" phase.  A good EDA answers:

* How big is the dataset and what is its time coverage?
* What does each numeric variable look like (distribution, skew, spread)?
* How are the variables correlated?  (CO2 vs temperature is the classic one)
* What do the yearly / seasonal aggregates look like?
* Which years stand out?

Everything here returns **DataFrames**, so the results can be exported as
CSV tables (proof of work) and rendered by `visualizations.py`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as cfg


def summary_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """Descriptive statistics + skew/kurtosis for every climate variable."""
    cols = [c for c in cfg.CLIMATE_COLUMNS if c in df.columns]
    desc = df[cols].describe().T
    desc["skew"] = df[cols].skew()
    desc["kurtosis"] = df[cols].kurtosis()
    desc["missing"] = df[cols].isna().sum()
    desc["unit"] = [
        "degC", "degC", "degC", "mm", "%", "ppm", "mm"
    ][: len(cols)]
    return desc.round(3)


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation between the climate variables."""
    cols = [c for c in cfg.CLIMATE_COLUMNS if c in df.columns]
    return df[cols].corr().round(3)


def yearly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the monthly record to one row per year and region."""
    g = df.groupby(["region", "year"])
    out = g.agg(
        temp_mean=("temp_mean_c", "mean"),
        temp_max=("temp_max_c", "max"),
        temp_min=("temp_min_c", "min"),
        rainfall_total=("rainfall_mm", "sum"),
        rainfall_mean=("rainfall_mm", "mean"),
        humidity_mean=("humidity_pct", "mean"),
        co2_mean=("co2_ppm", "mean"),
        sea_level_mean=("sea_level_mm", "mean"),
        temp_anomaly=("temp_anomaly", "mean"),
        extreme_events=("extreme_event", "sum"),
    ).reset_index()
    return out.round(3)


def global_yearly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per year, averaged over all regions (the 'global' picture)."""
    per_region = yearly_summary(df)
    out = per_region.groupby("year").agg(
        temp_mean=("temp_mean", "mean"),
        rainfall_total=("rainfall_total", "mean"),
        humidity_mean=("humidity_mean", "mean"),
        co2_mean=("co2_mean", "mean"),
        sea_level_mean=("sea_level_mean", "mean"),
        temp_anomaly=("temp_anomaly", "mean"),
        extreme_events=("extreme_events", "sum"),
    ).reset_index()
    return out.round(3)


def seasonal_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Average value of each indicator per calendar month (all regions)."""
    cols = ["temp_mean_c", "rainfall_mm", "humidity_pct"]
    cols = [c for c in cols if c in df.columns]
    out = df.groupby("month")[cols].mean().reset_index()
    out["month_name"] = out["month"].map(
        {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
         7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
    )
    return out.round(3)


def regional_seasonal_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Month x region matrix of mean temperature (used for the heatmap)."""
    return (
        df.pivot_table(index="month", columns="region", values="temp_mean_c", aggfunc="mean")
        .round(2)
        .reset_index()
    )


def warmest_years(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """The `top_n` warmest years in the record (global mean across regions)."""
    gy = global_yearly_summary(df)
    return gy.nlargest(top_n, "temp_mean").reset_index(drop=True)


def data_quality_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Per-column completeness profile - proof of the cleaning work."""
    rows = []
    for col in df.columns:
        missing = int(df[col].isna().sum())
        rows.append(
            {
                "column": col,
                "dtype": str(df[col].dtype),
                "missing": missing,
                "missing_pct": round(100.0 * missing / len(df), 3),
                "unique": int(df[col].nunique()),
            }
        )
    return pd.DataFrame(rows)


def run_eda(df: pd.DataFrame) -> dict:
    """Run every EDA routine and return a bundle of tables."""
    bundle = {
        "summary": summary_statistics(df),
        "correlations": correlation_matrix(df),
        "yearly": yearly_summary(df),
        "global_yearly": global_yearly_summary(df),
        "seasonal": seasonal_profile(df),
        "regional_seasonal": regional_seasonal_profile(df),
        "warmest_years": warmest_years(df),
        "quality": data_quality_profile(df),
    }
    return bundle


if __name__ == "__main__":
    from .data_loader import load_clean

    bundle = run_eda(load_clean())
    print(bundle["summary"].to_string())
    print()
    print("Strongest correlation with temperature:")
    corr = bundle["correlations"]["temp_mean_c"].drop("temp_mean_c").sort_values(
        ascending=False, key=lambda s: s.abs()
    )
    print(corr.to_string())

```

**What this file does:** Descriptive statistics, correlations, seasonal and annual aggregations.


## `src/features.py`

```python
"""
features.py
===========
**Feature engineering** for climate time series.

Feature engineering turns raw measurements into *model-ready* variables.
For climate data the most valuable features are:

* calendar features   : year, month, quarter, season, decade
* trend features     : linear time index `t`
* smoothing features : 12-month rolling mean / std (removes seasonal noise)
* climatology        : per-calendar-month baseline (the long term normal)
* anomalies          : how far a month deviates from its own normal
* persistence        : lagged values (t-1, t-12) - what a forecaster sees
* event flags        : heat wave / drought indicators
* global drivers     : CO2 level and sea level for the same month

The same feature table is used by the EDA, the anomaly detector, the
forecaster and the dashboard - one source of truth, no duplication.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as cfg

#: Calendar month -> meteorological season (northern hemisphere convention)
MONTH_TO_SEASON = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Autumn", 10: "Autumn", 11: "Autumn",
}


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar / index features."""
    df = df.copy()
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["season"] = df["month"].map(MONTH_TO_SEASON)
    df["decade"] = (df["year"] // 10) * 10
    df["t"] = (df["year"] - df["year"].min()) * 12 + (df["month"] - 1)
    df["date_ordinal"] = (df["date"] - pd.Timestamp("1980-01-01")).dt.days
    # Meteorological seasons reverse in the southern hemisphere.
    southern = df["latitude"] < 0
    opposite = {"Winter":"Summer","Spring":"Autumn","Summer":"Winter","Autumn":"Spring"}
    df.loc[southern,"season"] = df.loc[southern,"season"].map(opposite)
    return df


def add_rolling_features(df: pd.DataFrame, window: int = cfg.ROLLING_WINDOW) -> pd.DataFrame:
    """Add centred rolling mean / std of the main indicators (per region)."""
    df = df.copy()
    for col in ("temp_mean_c", "rainfall_mm", "co2_ppm"):
        if col not in df.columns:
            continue
        g = df.groupby("region")[col]
        df[f"{col}_roll{window}_mean"] = g.transform(
            lambda s: s.rolling(window, center=True, min_periods=3).mean()
        )
        df[f"{col}_roll{window}_std"] = g.transform(
            lambda s: s.rolling(window, center=True, min_periods=3).std()
        )
    return df


def add_climatology(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the climatological baseline (the 'normal') and the anomalies.

    * `temp_clim`     : mean temperature of that calendar month (all years)
    * `temp_anomaly`  : observed - normal  (in °C)
    * `temp_anomaly_pct`: anomaly expressed in % of the normal
    * `rain_normal`   : average rainfall of that calendar month
    * `rain_anomaly_pct`: (observed - normal) / normal * 100
    """
    df = df.copy()
    grp = df.groupby(["region", "month"])
    df["temp_clim"] = grp["temp_mean_c"].transform("mean")
    df["temp_std_clim"] = grp["temp_mean_c"].transform("std")
    df["rain_normal"] = grp["rainfall_mm"].transform("mean")
    df["rain_std_clim"] = grp["rainfall_mm"].transform("std")

    df["temp_anomaly"] = df["temp_mean_c"] - df["temp_clim"]
    df["temp_anomaly_z"] = df["temp_anomaly"] / df["temp_std_clim"].replace(0, np.nan)
    df["temp_anomaly_pct"] = 100.0 * df["temp_anomaly"] / df["temp_clim"].replace(0, np.nan)
    df["rain_anomaly_pct"] = 100.0 * (df["rainfall_mm"] - df["rain_normal"]) / df["rain_normal"].replace(0, np.nan)
    df["rain_pct_of_normal"] = 100.0 * df["rainfall_mm"] / df["rain_normal"].replace(0, np.nan)
    df["rain_anomaly_z"] = (
        (df["rainfall_mm"] - df["rain_normal"]) / df["rain_std_clim"].replace(0, np.nan)
    )
    return df


def add_lag_features(df: pd.DataFrame, lags=(1, 2, 3, 12)) -> pd.DataFrame:
    """Add lagged target values - the classic supervised-learning setup."""
    df = df.copy()
    for col in ("temp_mean_c", "rainfall_mm"):
        if col not in df.columns:
            continue
        g = df.groupby("region")[col]
        for lag in lags:
            df[f"{col}_lag{lag}"] = g.shift(lag)
    return df


def add_event_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flag heat waves and droughts.

    * heat wave : >= 3 consecutive months with anomaly > 1.5 sigma
    * drought   : rainfall < 40 % of the calendar-month normal
    """
    df = df.copy()
    df["heatwave_month"] = (df["temp_anomaly_z"] > 1.5).astype(int)
    df["drought_month"] = (df["rain_pct_of_normal"] < 40).astype(int)

    def _streak(series: pd.Series) -> pd.Series:
        """Flag positions that belong to a run of >= 3 consecutive True values."""
        arr = series.to_numpy()
        out = np.zeros(len(arr), dtype=int)
        run = 0
        for i, v in enumerate(arr):
            run = run + 1 if v else 0
            out[i] = 1 if run >= 3 else 0
        return pd.Series(out, index=series.index)

    df["heatwave_event"] = (
        df.groupby("region")["heatwave_month"].transform(_streak)
    )
    df["drought_event"] = (
        df.groupby("region")["drought_month"].transform(_streak)
    )
    df["extreme_event"] = ((df["heatwave_event"] == 1) | (df["drought_event"] == 1)).astype(int)
    return df


def add_global_driver_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add slow-moving global drivers (CO2, sea level) and a smoothed
    ENSO-proxy index derived from the global mean temperature anomaly.
    """
    df = df.copy()
    # global mean anomaly per month (same for every region)
    global_enso = (
        df.groupby("date")["temp_anomaly"].mean().sort_index().rolling(3, center=True).mean()
    )
    df["enso_proxy"] = df["date"].map(global_enso)
    df["co2_change_rate"] = df.groupby("region")["co2_ppm"].diff(12)
    df["sea_level_change_rate"] = df.groupby("region")["sea_level_mm"].diff(12)
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Run every feature-engineering step in the correct order."""
    out = df.copy()
    out = add_time_features(out)
    out = add_rolling_features(out)
    out = add_climatology(out)
    out = add_lag_features(out)
    out = add_event_flags(out)
    out = add_global_driver_features(out)
    out = out.sort_values(["region", "date"]).reset_index(drop=True)
    return out


def feature_list_for_forecasting() -> list[str]:
    """Numeric features used by the ML forecaster (no leakage of the target)."""
    return [
        "t",
        "month_sin",
        "month_cos",
        "temp_mean_c_lag1",
        "temp_mean_c_lag2",
        "temp_mean_c_lag3",
        "temp_mean_c_lag12",
        "temp_mean_c_roll12_mean",
        "co2_ppm",
        "enso_proxy",
    ]


def add_cyclical_month(df: pd.DataFrame) -> pd.DataFrame:
    """Sin/cos encoding of the month - lets trees learn seasonality."""
    df = df.copy()
    ang = 2 * np.pi * df["month"] / 12.0
    df["month_sin"] = np.sin(ang)
    df["month_cos"] = np.cos(ang)
    return df


if __name__ == "__main__":
    from .data_loader import load_clean

    df = build_features(load_clean())
    print(df.shape)
    print(df.columns.tolist())

```

**What this file does:** Retrospective exploratory features; these are not automatically safe prediction inputs.


## `src/forecasting.py`

```python
"""Chronological multi-step forecasting with fair baselines.

All models predict the ENTIRE last 60-month validation block without seeing
its targets. This block selects a model: it is not an independent test set.
Ridge uses only deterministic future-known calendar/time features. Exploratory
centred rolling means, full-record climatologies and ENSO proxies NEVER enter
this module. Missing training targets are forward filled within training only;
validation metrics exclude originally missing observations.
"""
from __future__ import annotations
import warnings
import numpy as np
import pandas as pd
from . import config as cfg


def evaluate(y_true, y_pred) -> dict:
    """Celsius MAPE is omitted: percentages depend on the arbitrary zero."""
    a, b = np.asarray(y_true, float), np.asarray(y_pred, float)
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    if not len(a):
        raise ValueError('No observed targets available for evaluation')
    e = a - b
    return dict(MAE=float(np.abs(e).mean()), RMSE=float(np.sqrt((e**2).mean())),
                R2=float(1-(e**2).sum()/((a-a.mean())**2).sum()) if a.std() else np.nan,
                n_evaluated=int(len(a)))


def naive_forecast(train, h):
    return np.repeat(train[-1], h)


def seasonal_naive_forecast(train, h, period=12):
    if len(train) < period:
        raise ValueError('Seasonal naive needs at least one year')
    return np.resize(np.asarray(train)[-period:], h)


def drift_forecast(train, h):
    return train[-1] + (train[-1]-train[0])/max(len(train)-1, 1)*np.arange(1,h+1)


def _calendar(dates):
    """Only known future covariates, no measurements of the future."""
    d = pd.DatetimeIndex(dates)
    t = (d.year.to_numpy()-1980)*12 + d.month.to_numpy()-1
    ang = 2*np.pi*d.month.to_numpy()/12
    return np.column_stack([t, np.sin(ang), np.cos(ang)])


def build_ml_dataset(df, target='temp_mean_c'):
    """Educational helper: no target-derived or centred features allowed."""
    d = df.sort_values('date').copy()
    d[['time_index','month_sin','month_cos']] = _calendar(d.date)
    return d, ['time_index','month_sin','month_cos']


def _ridge_fit(dates, values):
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge
    pipe = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    return pipe.fit(_calendar(dates), values)


def _observations(d, target):
    # Historical interpolation is NOT used to evaluate or fit the forecaster.
    name = 'observed_temp_mean_c' if target == 'temp_mean_c' and 'observed_temp_mean_c' in d else target
    return d[name].astype(float).to_numpy()


def _fill_train(a):
    s = pd.Series(a).ffill()
    if s.isna().all():
        raise ValueError('Training series has no observations')
    return s.fillna(s.median()).to_numpy()


def ml_forecast(df, target='temp_mean_c', h=cfg.FORECAST_HORIZON, test_size=cfg.TEST_SIZE):
    """Calendar Ridge: identical fixed-origin protocol for validation/future."""
    d = df.sort_values('date').copy()
    y = _observations(d, target)
    cut = len(d)-test_size
    pipe = _ridge_fit(d.date.iloc[:cut], _fill_train(y[:cut]))
    pred = pipe.predict(_calendar(d.date.iloc[cut:]))
    metrics = evaluate(y[cut:], pred)
    pipe = _ridge_fit(d.date, _fill_train(y))
    dates = pd.date_range(d.date.max()+pd.offsets.MonthBegin(), periods=h, freq='MS')
    future = pd.DataFrame({'date':dates, 'prediction':pipe.predict(_calendar(dates))})
    return dict(model='Ridge (calendar + trend)', metrics=metrics, forecast=future,
                fitted=pipe, features=['time_index','month_sin','month_cos'],
                validation_prediction=pred)


def arima_forecast(series, h=cfg.FORECAST_HORIZON, order=(1,1,1), test_size=cfg.TEST_SIZE):
    from statsmodels.tsa.arima.model import ARIMA
    y = np.asarray(series, float)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            fit = ARIMA(_fill_train(y[:-test_size]), order=order).fit()
            pred = np.asarray(fit.forecast(test_size))
            full = ARIMA(_fill_train(y), order=order).fit()
            fc = full.get_forecast(h)
        ci = np.asarray(fc.conf_int())
        return dict(model=f'ARIMA{order}', metrics=evaluate(y[-test_size:],pred),
                    forecast_mean=np.asarray(fc.predicted_mean), forecast_ci_low=ci[:,0],
                    forecast_ci_high=ci[:,1], order=order, validation_prediction=pred)
    except (ValueError, np.linalg.LinAlgError):
        return {}


def arima_grid_search(series, h=cfg.FORECAST_HORIZON, test_size=cfg.TEST_SIZE):
    """Choose order by TRAINING AIC, not repeated peeking at validation."""
    from statsmodels.tsa.arima.model import ARIMA
    train = _fill_train(np.asarray(series,float)[:-test_size])
    best, score = (1,1,1), np.inf
    for p in range(cfg.ARIMA_MAX_P+1):
        for dd in (0,1):
            for q in range(cfg.ARIMA_MAX_Q+1):
                if (p,dd,q)==(0,0,0):
                    continue
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore')
                        fit = ARIMA(train, order=(p,dd,q)).fit()
                    if fit.mle_retvals.get('converged',True) and fit.aic < score:
                        best, score = (p,dd,q), fit.aic
                except (ValueError, np.linalg.LinAlgError):
                    continue
    return arima_forecast(series,h,best,test_size)


def forecast_region(df_region, target='temp_mean_c', h=cfg.FORECAST_HORIZON, test_size=cfg.TEST_SIZE):
    d = df_region.sort_values('date').copy()
    if len(d)<test_size+36:
        return {}
    if not d.date.diff().dropna().dt.days.between(28,31).all():
        raise ValueError('Forecasting requires a complete monthly date grid')
    y = _observations(d,target)
    train = _fill_train(y[:-test_size]); full = _fill_train(y)
    records, forecasts, validation = [], {}, {}
    for name, fun in [('Naive',naive_forecast),('Seasonal naive',seasonal_naive_forecast),('Drift (linear)',drift_forecast)]:
        val = fun(train,test_size)
        records.append(dict(model=name,**evaluate(y[-test_size:],val)))
        forecasts[name] = fun(full,h); validation[name]=val
    ml = ml_forecast(d,target,h,test_size)
    records.append(dict(model=ml['model'],**ml['metrics']))
    forecasts[ml['model']] = ml['forecast'].prediction.to_numpy()
    validation[ml['model']] = ml['validation_prediction']
    arima = arima_grid_search(pd.Series(y),h,test_size)
    if arima:
        records.append(dict(model=arima['model'],**arima['metrics']))
        forecasts[arima['model']]=arima['forecast_mean']
        validation[arima['model']]=arima['validation_prediction']
    metrics = pd.DataFrame(records).sort_values('RMSE').reset_index(drop=True)
    best = metrics.iloc[0]['model']; pred = forecasts[best]
    dates = pd.date_range(d.date.max()+pd.offsets.MonthBegin(),periods=h,freq='MS')
    # Approximate residual bands, NOT a calibrated physical climate interval.
    half_width = 1.96*float(metrics.iloc[0]['RMSE'])
    lo, hi = pred-half_width, pred+half_width
    if arima and best==arima['model']:
        lo,hi = arima['forecast_ci_low'],arima['forecast_ci_high']
    fc = pd.DataFrame(dict(region=d.region.iloc[0],date=dates,prediction=pred,
                           ci_low=lo,ci_high=hi,model=best,target=target,
                           interval_method='ARIMA model-based' if best.startswith('ARIMA') else 'approximate 1.96 x validation RMSE; not calibrated'))
    return dict(region=d.region.iloc[0],best_model=best,metrics=metrics,forecast=fc,
                arima=arima,ml=ml,history=d[['date',target]].copy())


def run_forecasting(df, target='temp_mean_c', h=cfg.FORECAST_HORIZON, test_size=cfg.TEST_SIZE):
    results = [forecast_region(g,target,h,test_size) for _,g in df.groupby('region')]
    results = [r for r in results if r]
    metrics, forecasts = [], []
    for r in results:
        m = r['metrics'].assign(region=r['region']); metrics.append(m); forecasts.append(r['forecast'])
    return dict(metrics=pd.concat(metrics,ignore_index=True) if metrics else pd.DataFrame(),
                forecast=pd.concat(forecasts,ignore_index=True) if forecasts else pd.DataFrame(),
                results=results,target=target)

```

**What this file does:** Common fixed-origin validation with future-known predictors and train-only filling.


## `src/insights.py`

```python
"""
insights.py
===========
**Automatic insight generation.**

An analytics project is only valuable if it ends with *findings*, not just
charts.  This module converts the numeric results into natural-language
insights - the same sentences you would put in the "Key Findings" section of
a report or in an interview.

Every number in the text is read from the analysis results, so the insights
are always consistent with the data (no hard-coded claims).
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from . import config as cfg


def _fmt(x, nd=3):
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "n/a"
        return f"{float(x):.{nd}f}"
    except Exception:
        return str(x)


def generate_insights(bundle: dict) -> str:
    """
    Build the full markdown insight block.

    Parameters
    ----------
    bundle : dict
        The analysis bundle produced by `pipeline.run_pipeline()`.
    """
    df = bundle["featured"]
    trends = bundle["trend_results"]["trends"]
    temp_trends = bundle["trend_results"]["temperature_trends"]
    anomalies = bundle["anomaly_results"]["anomalies"]
    fc = bundle["forecast_results"]
    clean_report = bundle["clean_report"]
    corr = bundle["eda"]["correlations"]

    temp_trends = temp_trends.sort_values("slope_per_decade", ascending=False)
    fastest = temp_trends.iloc[0]
    slowest = temp_trends.iloc[-1]
    warming = temp_trends[temp_trends["slope_per_decade"] > 0]
    significant = trends[trends["p_value"] < 0.05]

    # --- CO2 / temperature relationship -----------------------------------
    g = df.groupby("date")[["co2_ppm", "temp_mean_c"]].mean().reset_index()
    co2_corr = float(np.corrcoef(g["co2_ppm"], g["temp_mean_c"])[0, 1])

    # --- extremes ---------------------------------------------------------
    n_anom = len(anomalies)
    hot = int((anomalies["direction"] == "hot").sum()) if n_anom else 0
    cold = int((anomalies["direction"] == "cold").sum()) if n_anom else 0
    drought = int((anomalies["direction"] == "drought").sum()) if n_anom else 0
    wet = int((anomalies["direction"] == "wet").sum()) if n_anom else 0
    notable = bundle["anomaly_results"].get("notable", pd.DataFrame())

    # --- forecasting ------------------------------------------------------
    best_models = {}
    if not fc["metrics"].empty:
        for region, g_m in fc["metrics"].groupby("region"):
            best_models[region] = g_m.iloc[0]["model"]
    fc_tbl = fc["forecast"]

    lines = []
    A = lines.append

    A("## Key Findings\n")
    A(f"*Generated automatically on {datetime.now().strftime('%Y-%m-%d %H:%M')} "
      f"from {len(df):,} cleaned monthly records "
      f"({df['date'].min():%Y-%m} to {df['date'].max():%Y-%m}) "
      f"across {df['region'].nunique()} regions.*\n")

    A("### 1. Warming trend\n")
    A(f"- **Synthetic warming signal.** {len(warming)} of {len(temp_trends)} simulated "
      f"regions show a statistically significant positive temperature trend "
      f"({len(significant)} of {len(trends)} region x indicator combinations are significant at p < 0.05).")
    A(f"- **Fastest synthetic warming:** {fastest['region']} at "
      f"**{_fmt(fastest['slope_per_decade'])} °C per decade** "
      f"(OLS slope {_fmt(fastest['slope_per_year'], 4)} °C/yr, full model R² (including seasonal effects) = {_fmt(fastest['r_squared'])}, "
      f"p = {fastest['p_value']:.2e}).")
    A(f"- **Slowest warming:** {slowest['region']} at "
      f"{_fmt(slowest['slope_per_decade'])} °C per decade.")
    A(f"- **Mann-Kendall (non-parametric) test** confirms the trend for "
      f"{int((temp_trends['mk_p_value'] < 0.05).sum())}/{len(temp_trends)} regions "
      f"(all {temp_trends['mk_trend'].unique().tolist()}).")
    A(f"- Regional spread in warming rate is "
      f"**{_fmt(fastest['slope_per_decade'] - slowest['slope_per_decade'])} °C/decade**, "
      f"i.e. the same climate driver produces very different local impacts - "
      f"which is exactly why regionalisation matters for policy.\n")

    A("### 2. Seasonal structure\n")
    names = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
             7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}
    # peak / trough month PER REGION (a pooled average would mix the hemispheres)
    reg_month = df.groupby(["region", "month"])["temp_mean_c"].mean()
    region_peak = reg_month.groupby("region").idxmax().map(lambda x: int(x[1]))
    region_trough = reg_month.groupby("region").idxmin().map(lambda x: int(x[1]))
    swing = (reg_month.groupby("region").max() - reg_month.groupby("region").min())

    peak_list = ", ".join(f"{r} ({names[m]})" for r, m in region_peak.items())
    A(f"- **Every region has its own seasonal peak:** {peak_list}. "
      f"The ~6-month phase shift between the northern and southern hemispheres "
      f"(London peaks in July, Sydney in January) is exactly what a climate-aware "
      f"model has to capture.")
    A(f"- The seasonal swing differs sharply by climate: "
      f"**{swing.idxmax()}** swings {_fmt(swing.max(), 1)} °C between its warmest and "
      f"coolest month, while **{swing.idxmin()}** swings only {_fmt(swing.min(), 1)} °C - "
      f"a {int(swing.max() / max(swing.min(), 1e-6))}x difference in seasonal amplitude.")
    A(f"- {len(set(region_peak))} distinct peak months appear across the {len(region_peak)} regions, "
      f"confirming the simulator reproduces hemisphere-aware seasonality.")
    A("- Seasonality is the main source of variance, so every model in this project "
      "uses a 12-month baseline (climatology) or a seasonal-naive benchmark, and every "
      "trend statistic is computed on a **deseasonalised** series.\n")

    A("### 3. Anomalies and extreme events\n")
    A(f"- **{n_anom:,} detector records** were detected by the four-method ensemble "
      f"(z-score, STL residual, IQR, Isolation Forest).")
    A(f"- Detector-record direction split (methods can flag the same month): **{hot} hot**, **{cold} cold**, **{drought} dry**, **{wet} wet** months.")
    if not notable.empty:
        top = notable.iloc[0]
        A(f"- Most extreme event: **{top['description']}** in {top['region']} "
          f"on {pd.Timestamp(top['date']):%d %b %Y} (score {top['score']}).")
    # extreme events normalised per year, because the last decade is incomplete
    ev = df.groupby("decade").agg(events=("extreme_event", "sum"),
                                  months=("extreme_event", "size"))
    ev["per_year"] = ev["events"] / (ev["months"] / 12.0)
    if len(ev) > 1:
        first, last = ev.iloc[0], ev.iloc[-1]
        change = 100.0 * (last["per_year"] / max(first["per_year"], 1e-9) - 1)
        direction = "rising" if change > 0 else "falling"
        A(f"- Heat-wave + drought months occur at **{_fmt(first['per_year'], 1)} per year** in the "
          f"{int(ev.index[0])}s and **{_fmt(last['per_year'], 1)} per year** in the "
          f"{int(ev.index[-1])}s - a {direction} rate "
          f"({_fmt(abs(change), 1)} % {'more' if change > 0 else 'fewer'}). "
          f"(The {int(ev.index[-1])}s are a partial decade, so the rate is used instead of the raw count.)")
        A(f"- The mean warming rate is "
          f"{_fmt(float(temp_trends['slope_per_decade'].mean()), 3)} °C/decade; "
          f"extremes and the mean therefore move **"
          f"{'in the same direction' if (change > 0) == (temp_trends['slope_per_decade'].mean() > 0) else 'in opposite directions'}**, "
          f"but these planted simulation episodes are not evidence that real-world extreme frequency increased.\n")

    A("### 4. Drivers\n")
    A(f"- Atmospheric CO₂ and mean temperature have a monthly, unweighted five-city correlation of "
      f"**r = {co2_corr:.3f}** (Pearson, monthly unweighted five-city means).")
    co2_trend = trends[(trends["indicator"] == "co2_ppm")]
    if not co2_trend.empty:
        c = co2_trend.iloc[0]
        A(f"- CO₂ is rising at about **{_fmt(c['slope_per_year'] * 10, 2)} ppm per decade** "
          f"(R² = {_fmt(c['r_squared'])}) (concentration, not emissions).")
    A("- Shared time trends can create spurious correlation; these simulated associations "
      "do not establish causal attribution. This five-city mean is NOT a global climate index.\n")

    A("### 5. Forecasting\n")
    if not fc["metrics"].empty and not fc_tbl.empty:
        avg_rmse = float(fc["metrics"]["RMSE"].min())
        A(f"- The best model per region was selected by **60-month chronological validation**: "
          f"{', '.join(f'{r} -> {m}' for r, m in best_models.items())}.")
        A(f"- Lowest validation RMSE among candidates: **{_fmt(avg_rmse, 3)} °C** "
          f"on a monthly average temperature series.")
        last = fc_tbl.sort_values("date").groupby("region").tail(1)
        for _, r in last.iterrows():
            A(f"- **{r['region']}**: projected mean temperature in "
              f"{pd.Timestamp(r['date']):%B %Y} = **{_fmt(r['prediction'], 2)} °C**.")
        A("- Production note: the 36-month projection is a *trend continuation* scenario, "
          "not a physical climate model. For policy-grade numbers, this pipeline would be "
          "pointed at CMIP6/IPCC scenarios instead of a statistical extrapolation.\n")

    A("### 6. Data quality\n")
    A(f"- The raw file contained **{clean_report['rows_in']:,} rows**; after removing "
      f"{clean_report['rows_dropped']:,} unusable records (bad dates / duplicates) the "
      f"analysis table holds **{clean_report['rows_out']:,} rows**.")
    A(f"- **{sum(clean_report['values_imputed'].values()):,} values** were imputed and "
      f"**{clean_report['rows_with_impossible_values']:,} rows** contained physically "
      f"impossible readings (e.g. -999 °C sensor dropouts) that were flagged and repaired.")
    A(f"- Final completeness: **{clean_report['completeness_pct']:.2f} %**.\n")

    A("### 7. Business & policy implications\n")
    A("- **Energy & utilities:** a reliable regional warming signal supports "
      "peak-demand and cooling-load planning; no cost savings are measured by this project.")
    A("- **Agriculture:** seasonal rainfall anomalies identify drought and flood "
      "risk windows for crop planning and irrigation scheduling.")
    A("- **Insurance & finance:** anomaly frequency and trend severity are the "
      "inputs for parametric weather-risk pricing and climate exposure disclosure.")
    A("- **Urban planning & public health:** heat-wave month counts translate directly "
      "into cooling-centre, heat-health-alert and infrastructure design criteria.")
    A("- **Sustainability reporting:** the pipeline produces reproducible, auditable "
      "tables and charts that can be embedded in ESG / TCFD disclosures.\n")

    A("### 8. Limitations and next steps\n")
    A("- The dataset is a **simulation**: it reproduces realistic statistical structure "
      "(seasonality, autocorrelation, trends, extremes) but it is not an observational record.")
    A("- The statistical models extrapolate; they do not model physical climate feedbacks.")
    A("- Next: replace the simulator with a public dataset (NASA GISTEMP, NOAA, "
      "Our World in Data), add CMIP6 scenarios, and validate the forecasts against "
      "published indices.\n")

    return "\n".join(lines)


def key_numbers(bundle: dict) -> dict:
    """Machine readable version of the headline numbers (used in the report)."""
    trends = bundle["trend_results"]["temperature_trends"]
    anomalies = bundle["anomaly_results"]["anomalies"]
    fc = bundle["forecast_results"]
    fastest = trends.sort_values("slope_per_decade", ascending=False).iloc[0]
    return {
        "rows_analysed": int(len(bundle["featured"])),
        "regions": int(bundle["featured"]["region"].nunique()),
        "fastest_warming_region": fastest["region"],
        "fastest_warming_c_per_decade": round(float(fastest["slope_per_decade"]), 4),
        "mean_warming_c_per_decade": round(float(trends["slope_per_decade"].mean()), 4),
        "anomalies_detected": int(len(anomalies)),
        "best_forecast_rmse": (
            round(float(fc["metrics"]["RMSE"].min()), 4) if not fc["metrics"].empty else None
        ),
        "data_completeness_pct": bundle["clean_report"]["completeness_pct"],
    }

```

**What this file does:** Natural-language findings computed from saved statistical results.


## `src/pipeline.py`

```python
"""
pipeline.py
===========
**End-to-end orchestration.**

`run_pipeline()` executes the full workflow in the correct order and returns a
single *bundle* (a dict of DataFrames) that every downstream consumer
(report, dashboard, tests) uses.

Stages
------
    simulate -> clean -> features -> eda -> trends -> anomalies -> forecast
             -> visualise -> insights -> report

Each stage is a separate function so it can also be run on its own from
`main.py` (e.g. `python main.py --step trends`).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from . import config as cfg
from . import (
    anomaly_detection,
    data_generator,
    data_loader,
    eda as eda_mod,
    features as feat_mod,
    forecasting as fc_mod,
    insights as ins_mod,
    preprocessing,
    report_generator,
    trend_analysis,
    visualizations as viz,
)


def _log(msg: str, start: float) -> None:
    print(f"[pipeline] {msg}  (+{time.time() - start:.1f}s)")


# --------------------------------------------------------------------------
# Individual stages
# --------------------------------------------------------------------------
def stage_simulate(force: bool = False) -> pd.DataFrame:
    """Create the raw (imperfect) dataset if it does not exist yet."""
    if cfg.RAW_CSV.exists() and not force:
        print(f"[pipeline] Raw dataset already present: {cfg.RAW_CSV}")
        return data_loader.load_raw(cfg.RAW_CSV)
    raw = data_generator.write_raw_dataset(cfg.RAW_CSV, seed=cfg.RANDOM_SEED)
    print(f"[pipeline] Simulated raw dataset written: {cfg.RAW_CSV} {raw.shape}")
    return raw


def stage_clean(raw: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """Clean the raw dataset and store the clean master table."""
    raw = raw if raw is not None else data_loader.load_raw(cfg.RAW_CSV)
    clean, report = preprocessing.clean_dataset(raw)
    clean.to_csv(cfg.CLEAN_CSV, index=False)
    preprocessing.quality_report_table(report).to_csv(cfg.TABLES_DIR / "cleaning_audit.csv", index=False)
    data_loader.save_json(report, cfg.OUTPUTS_DIR / "cleaning_audit.json")
    print(f"[pipeline] Clean dataset -> {cfg.CLEAN_CSV} {clean.shape}")
    return clean, report


def stage_features(clean: pd.DataFrame | None = None) -> pd.DataFrame:
    """Engineer the model-ready features."""
    clean = clean if clean is not None else data_loader.load_clean(cfg.CLEAN_CSV)
    feat = feat_mod.build_features(clean)
    feat = feat_mod.add_cyclical_month(feat)
    feat.to_csv(cfg.FEATURED_CSV, index=False)
    print(f"[pipeline] Featured dataset -> {cfg.FEATURED_CSV} {feat.shape}")
    return feat


def stage_eda(featured: pd.DataFrame) -> dict:
    """Exploratory data analysis."""
    bundle = eda_mod.run_eda(featured)
    data_loader.save_table(bundle["yearly"], cfg.YEARLY_CSV)
    data_loader.save_table(bundle["correlations"].reset_index(names="indicator"), cfg.CORR_CSV)
    print(f"[pipeline] EDA complete ({len(bundle['yearly'])} yearly rows)")
    return bundle


def stage_trends(featured: pd.DataFrame) -> dict:
    """Trend analysis (OLS + Mann-Kendall + decomposition)."""
    res = trend_analysis.run_trend_analysis(featured)
    data_loader.save_table(res["trends"], cfg.TREND_CSV)
    print(f"[pipeline] Trend analysis complete ({len(res['trends'])} region x indicator rows)")
    return res


def stage_anomalies(featured: pd.DataFrame) -> dict:
    """Anomaly detection ensemble."""
    res = anomaly_detection.run_anomaly_detection(featured)
    data_loader.save_table(res["anomalies"], cfg.ANOMALY_CSV)
    print(f"[pipeline] Anomaly detection complete ({len(res['anomalies'])} anomalies)")
    return res


def stage_forecast(featured: pd.DataFrame, do_forecast: bool = True) -> dict:
    """Model comparison + 36-month projection."""
    if not do_forecast:
        print("[pipeline] Forecasting skipped (--no-forecast)")
        return {"metrics": pd.DataFrame(), "forecast": pd.DataFrame(), "results": []}
    res = fc_mod.run_forecasting(featured)
    if not res["metrics"].empty:
        data_loader.save_table(res["metrics"], cfg.METRICS_CSV)
    if not res["forecast"].empty:
        data_loader.save_table(res["forecast"], cfg.FORECAST_CSV)
    print(f"[pipeline] Forecasting complete ({len(res['forecast'])} projected rows)")
    return res


def stage_visualize(bundle: dict) -> dict:
    """Create every figure used in the report and the README."""
    raw = bundle.get("raw")
    clean = bundle["clean"]
    featured = bundle["featured"]
    anomalies = bundle["anomaly_results"]["anomalies"]

    figs: dict = {}
    figs["architecture"] = viz.plot_architecture_diagram()
    if raw is not None:
        figs["raw"] = viz.plot_raw_preview(raw)
        figs["quality"] = viz.plot_data_quality(raw, clean)
    figs["temperature"] = viz.plot_temperature_trend(featured)
    figs["rainfall"] = viz.plot_rainfall_trend(featured)
    figs["heatmap"] = viz.plot_seasonal_heatmap(featured)
    figs["seasonal_profile"] = viz.plot_seasonal_profile(featured)
    figs["yearly"] = viz.plot_yearly_comparison(featured)
    figs["warming_bar"] = viz.plot_regional_warming_bar(
        bundle["trend_results"]["trends"]
    )
    figs["decomposition"] = viz.plot_decomposition(
        bundle["trend_results"]["decomposition"]
    )
    figs["anomaly"] = viz.plot_anomaly_detection(featured, anomalies)
    figs["anomaly_timeline"] = viz.plot_anomaly_timeline(anomalies)
    figs["extreme_events"] = viz.plot_extreme_events(featured)
    figs["co2"] = viz.plot_co2_vs_temperature(featured)
    figs["sea_level"] = viz.plot_sea_level_rise(featured)
    if bundle["forecast_results"].get("results"):
        figs["forecast"] = viz.plot_forecast(bundle["forecast_results"])
        figs["model_comparison"] = viz.plot_model_comparison(
            bundle["forecast_results"]["metrics"]
        )
    return figs


def stage_insights(bundle: dict) -> str:
    """Generate the natural-language insights and the key-numbers dict."""
    text = ins_mod.generate_insights(bundle)
    numbers = ins_mod.key_numbers(bundle)
    bundle["insights_text"] = text
    bundle["key_numbers"] = numbers
    return text


def stage_report(bundle: dict) -> None:
    """Write the Markdown + HTML reports and the insights document."""
    report_generator.build_markdown_report(bundle)
    report_generator.build_html_report(bundle)
    report_generator.write_insights_doc(bundle)


# --------------------------------------------------------------------------
# Full pipeline
# --------------------------------------------------------------------------
def run_pipeline(
    do_forecast: bool = True,
    force_simulate: bool = False,
    verbose: bool = True,
) -> dict:
    """
    Run the complete analytical workflow.

    Returns the analysis bundle (all DataFrames + results).
    """
    t0 = time.time()
    if verbose:
        print("=" * 70)
        print("CLIMATE TREND ANALYZER - END-TO-END PIPELINE")
        print("=" * 70)

    raw = stage_simulate(force=force_simulate)
    _log("stage 1/9  ingestion done", t0)

    clean, clean_report = stage_clean(raw)
    _log("stage 2/9  cleaning done", t0)

    featured = stage_features(clean)
    _log("stage 3/9  feature engineering done", t0)

    eda_bundle = stage_eda(featured)
    _log("stage 4/9  EDA done", t0)

    trend_results = stage_trends(featured)
    _log("stage 5/9  trend analysis done", t0)

    anomaly_results = stage_anomalies(featured)
    _log("stage 6/9  anomaly detection done", t0)

    forecast_results = stage_forecast(featured, do_forecast=do_forecast)
    _log("stage 7/9  forecasting done", t0)

    bundle = {
        "raw": raw,
        "clean": clean,
        "featured": featured,
        "clean_report": clean_report,
        "eda": eda_bundle,
        "trend_results": trend_results,
        "anomaly_results": anomaly_results,
        "forecast_results": forecast_results,
    }

    bundle["figures"] = stage_visualize(bundle)
    _log("stage 8/9  visualisations done", t0)

    # Real observations are a separate companion track, never synthetic joins.
    from .public_data import analyze as analyze_public, PATH as public_path
    if public_path.exists():
        bundle["public_data"] = analyze_public()
        bundle["figures"]["public_noaa"] = cfg.FIGURES_DIR / "16_public_noaa_co2.png"
    stage_insights(bundle)
    stage_report(bundle)
    _log("stage 9/9  insights + report done", t0)

    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "runtime_seconds": round(time.time() - t0, 1),
        "seed": cfg.RANDOM_SEED,
        "rows_raw": int(len(raw)),
        "rows_clean": int(len(clean)),
        "rows_featured": int(len(featured)),
        "regions": sorted(featured["region"].unique().tolist()),
        "date_min": str(featured["date"].min().date()),
        "date_max": str(featured["date"].max().date()),
        "anomalies": int(len(bundle["anomaly_results"]["anomalies"])),
        "figures": [str(p) for p in bundle["figures"].values()],
        "key_numbers": bundle["key_numbers"],
    }
    data_loader.save_json(summary, cfg.RUN_SUMMARY_JSON)

    if verbose:
        print("=" * 70)
        print(f"PIPELINE COMPLETE in {summary['runtime_seconds']}s")
        print(f"  figures   : {len(bundle['figures'])}  -> {cfg.FIGURES_DIR}")
        print(f"  tables    : {len(list(cfg.TABLES_DIR.glob('*.csv')))} -> {cfg.TABLES_DIR}")
        print(f"  report    : {cfg.REPORTS_DIR / 'climate_trend_report.html'}")
        print("=" * 70)
    return bundle


if __name__ == "__main__":
    run_pipeline()

```

**What this file does:** Orchestration of the analysis stages and saved run metadata.


## `src/preprocessing.py`

```python
"""
preprocessing.py
================
**Data cleaning & quality control** for the climate dataset.

The cleaning pipeline implemented here follows the standard Data-Quality
framework (ISO 8000 inspired) and is intentionally *auditable*: every action
is counted and returned in a report dictionary, so the final report can show
"before vs after" evidence.

Steps
-----
1.  Normalise column names & strip whitespace
2.  Parse the messy date column (handles "YYYY-MM-DD" **and** "MM/DD/YYYY")
3.  Drop rows whose date cannot be parsed
4.  Remove duplicate records
5.  Coerce numeric columns & count missing values
6.  Detect physically impossible values (outliers) and treat them as missing
7.  Impute remaining gaps (time interpolation, then regional median)
8.  Round / finalise types, sort and return a clean master table
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as cfg

# --------------------------------------------------------------------------
# Helper functions
# --------------------------------------------------------------------------
def _standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lower-case column names, replace spaces/dots with underscores."""
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace(".", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    return df


def parse_dates(df: pd.DataFrame, col: str = "date") -> pd.DataFrame:
    """
    Parse a mixed-format date column.

    The simulator deliberately writes 10 % of the dates as `MM/DD/YYYY`,
    therefore we try the ISO format first and fall back to the US format.
    """
    df = df.copy()
    raw = df[col].astype(str).str.strip()

    parsed = pd.to_datetime(raw, format="%Y-%m-%d", errors="coerce")
    still_missing = parsed.isna() & raw.notna()
    if still_missing.any():
        fallback = pd.to_datetime(raw[still_missing], format="%m/%d/%Y", errors="coerce")
        parsed.loc[still_missing] = fallback

    df[col] = parsed
    return df


def _impute_by_region(df: pd.DataFrame, col: str) -> pd.Series:
    """
    Impute missing values of one column, region by region.

    1. linear interpolation in time (keeps the physical continuity),
    2. regional median as a fallback for leading/trailing gaps.
    """
    out = df[col].copy()
    for region, idx in df.groupby("region").groups.items():
        s = out.loc[idx]
        # `method="time"` needs a DatetimeIndex, so re-index temporarily
        tmp = pd.Series(
            s.to_numpy(dtype=float),
            index=pd.DatetimeIndex(df.loc[idx, "date"].to_numpy()),
        )
        interpolated = tmp.interpolate(method="time", limit_direction="both")
        filled = interpolated.fillna(s.median())
        out.loc[idx] = filled.to_numpy()
    return out


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------
def clean_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Clean the raw climate dataset.

    Parameters
    ----------
    df : pd.DataFrame
        Raw dataset as returned by `data_loader.load_raw()`.

    Returns
    -------
    (clean_df, report)
        `clean_df` is the analysis-ready master table,
        `report` is a dict with every counter for documentation.
    """
    report: dict = {}
    df = df.copy()
    report["rows_in"] = int(len(df))
    report["columns_in"] = list(df.columns)

    # ---- 1. standardise column names ------------------------------------
    df = _standardise_columns(df)

    # ---- 2/3. dates ------------------------------------------------------
    df = parse_dates(df, "date")
    report["rows_unparseable_date"] = int(df["date"].isna().sum())
    df = df.dropna(subset=["date"]).copy()

    # ---- 4. duplicates ---------------------------------------------------
    dup_mask = df.duplicated(subset=["date", "region"], keep="first")
    report["duplicate_rows_removed"] = int(dup_mask.sum())
    df = df.loc[~dup_mask].copy()

    # ---- 5. numeric coercion + missing values ---------------------------
    for col in cfg.CLIMATE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    missing_before = {c: int(df[c].isna().sum()) for c in cfg.CLIMATE_COLUMNS if c in df}
    report["missing_before"] = missing_before

    # ---- 6. impossible values -> treated as missing ----------------------
    outlier_mask = pd.Series(False, index=df.index)
    outliers_found: dict = {}
    for col, (lo, hi) in cfg.VALID_RANGES.items():
        if col not in df.columns:
            continue
        bad = df[col].notna() & ((df[col] < lo) | (df[col] > hi))
        outliers_found[col] = int(bad.sum())
        outlier_mask |= bad
        df.loc[bad, col] = np.nan
    report["impossible_values_found"] = outliers_found
    report["rows_with_impossible_values"] = int(outlier_mask.sum())

    # Preserve observed targets for leakage-free temporal evaluation.  The
    # historical analysis may interpolate both ways; forecasting must not.
    df["observed_temp_mean_c"] = df["temp_mean_c"]
    df["data_quality_flag"] = np.where(
        df[[c for c in cfg.CLIMATE_COLUMNS if c in df]].isna().any(axis=1),
        "repaired", "original",
    )
    df = df.sort_values(["region", "date"])

    # ---- 7. imputation ----------------------------------------------------
    imputed_counts: dict = {}
    for col in cfg.CLIMATE_COLUMNS:
        if col not in df.columns:
            continue
        n_missing = int(df[col].isna().sum())
        if n_missing:
            df[col] = _impute_by_region(df, col)
        imputed_counts[col] = n_missing
    report["values_imputed"] = imputed_counts

    missing_after = {c: int(df[c].isna().sum()) for c in cfg.CLIMATE_COLUMNS if c in df}
    report["missing_after"] = missing_after

    # ---- 8. final tidy up -------------------------------------------------
    df = df.sort_values(["region", "date"]).reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    for col in ("temp_mean_c", "temp_min_c", "temp_max_c"):
        if col in df:
            df[col] = df[col].round(2)
    for col in ("rainfall_mm", "humidity_pct", "sea_level_mm"):
        if col in df:
            df[col] = df[col].round(1)
    if "co2_ppm" in df:
        df["co2_ppm"] = df["co2_ppm"].round(2)

    report["rows_out"] = int(len(df))
    report["rows_dropped"] = report["rows_in"] - report["rows_out"]
    report["date_min"] = str(df["date"].min().date())
    report["date_max"] = str(df["date"].max().date())
    report["regions"] = sorted(df["region"].unique().tolist())
    report["completeness_pct"] = round(
        100.0
        * (1 - sum(missing_after.values()) / max(1, len(df) * len(missing_after))),
        3,
    )
    return df, report


def quality_report_table(report: dict) -> pd.DataFrame:
    """Turn the cleaning report into a table that can be saved / printed."""
    rows = [
        {"metric": "Rows loaded (raw)", "value": report["rows_in"]},
        {"metric": "Rows dropped (bad dates / duplicates)", "value": report["rows_dropped"]},
        {"metric": "Rows in clean dataset", "value": report["rows_out"]},
        {"metric": "Unparseable dates removed", "value": report["rows_unparseable_date"]},
        {"metric": "Duplicate rows removed", "value": report["duplicate_rows_removed"]},
        {"metric": "Rows containing impossible values", "value": report["rows_with_impossible_values"]},
        {"metric": "Total values imputed", "value": sum(report["values_imputed"].values())},
        {"metric": "Completeness after cleaning (%)", "value": report["completeness_pct"]},
    ]
    return pd.DataFrame(rows)


if __name__ == "__main__":
    from .data_loader import load_raw

    raw = load_raw()
    clean, rep = clean_dataset(raw)
    print(quality_report_table(rep).to_string(index=False))

```

**What this file does:** Auditable historical cleaning with preserved original targets for temporal evaluation.


## `src/public_data.py`

```python
"""Real public-data companion: NOAA/Scripps Mauna Loa monthly CO2.

This track is NEVER merged with simulated city measurements. It preserves
source comments, source URL, SHA256 and retrieval time. Offline analysis uses
the bundled snapshot; --refresh downloads a new snapshot explicitly.
Run: python -m src.public_data [--refresh]
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen
import numpy as np
import pandas as pd
from . import config as cfg

URL = 'https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv'
PATH = cfg.RAW_DIR / 'noaa_co2_mm_mlo.csv'
CITATION = 'Xin Lan, NOAA/GML, and Ralph Keeling, Scripps Institution of Oceanography; https://gml.noaa.gov/ccgg/trends/data.html'


def download():
    """Download with a timeout; fail clearly rather than fabricate real data."""
    req = Request(URL, headers={'User-Agent':'ClimateTrendAnalyzer educational project'})
    with urlopen(req, timeout=45) as res:
        content = res.read()
    if b'year,month' not in content.replace(b' ',b''):
        raise ValueError('Unexpected NOAA response; expected a monthly CO2 CSV')
    PATH.write_bytes(content)
    meta = dict(source_url=URL, retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                sha256=hashlib.sha256(content).hexdigest(),citation=CITATION,
                license_note='NOAA public data: preserve source attribution and file usage notes; not relicensed under project MIT')
    (cfg.RAW_DIR/'noaa_provenance.json').write_text(json.dumps(meta,indent=2))


def analyze(refresh=False):
    if refresh or not PATH.exists():
        download()
    raw = pd.read_csv(PATH,comment='#',skipinitialspace=True)
    raw.columns = raw.columns.str.strip()
    raw['date'] = pd.to_datetime(dict(year=raw.year,month=raw.month,day=1))
    raw['average'] = pd.to_numeric(raw['average'],errors='coerce').mask(lambda s:s<0)
    # Complete, common analysis window. Do not silently compare incomplete years.
    d = raw[(raw.date>='1980-01-01') & (raw.date<='2024-12-01')].copy()
    d = d[['date','average']].rename(columns={'average':'co2_ppm'}).dropna()
    d['year']=d.date.dt.year
    annual = d.groupby('year',as_index=False).co2_ppm.agg(['mean','count']).reset_index()
    annual = annual[annual['count']==12].copy()
    from scipy.stats import linregress
    fit = linregress(annual.year,annual['mean'])
    summary = dict(dataset='NOAA/Scripps Mauna Loa monthly atmospheric CO2',
                   data_type='PUBLIC OBSERVATIONS, separate from synthetic city data',
                   n_months=len(d),start=str(d.date.min().date()),end=str(d.date.max().date()),
                   n_complete_years=len(annual),linear_slope_ppm_per_year=float(fit.slope),
                   first_complete_year_mean_ppm=float(annual['mean'].iloc[0]),
                   last_complete_year_mean_ppm=float(annual['mean'].iloc[-1]),
                   source=URL,citation=CITATION,
                   caveats='Station CO2 concentration in ppm, not emissions; linear summary of accelerating series. Source notes include measurement-site interruptions and interpolation.')
    d.to_csv(cfg.PROCESSED_DIR/'noaa_co2_monthly.csv',index=False)
    annual.to_csv(cfg.TABLES_DIR/'noaa_co2_annual.csv',index=False)
    (cfg.OUTPUTS_DIR/'noaa_summary.json').write_text(json.dumps(summary,indent=2))
    cfg.use_headless_backend()
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11,5))
    ax.plot(d.date,d.co2_ppm,color='#167d9a',lw=1,label='Public monthly observations')
    ax.plot(pd.to_datetime(annual.year.astype(str)+'-07-01'),annual['mean'],color='#c65d37',lw=2,label='Complete-year mean')
    ax.set(title='NOAA/Scripps Mauna Loa atmospheric CO2 — PUBLIC DATA, 1980–2024',xlabel='Date',ylabel='CO2 concentration (ppm)')
    ax.legend(); fig.tight_layout();fig.savefig(cfg.FIGURES_DIR/'16_public_noaa_co2.png',dpi=150);plt.close(fig)
    print(json.dumps(summary,indent=2))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh',action='store_true')
    args=parser.parse_args()
    analyze(args.refresh)

```

**What this file does:** Separate public NOAA CO2 ingestion, attribution, checksum and concentration analysis.


## `src/report_generator.py`

```python
"""
report_generator.py
===================
Builds the final deliverables:

* `outputs/reports/climate_trend_report.md`  - the written report (Markdown)
* `outputs/reports/climate_trend_report.html` - a self-contained HTML version
  (figures embedded as base64, so it can be shared as a single file)
* `docs/INSIGHTS.md`                           - the key-findings document
"""

from __future__ import annotations

import base64
import html
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import config as cfg


def _md_table(df: pd.DataFrame, float_fmt: str = "{:.3f}") -> str:
    """Render a DataFrame as a GitHub-flavoured Markdown table."""
    if df is None or df.empty:
        return "_No rows available._"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda v: "" if pd.isna(v) else float_fmt.format(v))
    header = "| " + " | ".join(str(c) for c in view.columns) + " |"
    sep = "| " + " | ".join("---" for _ in view.columns) + " |"
    rows = []
    for _, r in view.iterrows():
        rows.append("| " + " | ".join(str(v) for v in r.tolist()) + " |")
    return "\n".join([header, sep] + rows)


def build_markdown_report(bundle: dict) -> Path:
    """Write the full Markdown report."""
    out_path = cfg.REPORTS_DIR / "climate_trend_report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    eda = bundle["eda"]
    trends = bundle["trend_results"]["trends"]
    temp_trends = bundle["trend_results"]["temperature_trends"]
    anomalies = bundle["anomaly_results"]["anomalies"]
    fc = bundle["forecast_results"]
    clean_report = bundle["clean_report"]
    figs = bundle["figures"]
    numbers = bundle["key_numbers"]

    def rel(p: Path | None) -> str:
        if p is None:
            return ""
        try:
            return str(Path("..") / Path(p).relative_to(cfg.OUTPUTS_DIR)).replace("\\", "/")
        except ValueError:
            return str(p)

    md = []
    A = md.append

    A("# Climate Trend Analyzer - Analytical Report")
    A("")
    A(f"*Generated on {datetime.now().strftime('%d %B %Y, %H:%M')} by the "
      f"`Climate-Trend-Analyzer` pipeline (seed = {cfg.RANDOM_SEED}).*")
    A("")
    A("---")
    A("")

    # ---------------- executive summary ----------------
    A("## Executive Summary")
    A("")
    A(f"| Metric | Value |")
    A("| --- | --- |")
    A(f"| Records analysed | {numbers['rows_analysed']:,} monthly observations |")
    A(f"| Regions covered | {numbers['regions']} |")
    A(f"| Time span | {bundle['featured']['date'].min():%Y-%m} to {bundle['featured']['date'].max():%Y-%m} |")
    A(f"| Mean warming rate | {numbers['mean_warming_c_per_decade']:+.3f} °C per decade |")
    A(f"| Fastest warming region | {numbers['fastest_warming_region']} "
      f"({numbers['fastest_warming_c_per_decade']:+.3f} °C/decade) |")
    A(f"| Detector records (overlapping methods) | {numbers['anomalies_detected']:,} |")
    A(f"| Best forecast RMSE | {numbers['best_forecast_rmse']} °C |")
    A(f"| Post-cleaning completeness | {numbers['data_completeness_pct']:.2f} % |")
    A("")
    A(bundle["insights_text"].split("### 1.")[0].replace("## Key Findings", "").strip())
    A("")

    # ---------------- data quality ----------------
    A("## 1. Data Ingestion & Quality Control")
    A("")
    A(f"The raw file `data/raw/climate_raw.csv` was generated by the built-in simulator "
      f"(a virtual stand-in for a real station/portal feed) and contains "
      f"{clean_report['rows_in']:,} rows with deliberate defects: mixed date formats, "
      f"duplicated records, missing readings and physically impossible values.")
    A("")
    A(_md_table(pd.DataFrame([
        {"metric": "Rows loaded (raw)", "value": clean_report["rows_in"]},
        {"metric": "Unparseable dates removed", "value": clean_report["rows_unparseable_date"]},
        {"metric": "Duplicate rows removed", "value": clean_report["duplicate_rows_removed"]},
        {"metric": "Rows with impossible values", "value": clean_report["rows_with_impossible_values"]},
        {"metric": "Values imputed", "value": sum(clean_report["values_imputed"].values())},
        {"metric": "Rows in analysis table", "value": clean_report["rows_out"]},
        {"metric": "Completeness (%)", "value": clean_report["completeness_pct"]},
    ])))
    A("")
    if figs.get("raw"):
        A(f"![Raw data preview]({rel(figs['raw'])})")
        A("")
    if figs.get("quality"):
        A(f"![Data quality]({rel(figs['quality'])})")
        A("")

    # ---------------- EDA ----------------
    A("## 2. Exploratory Data Analysis")
    A("")
    A("### Descriptive statistics")
    A("")
    A(_md_table(eda["summary"].reset_index(names="indicator")))
    A("")
    A("### Correlation matrix")
    A("")
    A(_md_table(eda["correlations"].reset_index(names="indicator"), "{:.2f}"))
    A("")
    A("### Warmest years in the record")
    A("")
    A(_md_table(eda["warmest_years"].head(10)))
    A("")
    if figs.get("seasonal_profile"):
        A(f"![Seasonal profile]({rel(figs['seasonal_profile'])})")
        A("")
    if figs.get("yearly"):
        A(f"![Yearly comparison]({rel(figs['yearly'])})")
        A("")
    if figs.get("heatmap"):
        A(f"![Seasonal heatmap]({rel(figs['heatmap'])})")
        A("")

    # ---------------- trends ----------------
    A("## 3. Trend Analysis")
    A("")
    A("Ordinary Least Squares (parametric) and the Mann-Kendall test (non-parametric) "
      "were applied to every region x indicator combination.")
    A("")
    A("### Temperature trends")
    A("")
    A(_md_table(temp_trends))
    A("")
    if figs.get("temperature"):
        A(f"![Temperature trend]({rel(figs['temperature'])})")
        A("")
    if figs.get("warming_bar"):
        A(f"![Warming rate by region]({rel(figs['warming_bar'])})")
        A("")
    if figs.get("decomposition"):
        A(f"![Seasonal decomposition]({rel(figs['decomposition'])})")
        A("")
    if figs.get("rainfall"):
        A(f"![Rainfall trend]({rel(figs['rainfall'])})")
        A("")

    # ---------------- anomalies ----------------
    A("## 4. Anomaly Detection")
    A("")
    A(f"{len(anomalies):,} detector records were registered (methods can flag the same city-month) by the four-method ensemble. "
      f"The full register is saved to `outputs/tables/anomalies.csv`.")
    A("")
    A("### Anomalies per region")
    A("")
    A(_md_table(bundle["anomaly_results"]["summary"]))
    A("")
    A("### Ten most extreme anomalies")
    A("")
    A(_md_table(bundle["anomaly_results"].get("notable", pd.DataFrame())))
    A("")
    if figs.get("anomaly"):
        A(f"![Anomaly detection]({rel(figs['anomaly'])})")
        A("")
    if figs.get("anomaly_timeline"):
        A(f"![Anomaly timeline]({rel(figs['anomaly_timeline'])})")
        A("")
    if figs.get("extreme_events"):
        A(f"![Extreme events]({rel(figs['extreme_events'])})")
        A("")

    # ---------------- forecasting ----------------
    A("## 5. Forecasting")
    A("")
    A("Every model was scored on the same 60-month chronological validation window, then the winner "
      "was refit on the full series to project the next 36 months.")
    A("")
    A(_md_table(fc["metrics"]))
    A("")
    if figs.get("model_comparison"):
        A(f"![Model comparison]({rel(figs['model_comparison'])})")
        A("")
    if figs.get("forecast"):
        A(f"![Forecast]({rel(figs['forecast'])})")
        A("")

    # ---------------- drivers ----------------
    A("## 6. Drivers: CO2, Sea Level and Correlation Structure")
    A("")
    if figs.get("co2"):
        A(f"![CO2 vs temperature]({rel(figs['co2'])})")
        A("")
    if figs.get("sea_level"):
        A(f"![Sea level]({rel(figs['sea_level'])})")
        A("")

    # ---------------- insights ----------------
    A("## 7. Key Findings")
    A("")
    A(bundle["insights_text"].split("## Key Findings", 1)[-1].strip())
    A("")

    if bundle.get("public_data"):
        A("## Separate real public-data companion — NOAA/Scripps CO2")
        A("")
        A("Real public observations are analyzed independently, never joined to synthetic cities. Concentration is in ppm, not emissions. Source/citation and retrieval checksum are preserved in data/raw/noaa_provenance.json.")
        A("")
        if figs.get("public_noaa"):
            A(f"![Public CO2 observations]({rel(figs['public_noaa'])})")
        A("")

    # ---------------- limits ----------------
    A("## 8. Methodology Notes & Limitations")
    A("")
    A("- The input is a **simulated** dataset that reproduces realistic statistical "
      "structure; it is not an observational climate record.")
    A("- OLS uses monthly fixed effects and HAC(12) uncertainty. Full-model R² includes seasonality. "
      "MK is a descriptive cross-check without serial-dependence or multiple-testing adjustment.")
    A("- Forecasts are fixed-origin statistical extrapolations from end-2024, not physical climate-model projections. "
      "Model selection uses a validation block, not an independent test; non-ARIMA bands are approximate and uncalibrated.")
    A("- Anomaly thresholds (z > 2.5, |STL residual| > 2 sigma, IQR fences, "
      "2 % Isolation Forest contamination) are configurable in `src/config.py`.")
    A("")
    A("---")
    A("")
    A(f"*Report generated by `src/report_generator.py` - every number above is "
      f"reproduced by running `python main.py --step all`.*")

    out_path.write_text("\n".join(md), encoding="utf-8")
    print(f"[report] Markdown report -> {out_path}")
    return out_path


def build_html_report(bundle: dict) -> Path:
    """Write a self-contained HTML report (images embedded as base64)."""
    out_path = cfg.REPORTS_DIR / "climate_trend_report.html"
    numbers = bundle["key_numbers"]
    figs = bundle["figures"]

    def img(key: str, caption: str = "") -> str:
        p = figs.get(key)
        if not p or not Path(p).exists():
            return ""
        b64 = base64.b64encode(Path(p).read_bytes()).decode()
        cap = f'<figcaption>{html.escape(caption)}</figcaption>' if caption else ""
        return (f'<figure><img src="data:image/png;base64,{b64}" alt="{caption}">'
                f"{cap}</figure>")

    cards = [
        ("Records", f"{numbers['rows_analysed']:,}"),
        ("Regions", f"{numbers['regions']}"),
        ("Mean warming", f"{numbers['mean_warming_c_per_decade']:+.3f} °C/dec"),
        ("Fastest region", f"{numbers['fastest_warming_region']}"),
        ("Anomalies", f"{numbers['anomalies_detected']:,}"),
        ("Best RMSE", f"{numbers['best_forecast_rmse']} °C"),
    ]
    card_html = "".join(
        f'<div class="card"><div class="v">{v}</div><div class="k">{k}</div></div>'
        for k, v in cards
    )

    body = f"""
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Climate Trend Analyzer - Report</title>
<style>
  :root {{ --bg:#0f1720; --card:#182430; --accent:#4cc9f0; --text:#e8eef4; --muted:#93a4b5; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:0 0 60px; background:var(--bg); color:var(--text);
         font-family:'Segoe UI',system-ui,-apple-system,sans-serif; line-height:1.6; }}
  header {{ padding:44px 24px; background:linear-gradient(135deg,#102a43,#0f1720);
            border-bottom:3px solid var(--accent); }}
  header h1 {{ margin:0 0 6px; font-size:2.3rem; letter-spacing:.5px; }}
  header p {{ margin:0; color:var(--muted); }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:0 24px; }}
  .cards {{ display:flex; flex-wrap:wrap; gap:14px; margin:26px 0; }}
  .card {{ flex:1 1 150px; background:var(--card); border:1px solid #24384c;
           border-radius:10px; padding:16px; text-align:center; }}
  .card .v {{ font-size:1.5rem; font-weight:700; color:var(--accent); }}
  .card .k {{ font-size:.8rem; color:var(--muted); text-transform:uppercase; letter-spacing:1px; }}
  h2 {{ margin-top:42px; border-left:4px solid var(--accent); padding-left:12px; }}
  h3 {{ color:#bcd3e5; }}
  table {{ width:100%; border-collapse:collapse; margin:16px 0; font-size:.88rem; }}
  th,td {{ border:1px solid #24384c; padding:7px 9px; text-align:left; }}
  th {{ background:#1d2c3a; color:var(--accent); }}
  tr:nth-child(even) td {{ background:#141f2b; }}
  figure {{ margin:22px 0; }}
  img {{ width:100%; border-radius:8px; border:1px solid #24384c; }}
  figcaption {{ color:var(--muted); font-size:.85rem; margin-top:6px; }}
  pre {{ background:#0b1219; border:1px solid #24384c; border-radius:8px;
         padding:14px; overflow-x:auto; white-space:pre-wrap; font-size:.85rem; }}
  .note {{ background:#152534; border-left:4px solid #f0a500; padding:12px 16px;
           border-radius:6px; margin:18px 0; font-size:.9rem; }}
  footer {{ text-align:center; color:var(--muted); margin-top:60px; font-size:.82rem; }}
</style></head>
<body>
<header><div class="wrap">
  <h1>Climate Trend Analyzer</h1>
  <p>Analytical report - generated {datetime.now().strftime('%d %B %Y, %H:%M')} -
     Climate-Trend-Analyzer v1.0</p>
</div></header>
<div class="wrap">
  <div class="cards">{card_html}</div>

  <h2>Key Findings</h2>
  <pre>{html.escape(bundle['insights_text'])}</pre>

  <h2>Real public-data companion — NOAA/Scripps CO2</h2>
  <p>Public observations are analyzed separately; no simulated city is presented as real.</p>
  {img('public_noaa', 'Mauna Loa CO2 concentration — real public observations, not emissions')}
  <h2>Temperature trend by region — SYNTHETIC</h2>
  {img('temperature', 'Fig. 1 - Monthly temperature with 12-month rolling mean, all regions')}
  {img('warming_bar', 'Fig. 2 - OLS warming rate per region with 95% confidence interval')}
  {img('decomposition', 'Fig. 3 - STL decomposition: trend, seasonality and residuals')}

  <h2>Seasonality</h2>
  {img('seasonal_profile', 'Fig. 4 - Seasonal cycle of temperature and rainfall')}
  {img('heatmap', 'Fig. 5 - Month x year temperature anomaly heatmap')}
  {img('yearly', 'Fig. 6 - Yearly mean temperature comparison')}

  <h2>Anomaly detection</h2>
  {img('anomaly', 'Fig. 7 - Detected hot and cold anomalies in the time series')}
  {img('anomaly_timeline', 'Fig. 8 - Anomaly count per region and year')}
  {img('extreme_events', 'Fig. 9 - Heat wave and drought months per decade')}

  <h2>Drivers</h2>
  {img('co2', 'Fig. 10 - CO2 concentration vs mean temperature')}
  {img('sea_level', 'Fig. 11 - Global mean sea level trend')}
  {img('rainfall', 'Fig. 12 - Annual rainfall totals with fitted trend')}

  <h2>Forecasting</h2>
  {img('model_comparison', 'Fig. 13 - Forecast error by model')}
  {img('forecast', 'Fig. 14 - Historical series and 36-month forecast with interval')}

  <div class="note"><b>Scope note:</b> the source dataset is a high-fidelity simulation
  produced by the project's own generator. It reproduces seasonality, autocorrelation,
  long-term trends and extreme events, but it is not an observational climate record.
  The pipeline is designed so a real public dataset (NASA GISTEMP, NOAA, Our World in Data)
  requires a source-specific adapter that preserves real measurements, units and coverage.</div>

  <h2>Trend statistics</h2>
  <pre>{html.escape(bundle['trend_results']['temperature_trends'].round(4).to_string(index=False))}</pre>

  <footer>Built with the Climate-Trend-Analyzer pipeline &middot; pandas, NumPy,
  scikit-learn, statsmodels, Matplotlib, Seaborn, Plotly, Streamlit</footer>
</div></body></html>"""
    out_path.write_text(body, encoding="utf-8")
    print(f"[report] HTML report -> {out_path}")
    return out_path


def write_insights_doc(bundle: dict) -> Path:
    """Save the key findings as a standalone document under `docs/`."""
    out_path = cfg.DOCS_DIR / "INSIGHTS.md"
    out_path.write_text(
        "# Key Findings - Climate Trend Analyzer\n\n" + bundle["insights_text"],
        encoding="utf-8",
    )
    print(f"[report] Insights doc -> {out_path}")
    return out_path

```

**What this file does:** Markdown and embedded-image HTML report assembly.


## `src/trend_analysis.py`

```python
"""
trend_analysis.py
=================
**Long-term climate trend estimation.**

Two complementary, industry-standard methods are used:

1. **Ordinary Least Squares (OLS) regression** of the indicator on time.
   Gives a slope in units per month, an R^2 and a p-value, and is easy to
   explain in an interview.

2. **Mann-Kendall test** (non-parametric, deseasonalised; no pre-whitening).
   It does *not* assume linearity and is the test used by IPCC/NOAA-style
   climate reports.  We implement it from scratch (no extra dependency) so
   the logic is fully visible.

3. **Seasonal decomposition** (STL / classical additive) splits a series into
   trend + seasonality + residual, which is the base for the anomaly detector.

Everything is returned as tidy DataFrames so it can be exported and charted.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from . import config as cfg


# --------------------------------------------------------------------------
# 0. Seasonal pre-adjustment
# --------------------------------------------------------------------------
def deseasonalize(series: pd.Series, months=None, period: int = 12) -> pd.Series:
    """
    Remove the seasonal cycle from a monthly series.

    For every calendar month the mean is subtracted, leaving a series that
    contains **only** the long-term signal plus noise.

    Why this matters (a classic climate-analysis pitfall):
    a raw monthly temperature series swings +/- 12 °C between summer and
    winter.  A trend test run directly on it is dominated by that seasonal
    ordering and can even report the *wrong direction* - which is exactly
    why the IPCC-style approach is to deseasonalise first (or to test annual
    means).  Every trend statistic in this module is therefore computed on
    the deseasonalised series, and the raw R^2 is reported alongside for
    transparency.
    """
    s = series.dropna()
    if len(s) < 2 * period:
        return s
    if months is None:
        m = np.arange(len(s)) % period
    elif isinstance(months, pd.Series):
        m = months.reindex(s.index).to_numpy()
        m = np.nan_to_num(m, nan=1).astype(int)
    else:
        m = np.asarray(months)
    values = s.to_numpy(dtype=float)
    seasonal = pd.Series(values).groupby(m).transform("mean").to_numpy()
    return pd.Series(values - seasonal, index=s.index)


# --------------------------------------------------------------------------
# 1. OLS trend  (regression with seasonal fixed effects)
# --------------------------------------------------------------------------
def ols_trend(series: pd.Series, months=None, period: int = 12) -> dict:
    """
    Estimate the long-term trend with a **seasonal fixed-effects regression**:

        value_t = b0 + b1 * t  +  sum_k (month_dummy_k)  +  error_t

    Why not a plain regression on the raw series?
    A monthly temperature series swings by up to 12 °C between summer and
    winter.  Regressing it on time alone mixes the seasonal cycle into the
    trend estimate (and produces a tiny R^2).  Adding month dummies lets the
    model absorb the seasonal cycle, so `b1` is a clean estimate of the
    long-term trend - this is the same idea as "regression with seasonal
    fixed effects" used in official climate statistics.

    `slope` is per observation step; for monthly data we convert it to
    **degrees per year** and **degrees per decade**, which is how climate
    reports express warming.
    """
    raw = series.dropna()
    if len(raw) < 2 * period:
        return {
            "slope_per_year": np.nan, "slope_per_decade": np.nan,
            "intercept": np.nan, "r_squared": np.nan, "r_squared_raw": np.nan,
            "p_value": np.nan, "ci_low": np.nan, "ci_high": np.nan, "n": int(len(raw)),
        }

    # --- align the month vector with the (possibly dropped) observations ---
    if months is None:
        m = np.arange(len(raw)) % period
    elif isinstance(months, pd.Series):
        m = months.reindex(raw.index).to_numpy()
        m = np.nan_to_num(m, nan=1).astype(int)
    else:
        m = np.asarray(months)

    n = len(raw)
    y = raw.to_numpy(dtype=float)
    t = np.arange(n, dtype=float)

    # design matrix: intercept + time + 11 month dummies (one is dropped)
    D = np.zeros((n, period - 1))
    for k in range(1, period):
        D[:, k - 1] = (m == k).astype(float)
    X = np.column_stack([np.ones(n), t, D])

    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    y_hat = X @ beta
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))

    # Newey-West/HAC covariance acknowledges serial dependence and unequal
    # variance. The slope is still OLS; its uncertainty is HAC robust.
    import statsmodels.api as sm
    robust = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags":12}, use_t=True)
    se = float(robust.bse[1])
    slope_per_year = float(beta[1] * 12.0)
    p_value = float(robust.pvalues[1])
    bounds = np.asarray(robust.conf_int())[1] * 12
    ci = float((bounds[1]-bounds[0])/2)

    # R^2 of a plain (seasonal) regression - reported for transparency only
    raw_res = stats.linregress(t, y)

    return {
        "slope_per_year": slope_per_year,
        "slope_per_decade": slope_per_year * 10,
        "intercept": float(beta[0]),
        "r_squared": float(1 - ss_res / ss_tot) if ss_tot else np.nan,
        "r_squared_raw": float(raw_res.rvalue ** 2),
        "p_value": p_value,
        "ci_low": float(slope_per_year - ci),
        "ci_high": float(slope_per_year + ci),
        "n": int(n),
    }


# --------------------------------------------------------------------------
# 2. Mann-Kendall test (implemented from scratch)
# --------------------------------------------------------------------------
def mann_kendall(series: pd.Series, months=None, period: int = 12) -> dict:
    """
    Non-parametric trend test, applied to the *deseasonalised* series.

    Steps
    -----
    1. Compute the sign of every pair difference -> S statistic
    2. Variance of S under the null hypothesis (no trend)
    3. Z score -> two sided p-value (normal approximation)
    4. Theil-Sen slope (median of all pairwise slopes) as the trend size
    """
    deseason = deseasonalize(series, months=months, period=period)
    s = deseason.to_numpy(dtype=float)
    n = len(s)
    if n < 10:
        return {"mk_trend": "insufficient data", "mk_s": np.nan, "mk_z": np.nan,
                "mk_p_value": np.nan, "theil_sen_slope_per_year": np.nan}

    # S statistic:  S = sum_{i<j} sign(x_j - x_i)
    # (note the order - a rising series must give a POSITIVE S)
    diff_sign = np.sign(s[None, :] - s[:, None])
    S = int(np.sum(np.triu(diff_sign, k=1)))

    # Variance with tie correction
    unique_x, counts = np.unique(s, return_counts=True)
    tie_term = 0.0
    for c in counts:
        if c > 1:
            tie_term += c * (c - 1) * (2 * c + 5)
    var_s = (n * (n - 1) * (2 * n + 5) - tie_term) / 18.0

    if S > 0:
        z = (S - 1) / np.sqrt(var_s)
    elif S < 0:
        z = (S + 1) / np.sqrt(var_s)
    else:
        z = 0.0
    p = 2 * stats.norm.sf(abs(z))

    # Theil-Sen slope (median of pairwise slopes) -> per year
    idx = np.arange(n)
    i, j = np.triu_indices(n, k=1)
    slopes = (s[j] - s[i]) / (idx[j] - idx[i])
    theil_sen = float(np.median(slopes) * 12.0)

    trend = "increasing" if p < 0.05 and S > 0 else ("decreasing" if p < 0.05 and S < 0 else "no significant trend")
    return {
        "mk_trend": trend,
        "mk_s": S,
        "mk_z": float(z),
        "mk_p_value": float(p),
        "theil_sen_slope_per_year": theil_sen,
    }


# --------------------------------------------------------------------------
# 3. Seasonal decomposition
# --------------------------------------------------------------------------
def seasonal_decomposition(series: pd.Series, period: int = 12) -> pd.DataFrame:
    """
    Additive decomposition into trend / seasonal / residual.

    Uses `statsmodels` when available and falls back to a simple
    moving-average + month-demeaning implementation otherwise.
    """
    s = series.dropna()
    idx = s.index
    try:
        from statsmodels.tsa.seasonal import STL

        stl = STL(pd.Series(s.to_numpy(), index=pd.RangeIndex(len(s))),
                  period=period, robust=True)
        res = stl.fit()
        out = pd.DataFrame(
            {
                "date": idx,
                "observed": s.to_numpy(),
                "trend": res.trend,
                "seasonal": res.seasonal,
                "resid": res.resid,
            }
        )
        return out
    except Exception:  # pragma: no cover - fallback path
        values = s.to_numpy(dtype=float)
        trend = pd.Series(values).rolling(12, center=True, min_periods=6).mean().bfill().ffill()
        detr = values - trend
        seasonal = pd.Series(detr).groupby(np.arange(len(s)) % period).mean()
        seasonal = seasonal.to_numpy()[np.arange(len(s)) % period]
        resid = values - trend - seasonal
        return pd.DataFrame(
            {"date": idx, "observed": values, "trend": trend, "seasonal": seasonal, "resid": resid}
        )


# --------------------------------------------------------------------------
# 4. Region-level trend analysis
# --------------------------------------------------------------------------
def analyze_trends(df: pd.DataFrame, indicators=None) -> pd.DataFrame:
    """
    Compute OLS + Mann-Kendall trends for every (region, indicator) pair.

    All statistics are computed on the **deseasonalised** series (calendar
    month means removed) - see `deseasonalize()` for why.  The raw R^2 is kept
    as `r_squared_raw` for transparency.

    Returns a tidy table: one row per region x indicator.
    """
    indicators = indicators or ["temp_mean_c", "rainfall_mm", "co2_ppm", "sea_level_mm", "humidity_pct"]
    rows = []

    for region, grp in df.groupby("region"):
        grp = grp.sort_values("date")
        for ind in indicators:
            if ind not in grp.columns:
                continue
            stats_ols = ols_trend(grp[ind], months=grp["month"])
            stats_mk = mann_kendall(grp[ind], months=grp["month"])
            rows.append(
                {
                    "region": region,
                    "indicator": ind,
                    "slope_per_year": stats_ols["slope_per_year"],
                    "slope_per_decade": stats_ols["slope_per_decade"],
                    "ci_low": stats_ols["ci_low"],
                    "ci_high": stats_ols["ci_high"],
                    "r_squared": stats_ols["r_squared"],
                    "r_squared_raw": stats_ols["r_squared_raw"],
                    "p_value": stats_ols["p_value"],
                    "significance": "significant" if stats_ols["p_value"] < 0.05 else "not significant",
                    "trend_basis": "OLS month fixed effects; HAC(12) CI; MK deseasonalised",
                    **stats_mk,
                }
            )
    return pd.DataFrame(rows).round(6)


def temperature_trend_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Temperature trends only, ranked by warming rate (the headline result)."""
    t = analyze_trends(df, ["temp_mean_c"])
    t = t[t["indicator"] == "temp_mean_c"].copy()
    return t.sort_values("slope_per_decade", ascending=False).reset_index(drop=True)


def warming_by_decade(df: pd.DataFrame) -> pd.DataFrame:
    """Mean temperature anomaly per decade (and per region)."""
    out = (
        df.groupby(["region", "decade"])
        .agg(temp_anomaly=("temp_anomaly", "mean"),
             temp_mean=("temp_mean_c", "mean"),
             rainfall=("rainfall_mm", "mean"),
             extreme_events=("extreme_event", "sum"))
        .reset_index()
    )
    return out.round(3)


def run_trend_analysis(df: pd.DataFrame) -> dict:
    """Full trend analysis bundle."""
    trends = analyze_trends(df)
    return {
        "trends": trends,
        "temperature_trends": temperature_trend_summary(df),
        "by_decade": warming_by_decade(df),
        "decomposition": seasonal_decomposition(
            df[df["region"] == df["region"].iloc[0]].sort_values("date").set_index("date")["temp_mean_c"]
        ),
    }


if __name__ == "__main__":
    from .data_loader import load_featured

    res = run_trend_analysis(load_featured())
    print(res["temperature_trends"].to_string(index=False))

```

**What this file does:** Season-controlled OLS with HAC uncertainty and exploratory MK/Theil–Sen cross-checks.


## `src/visualizations.py`

```python
"""
visualizations.py
=================
**Every figure used by the project**, in one place.

Design rules followed here (they are what makes a portfolio project look
professional):

* one shared colour palette, applied consistently across all charts
* every chart has a title, axis labels with units and a legend
* raw series are always drawn light, the smoothed/trend series bold on top
* files are saved as PNG (150 dpi) into `outputs/figures/` with descriptive
  names, so the README can reference them directly.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

from . import config as cfg

cfg.use_headless_backend()

import matplotlib.pyplot as plt  # noqa: E402
import seaborn as sns  # noqa: E402

# --------------------------------------------------------------------------
# Shared style
# --------------------------------------------------------------------------
PALETTE = ["#1f77b4", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd",
           "#8c564b", "#e377c2", "#17becf", "#bcbd22", "#7f7f7f"]
REGION_COLORS = dict(zip(cfg.REGION_NAMES, PALETTE))

sns.set_theme(style="whitegrid", context="notebook",
              font_scale=1.1, palette=PALETTE)


def _save(fig, name: str, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or cfg.FIGURES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[viz] saved {path.name}")
    return path


def _region_color(region: str) -> str:
    return REGION_COLORS.get(region, PALETTE[0])


# ==========================================================================
# 1. DATA QUALITY
# ==========================================================================
def plot_data_quality(raw: pd.DataFrame, cleaned: pd.DataFrame) -> Path:
    """Missing values before vs. after cleaning (the 'proof of cleaning')."""
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))

    cols = [c for c in cfg.CLIMATE_COLUMNS if c in raw.columns]
    before = raw[cols].isna().sum()
    after = cleaned[cols].isna().sum()

    x = np.arange(len(cols))
    width = 0.38
    axes[0].bar(x - width / 2, before.values, width, label="Before cleaning",
                color="#d62728", alpha=0.85)
    axes[0].bar(x + width / 2, after.values, width, label="After cleaning",
                color="#2ca02c", alpha=0.85)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([c.replace("_", "\n") for c in cols], fontsize=9)
    axes[0].set_ylabel("Missing values (count)")
    axes[0].set_title("Missing Values: Before vs. After Cleaning")
    axes[0].legend()

    # correlation heatmap of the clean data
    corr_cols = [c for c in cfg.CLIMATE_COLUMNS if c in cleaned.columns]
    corr = cleaned[corr_cols].corr()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm",
                center=0, ax=axes[1], square=True, linewidths=0.5)
    axes[1].set_title("Correlation Matrix of Climate Indicators")

    return _save(fig, "01_data_quality.png")


def plot_raw_preview(raw: pd.DataFrame) -> Path:
    """What the raw file looks like (screenshot-worthy proof of the source)."""
    fig, ax = plt.subplots(figsize=(14, 5))
    subset = raw.head(60).copy()
    ax.plot(range(len(subset)), subset["temp_mean_c"], marker="o", linestyle="-",
            color="#1f77b4", alpha=0.8, label="temp_mean_c")
    ax.plot(range(len(subset)), subset["rainfall_mm"], marker="s", linestyle="-",
            color="#2ca02c", alpha=0.6, label="rainfall_mm")
    ax.set_title("Raw (uncleaned) Dataset - First 60 Records")
    ax.set_xlabel("Record index")
    ax.set_ylabel("Value (mixed units)")
    ax.legend()
    return _save(fig, "00_raw_data_preview.png")


# ==========================================================================
# 2. TREND FIGURES
# ==========================================================================
def plot_temperature_trend(df: pd.DataFrame) -> Path:
    """Multi-region temperature trend with a 12-month rolling mean."""
    fig, ax = plt.subplots(figsize=(15, 7))
    for region, grp in df.groupby("region"):
        g = grp.sort_values("date")
        ax.plot(g["date"], g["temp_mean_c"], alpha=0.25, lw=0.9,
                color=_region_color(region))
        roll = g["temp_mean_c"].rolling(12, center=True, min_periods=6).mean()
        ax.plot(g["date"], roll, lw=2.4, color=_region_color(region),
                label=f"{region} (12-mo mean)")
    ax.set_title("SYNTHETIC Temperature Trend by Region (1980-2024)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Mean temperature (°C)")
    ax.legend(ncol=3, fontsize=9)
    ax.axhline(0, color="grey", ls=":", lw=1)
    return _save(fig, "02_temperature_trend.png")


def plot_rainfall_trend(df: pd.DataFrame) -> Path:
    """Annual rainfall totals per region with the fitted trend line."""
    from scipy import stats as st

    fig, ax = plt.subplots(figsize=(15, 7))
    yearly = df.groupby(["region", "year"])["rainfall_mm"].sum().reset_index()
    for region, g in yearly.groupby("region"):
        g = g.sort_values("year")
        ax.plot(g["year"], g["rainfall_mm"], marker="o", ms=4, alpha=0.55,
                color=_region_color(region))
        if len(g) > 3:
            slope, intercept, r, p, _ = st.linregress(g["year"], g["rainfall_mm"])
            x = np.linspace(g["year"].min(), g["year"].max(), 50)
            ax.plot(x, intercept + slope * x, lw=2.2, color=_region_color(region),
                    label=f"{region} trend ({slope:+.1f} mm/yr, p={p:.3f})")
    ax.set_title("Annual Rainfall Total with Linear Trend (per Region)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Annual rainfall total (mm)")
    ax.legend(fontsize=9, ncol=2)
    return _save(fig, "03_rainfall_trend.png")


def plot_seasonal_heatmap(df: pd.DataFrame) -> Path:
    """Month x Year heatmap of temperature anomalies (the classic climate chart)."""
    fig, axes = plt.subplots(1, 2, figsize=(18, 7), sharey=True)
    for ax, region in zip(axes, sorted(df["region"].unique())[:2]):
        g = df[df["region"] == region]
        piv = g.pivot_table(index="month", columns="year", values="temp_anomaly")
        sns.heatmap(piv, cmap="RdBu_r", center=0, ax=ax, cbar=ax is axes[1],
                    cbar_kws={"label": "Temperature anomaly (°C)"} if ax is axes[1] else None)
        ax.set_title(f"Temperature Anomaly Heatmap - {region}")
        ax.set_xlabel("Year")
        ax.set_ylabel("Month")
    return _save(fig, "04_seasonal_heatmap.png")


def plot_seasonal_profile(df: pd.DataFrame) -> Path:
    """Average temperature / rainfall per calendar month (all regions)."""
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.5))
    months = list(range(1, 13))
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    prof = df.groupby("month")["temp_mean_c"].mean()
    axes[0].plot(months, prof.values, marker="o", color="#d62728", lw=2.4)
    axes[0].fill_between(months, prof.values, alpha=0.15, color="#d62728")
    axes[0].set_xticks(months); axes[0].set_xticklabels(names)
    axes[0].set_title("Average Temperature by Calendar Month")
    axes[0].set_ylabel("Mean temperature (°C)"); axes[0].set_xlabel("Month")

    prof = df.groupby("month")["rainfall_mm"].mean()
    axes[1].bar(months, prof.values, color="#1f77b4", alpha=0.85)
    axes[1].set_xticks(months); axes[1].set_xticklabels(names)
    axes[1].set_title("Average Rainfall by Calendar Month")
    axes[1].set_ylabel("Mean rainfall (mm)"); axes[1].set_xlabel("Month")

    for region, g in df.groupby("region"):
        prof = g.groupby("month")["temp_mean_c"].mean()
        axes[2].plot(months, prof.values, marker="o", lw=1.8,
                     color=_region_color(region), label=region)
    axes[2].set_xticks(months); axes[2].set_xticklabels(names)
    axes[2].set_title("Seasonal Cycle by Region")
    axes[2].set_ylabel("Mean temperature (°C)"); axes[2].set_xlabel("Month")
    axes[2].legend(fontsize=8, ncol=2)
    return _save(fig, "05_seasonal_profile.png")


def plot_yearly_comparison(df: pd.DataFrame) -> Path:
    """Yearly mean temperature per region + the global mean line."""
    fig, axes = plt.subplots(1, 2, figsize=(18, 6))
    yearly = df.groupby(["region", "year"])["temp_mean_c"].mean().reset_index()
    for region, g in yearly.groupby("region"):
        axes[0].plot(g["year"], g["temp_mean_c"], marker="o", ms=3, lw=1.6,
                     color=_region_color(region), label=region)
    gy = df.groupby("year")["temp_mean_c"].mean()
    axes[0].plot(gy.index, gy.values, lw=3, color="black", label="Unweighted city mean")
    axes[0].set_title("Yearly Mean Temperature by Region (1980-2024)")
    axes[0].set_xlabel("Year"); axes[0].set_ylabel("Mean temperature (°C)")
    axes[0].legend(fontsize=8, ncol=2)

    axes[1].bar(gy.index, gy.values, color="#ff7f0e", alpha=0.75)
    axes[1].axhline(gy.mean(), color="black", ls="--", lw=1.5,
                    label=f"Mean {gy.mean():.2f}°C")
    axes[1].set_title("Unweighted Five-City Mean per Year — SYNTHETIC")
    axes[1].set_xlabel("Year"); axes[1].set_ylabel("Mean temperature (°C)")
    axes[1].legend(fontsize=9)
    axes[1].tick_params(axis="x", rotation=60)
    return _save(fig, "06_yearly_comparison.png")


def plot_regional_warming_bar(trends: pd.DataFrame) -> Path:
    """Headline chart: warming rate (°C/decade) per region with error bars."""
    t = trends[trends["indicator"] == "temp_mean_c"].copy()
    t = t.sort_values("slope_per_decade")
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = ["#d62728" if v > 0 else "#1f77b4" for v in t["slope_per_decade"]]
    err = (t["ci_high"] - t["ci_low"]).abs() / 2 * 10
    ax.barh(t["region"], t["slope_per_decade"], xerr=err, color=colors, alpha=0.85,
            capsize=4, edgecolor="black", linewidth=0.6)
    ax.axvline(0, color="black", lw=1)
    ax.set_title("Warming Rate by Region (OLS trend, HAC-robust 95% CI, °C per decade)")
    ax.set_xlabel("Temperature change (°C per decade)")
    for y, v in enumerate(t["slope_per_decade"]):
        ax.text(v + (0.005 if v >= 0 else -0.005), y, f"{v:+.3f}",
                va="center", ha="left" if v >= 0 else "right", fontsize=10)
    return _save(fig, "07_warming_rate_by_region.png")


def plot_decomposition(decomp: pd.DataFrame, region: str = "") -> Path:
    """Trend / seasonal / residual decomposition of the temperature series."""
    fig, axes = plt.subplots(4, 1, figsize=(15, 10), sharex=True)
    axes[0].plot(decomp["date"], decomp["observed"], color="#1f77b4", lw=1.0)
    axes[0].set_title(f"Observed temperature {region}".strip())
    axes[0].set_ylabel("°C")
    axes[1].plot(decomp["date"], decomp["trend"], color="#d62728", lw=2.0)
    axes[1].set_title("Trend component (STL)"); axes[1].set_ylabel("°C")
    axes[2].plot(decomp["date"], decomp["seasonal"], color="#2ca02c", lw=1.4)
    axes[2].set_title("Seasonal component"); axes[2].set_ylabel("°C")
    axes[3].plot(decomp["date"], decomp["resid"], color="#7f7f7f", lw=0.9)
    axes[3].axhline(0, color="black", ls=":", lw=1)
    axes[3].set_title("Residual (noise + anomalies)"); axes[3].set_ylabel("°C")
    axes[3].set_xlabel("Date")
    return _save(fig, "08_seasonal_decomposition.png")


# ==========================================================================
# 3. ANOMALY FIGURES
# ==========================================================================
def plot_anomaly_detection(df: pd.DataFrame, anomalies: pd.DataFrame) -> Path:
    """Time series with the detected anomalies highlighted."""
    region = sorted(df["region"].unique())[0]
    g = df[df["region"] == region].sort_values("date")
    fig, ax = plt.subplots(figsize=(16, 7))

    ax.plot(g["date"], g["temp_mean_c"], color="#1f77b4", lw=1.0, label="Monthly temperature")
    ax.plot(g["date"], g["temp_mean_c"].rolling(12, center=True, min_periods=6).mean(),
            color="black", lw=2.2, label="12-month rolling mean")

    a = anomalies[(anomalies["region"] == region) & (anomalies["variable"] == "temp_mean_c")]
    hot = a[a["direction"] == "hot"]
    cold = a[a["direction"] == "cold"]
    ax.scatter(hot["date"], hot["value"], s=95, color="#d62728", zorder=5,
               edgecolor="black", linewidth=0.5, label="Hot anomalies")
    ax.scatter(cold["date"], cold["value"], s=95, color="#1f77b4", zorder=5,
               edgecolor="black", linewidth=0.5, label="Cold anomalies")

    ax.set_title(f"Climate Anomaly Detection - {region}")
    ax.set_xlabel("Date"); ax.set_ylabel("Mean temperature (°C)")
    ax.legend(fontsize=9)
    return _save(fig, "09_anomaly_detection.png")


def plot_anomaly_timeline(anomalies: pd.DataFrame) -> Path:
    """Heatmap: how many anomalies occurred per year and region."""
    if anomalies.empty:
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.text(0.5, 0.5, "No anomalies detected", ha="center", va="center")
        return _save(fig, "10_anomaly_timeline.png")

    fig, ax = plt.subplots(figsize=(15, 6))
    piv = anomalies.pivot_table(index="region", columns=anomalies["date"].dt.year,
                                values="anomaly_id", aggfunc="count", fill_value=0)
    sns.heatmap(piv, cmap="YlOrRd", ax=ax, annot=True, fmt="d",
                cbar_kws={"label": "Number of anomalies"})
    ax.set_title("Anomaly Count by Region and Year")
    ax.set_xlabel("Year"); ax.set_ylabel("Region")
    return _save(fig, "10_anomaly_timeline.png")


def plot_extreme_events(df: pd.DataFrame) -> Path:
    """Heat waves and droughts per decade - the 'impact' chart."""
    fig, ax = plt.subplots(figsize=(13, 6))
    piv = df.pivot_table(index="region", columns="decade", values="extreme_event",
                         aggfunc="sum", fill_value=0)
    sns.heatmap(piv, cmap="magma", ax=ax, annot=True, fmt="d",
                cbar_kws={"label": "Extreme-event months"})
    ax.set_title("Extreme Climate Events (Heat Waves + Droughts) per Decade")
    ax.set_xlabel("Decade"); ax.set_ylabel("Region")
    return _save(fig, "11_extreme_events_by_decade.png")


# ==========================================================================
# 4. RELATIONSHIP / DRIVER FIGURES
# ==========================================================================
def plot_co2_vs_temperature(df: pd.DataFrame) -> Path:
    """CO2 vs temperature with a regression line (the key driver relationship)."""
    from scipy import stats as st

    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5))
    for region, g in df.groupby("region"):
        axes[0].scatter(g["co2_ppm"], g["temp_mean_c"], s=8, alpha=0.35,
                        color=_region_color(region), label=region)
    gy = df.groupby("date")[["co2_ppm", "temp_mean_c"]].mean().reset_index()
    slope, intercept, r, p, _ = st.linregress(gy["co2_ppm"], gy["temp_mean_c"])
    x = np.linspace(gy["co2_ppm"].min(), gy["co2_ppm"].max(), 50)
    axes[0].plot(x, intercept + slope * x, color="black", lw=2.4,
                 label=f"Five-city fit: R²={r**2:.3f}, p={p:.2e}")
    axes[0].set_title("CO₂ Concentration vs Mean Temperature")
    axes[0].set_xlabel("CO₂ (ppm)"); axes[0].set_ylabel("Mean temperature (°C)")
    axes[0].legend(fontsize=8, ncol=2)

    axes[1].plot(gy["date"], gy["co2_ppm"], color="#7f7f7f", lw=2.4)
    axes[1].set_title("Atmospheric CO₂ Concentration vs Temperature")
    axes[1].set_xlabel("Date"); axes[1].set_ylabel("CO₂ (ppm)")
    ax_right = axes[1].twinx()
    ax_right.plot(gy["date"], gy["temp_mean_c"], color="#d62728", lw=2.4)
    ax_right.set_ylabel("Mean temperature (°C)", color="#d62728")
    return _save(fig, "12_co2_vs_temperature.png")


def plot_sea_level_rise(df: pd.DataFrame) -> Path:
    """Sea-level trend (mm) - the slow, high-stakes climate indicator."""
    from scipy import stats as st

    fig, ax = plt.subplots(figsize=(14, 6))
    gy = df.groupby("date")["sea_level_mm"].mean().reset_index()
    ax.plot(gy["date"], gy["sea_level_mm"], color="#1f77b4", lw=1.8)
    slope, intercept, r, p, _ = st.linregress(np.arange(len(gy)), gy["sea_level_mm"])
    fit = intercept + slope * np.arange(len(gy))
    ax.plot(gy["date"], fit, color="#d62728", lw=2.4, ls="--",
            label=f"Trend: {slope*12:+.2f} mm/yr (R²={r**2:.3f})")
    ax.set_title("Global Mean Sea Level Change (relative to 1980 baseline)")
    ax.set_xlabel("Date"); ax.set_ylabel("Sea level (mm)")
    ax.legend()
    return _save(fig, "13_sea_level_rise.png")


# ==========================================================================
# 5. FORECAST FIGURES
# ==========================================================================
def plot_forecast(result: dict, region: str | None = None) -> Path:
    """History + forecast + prediction interval for one region."""
    if not result:
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.text(0.5, 0.5, "Forecasting skipped", ha="center", va="center")
        return _save(fig, "14_forecast.png")

    res = next((r for r in result["results"] if region is None or r["region"] == region),
               result["results"][0])
    hist = res["history"]
    fc = res["forecast"]

    fig, ax = plt.subplots(figsize=(15, 7))
    ax.plot(hist["date"], hist["temp_mean_c"], color="#1f77b4", lw=1.3, label="Historical")
    tail = hist.tail(60)
    ax.plot(tail["date"], tail["temp_mean_c"].rolling(12, center=True, min_periods=3).mean(),
            color="black", lw=2.0, label="12-mo rolling mean")
    ax.plot(fc["date"], fc["prediction"], color="#d62728", lw=2.6, ls="--",
            label=f"Forecast - {res['best_model']}")
    if "ci_low" in fc and fc["ci_low"].notna().any():
        ax.fill_between(fc["date"], fc["ci_low"], fc["ci_high"],
                        color="#d62728", alpha=0.15, label="Approximate 95% prediction band")
    ax.axvline(hist["date"].max(), color="grey", ls=":", lw=1.4)
    ax.set_title(f"Climate Forecast - {res['region']} "
                 f"({len(fc)} months ahead, model: {res['best_model']})")
    ax.set_xlabel("Date"); ax.set_ylabel("Mean temperature (°C)")
    ax.legend(fontsize=9)
    return _save(fig, "14_forecast.png")


def plot_model_comparison(metrics: pd.DataFrame) -> Path:
    """Accuracy of each forecasting model - proves the model choice."""
    fig, axes = plt.subplots(1, 2, figsize=(17, 6))
    if metrics.empty:
        fig.text(0.5, 0.5, "No metrics available", ha="center")
        return _save(fig, "15_model_comparison.png")

    agg = metrics.groupby("model")[["MAE", "RMSE"]].mean().sort_values("RMSE")
    agg.plot(kind="bar", ax=axes[0], color=["#1f77b4", "#d62728"])
    axes[0].set_title("Average Forecast Error by Model (lower = better)")
    axes[0].set_ylabel("Error (°C)")
    axes[0].set_xlabel("Model")
    axes[0].legend(title="Metric")
    axes[0].tick_params(axis="x", rotation=20)

    best = metrics.loc[metrics.groupby("region")["RMSE"].idxmin()]
    axes[1].bar(best["region"], best["RMSE"], color="#2ca02c", alpha=0.85)
    axes[1].set_title("Best Model RMSE per Region")
    axes[1].set_ylabel("RMSE (°C)"); axes[1].set_xlabel("Region")
    for x, v in enumerate(best["RMSE"]):
        axes[1].text(x, v, f"{v:.3f}", ha="center", va="bottom", fontsize=9)
    return _save(fig, "15_model_comparison.png")


# ==========================================================================
# 6. ARCHITECTURE DIAGRAM (for the README)
# ==========================================================================
def plot_architecture_diagram() -> Path:
    """A clean block diagram of the pipeline, generated programmatically."""
    fig, ax = plt.subplots(figsize=(16, 8.5))
    ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")

    blocks = [
        (0.4, 6.6, 3.2, 1.4, "1. DATA INGESTION\nSynthetic simulator / CSV / API", "#1f77b4"),
        (0.4, 4.6, 3.2, 1.4, "2. CLEANING\nDates, duplicates, outliers,\nimputation", "#2ca02c"),
        (0.4, 2.6, 3.2, 1.4, "3. FEATURE ENGINEERING\nCalendar, rolling, anomalies,\nlags, events", "#ff7f0e"),
        (0.4, 0.6, 3.2, 1.4, "4. EDA\nStats, seasonality,\ncorrelations", "#9467bd"),
        (5.0, 6.6, 3.2, 1.4, "5. TREND ANALYSIS\nOLS + Mann-Kendall +\ndecomposition", "#d62728"),
        (5.0, 4.6, 3.2, 1.4, "6. ANOMALY DETECTION\nz-score, STL, IQR,\nIsolation Forest", "#8c564b"),
        (5.0, 2.6, 3.2, 1.4, "7. FORECASTING\nNaive / Ridge / ARIMA\nwith back-testing", "#e377c2"),
        (5.0, 0.6, 3.2, 1.4, "8. INSIGHTS ENGINE\nAuto-generated findings", "#17becf"),
        (9.6, 5.1, 3.2, 1.4, "9. VISUALISATION\n15+ publication charts", "#bcbd22"),
        (9.6, 3.1, 3.2, 1.4, "10. DASHBOARD\nStreamlit app", "#8c564b"),
        (9.6, 1.1, 3.2, 1.4, "11. REPORTING\nMarkdown + HTML + CSV", "#7f7f7f"),
        (13.4, 3.1, 2.2, 1.4, "STAKEHOLDERS\nPolicy • Energy • Agri\nInsurance • Cities", "#1f77b4"),
    ]
    for x, y, w, h, label, color in blocks:
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=color, alpha=0.18,
                                   edgecolor=color, linewidth=2, joinstyle="round"))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=9.5,
                fontweight="bold", color="#222222")

    arrows = [
        ((3.6, 7.3), (5.0, 7.3)), ((1.6, 6.6), (1.6, 6.0)),
        ((1.6, 4.6), (1.6, 4.0)), ((1.6, 2.6), (1.6, 2.0)),
        ((3.6, 5.3), (5.0, 5.3)), ((3.6, 3.3), (5.0, 3.3)),
        ((3.6, 1.3), (5.0, 1.3)), ((6.6, 6.6), (9.6, 6.6)),
        ((8.2, 4.6), (8.2, 4.4)), ((9.6, 5.8), (9.6, 4.5)),
        ((8.2, 2.6), (8.2, 2.4)), ((9.6, 2.3), (9.6, 2.5)),
        ((9.6, 4.5), (9.6, 4.5)), ((11.2, 5.1), (11.2, 4.5)),
        ((12.8, 5.8), (13.4, 5.8)), ((12.8, 3.8), (13.4, 3.8)),
        ((12.8, 1.8), (13.4, 3.0)),
    ]
    for (x1, y1), (x2, y2) in arrows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", lw=1.6, color="#444444"))

    ax.set_title("Climate Trend Analyzer - System Architecture",
                 fontsize=16, fontweight="bold", pad=18)
    ax.text(8, 0.15, "Data flows left to right; every stage is a separate, testable Python module "
                     "under  src/",
            ha="center", fontsize=10, style="italic", color="#555555")
    return _save(fig, "00_architecture_diagram.png")


# ==========================================================================
# 7. HELPER: inline images for the HTML report
# ==========================================================================
def image_to_base64(path: Path | str) -> str:
    """Return a base64 data-URI for embedding a PNG inside the HTML report."""
    data = base64.b64encode(Path(path).read_bytes()).decode("utf-8")
    return f"data:image/png;base64,{data}"

```

**What this file does:** Shared chart functions and self-contained-image helpers.


## `app/app.py`

```python
"""
app.py
======
**Streamlit dashboard** for the Climate Trend Analyzer.

Run it with:

    streamlit run app/app.py

What it does
------------
* loads the analysis-ready dataset produced by the pipeline
* lets the user filter by region, indicator and time window
* shows headline KPIs (mean level, warming rate, anomalies, forecast)
* renders interactive Plotly charts (trend, seasonality, anomalies, forecast)
* exposes the anomaly register and the trend table for download
* shows the auto-generated insights

This is the "demo" a recruiter or interviewer can click through in 60 seconds.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# make the `src` package importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import config as cfg  # noqa: E402

st.set_page_config(
    page_title="Climate Trend Analyzer",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Data loading (cached so the app stays fast)
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data():
    """Load the featured dataset, the trend table, the anomalies and forecasts."""
    data = {}
    if cfg.FEATURED_CSV.exists():
        data["featured"] = pd.read_csv(cfg.FEATURED_CSV, parse_dates=["date"])
    if cfg.TREND_CSV.exists():
        data["trends"] = pd.read_csv(cfg.TREND_CSV)
    if cfg.ANOMALY_CSV.exists():
        data["anomalies"] = pd.read_csv(cfg.ANOMALY_CSV, parse_dates=["date"])
    if cfg.FORECAST_CSV.exists():
        data["forecast"] = pd.read_csv(cfg.FORECAST_CSV, parse_dates=["date"])
    if cfg.METRICS_CSV.exists():
        data["metrics"] = pd.read_csv(cfg.METRICS_CSV)
    return data


DATA = load_data()

if "featured" not in DATA:
    st.error(
        "No processed data found. Run the pipeline first:\n\n"
        "```bash\npython main.py --step all\n```"
    )
    st.stop()

df = DATA["featured"]
trends = DATA.get("trends", pd.DataFrame())
anomalies = DATA.get("anomalies", pd.DataFrame())
forecast = DATA.get("forecast", pd.DataFrame())
metrics = DATA.get("metrics", pd.DataFrame())

# --------------------------------------------------------------------------
# Sidebar controls
# --------------------------------------------------------------------------
st.sidebar.title("🌍 Climate Trend Analyzer")
st.sidebar.caption("Long-term trends, anomalies and forecasts from monthly climate data")

regions = sorted(df["region"].unique().tolist())
selected_regions = st.sidebar.multiselect(
    "Regions", regions, default=regions,
    help="Choose one or more regions to compare.",
)

variable_map = {
    "Mean temperature (°C)": "temp_mean_c",
    "Rainfall (mm)": "rainfall_mm",
    "Humidity (%)": "humidity_pct",
    "CO₂ (ppm)": "co2_ppm",
    "Sea level (mm)": "sea_level_mm",
}
variable_label = st.sidebar.selectbox("Indicator", list(variable_map.keys()))
variable = variable_map[variable_label]

min_date, max_date = df["date"].min(), df["date"].max()
date_range = st.sidebar.slider(
    "Date range",
    min_value=min_date.to_pydatetime(),
    max_value=max_date.to_pydatetime(),
    value=(min_date.to_pydatetime(), max_date.to_pydatetime()),
    format="YYYY-MM-DD",
)

show_anomalies = st.sidebar.checkbox("Highlight anomalies", value=True)
st.sidebar.divider()
st.sidebar.markdown(
    f"""
**Dataset**  \n
`{len(df):,}` monthly records · `{df['region'].nunique()}` regions · \
`{df['date'].min():%Y-%m}` → `{df['date'].max():%Y-%m}`

**Built with**  \n
pandas · NumPy · SciPy · scikit-learn · statsmodels · Plotly · Streamlit
"""
)

# --------------------------------------------------------------------------
# Filter the data
# --------------------------------------------------------------------------
mask = (
    df["region"].isin(selected_regions)
    & (df["date"] >= pd.Timestamp(date_range[0]))
    & (df["date"] <= pd.Timestamp(date_range[1]))
)
view = df[mask].copy()
if view.empty:
    st.warning("No data in the selected range - widen the filters.")
    st.stop()

# --------------------------------------------------------------------------
# Header + KPI cards
# --------------------------------------------------------------------------
st.title("Climate Trend Analyzer")
st.info("City charts use SYNTHETIC data (1980–2024). NOAA/Scripps observations are a separate CO2 companion below. No institutional access or sensor hardware is used.")
st.markdown(
    f"**{variable_label}** · {len(selected_regions)} region(s) · "
    f"{view['date'].min():%d %b %Y} → {view['date'].max():%d %b %Y} · "
    f"{len(view):,} observations"
)

kpi = st.columns(5)

# 1. mean level
kpi[0].metric("Mean level", f"{view[variable].mean():.2f}")

# 2. warming / trend rate (only meaningful for temperature)
if variable == "temp_mean_c" and not trends.empty:
    t = trends[(trends["indicator"] == "temp_mean_c") & (trends["region"].isin(selected_regions))]
    if not t.empty:
        kpi[1].metric("Warming (°C/decade)", f"{t['slope_per_decade'].mean():+.3f}")
        kpi[2].metric("Trend significance", f"{int((t['p_value'] < 0.05).sum())}/{len(t)} regions",
                      help="p < 0.05 in the seasonal fixed-effects OLS model")
    else:
        kpi[1].metric("Warming rate", "n/a")
        kpi[2].metric("Trend significance", "n/a")
else:
    monthly = view.groupby("date")[variable].mean()
    kpi[1].metric("Endpoint city-mean change", f"{monthly.iloc[-1] - monthly.iloc[0]:+.2f}")
    kpi[2].metric("Std deviation", f"{view[variable].std():.2f}")

# 4. anomalies
if not anomalies.empty:
    a = anomalies[anomalies["region"].isin(selected_regions)]
    a = a[(a.date >= pd.Timestamp(date_range[0])) & (a.date <= pd.Timestamp(date_range[1]))]
    kpi[3].metric("Detector records", f"{len(a):,}", help="Different methods may flag the same region-month; not unique events")
else:
    kpi[3].metric("Anomalies detected", "0")

# 5. forecast quality
if not metrics.empty:
    best = metrics[metrics["region"].isin(selected_regions)]
    if not best.empty:
        kpi[4].metric("Best model", best.iloc[0]["model"].split(" (")[0], help=f"RMSE = {best.iloc[0]['RMSE']:.3f}")
    else:
        kpi[4].metric("Best model", "n/a")
else:
    kpi[4].metric("Best model", "n/a")

# --------------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["📈 Trends", "🌀 Anomalies", "🔮 Forecast", "📋 Data & Downloads"]
)

# ------------------------------- TRENDS -----------------------------------
with tab1:
    import plotly.express as px

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Observed series with 12-month rolling mean")
        long = view[["date", "region", variable]].rename(columns={variable: "value"})
        roll = (
            view.sort_values("date")
            .groupby("region")[variable]
            .rolling(12, center=True, min_periods=6)
            .mean()
            .reset_index(level=0, drop=True)
        )
        long["rolling_mean"] = roll.reindex(long.index)
        fig = px.line(
            long, x="date", y="value", color="region",
            title=f"{variable_label} over time",
            labels={"value": variable_label, "date": "Date", "region": "Region"},
        )
        for region, g in long.groupby("region"):
            g = g.sort_values("date")
            fig.add_scatter(x=g["date"], y=g["rolling_mean"], mode="lines",
                            line=dict(width=3, dash="dot"), name=f"{region} rolling mean")
        if show_anomalies and not anomalies.empty:
            a = anomalies[(anomalies.region.isin(selected_regions)) & (anomalies.variable==variable)
                          & (anomalies.date>=pd.Timestamp(date_range[0])) & (anomalies.date<=pd.Timestamp(date_range[1]))]
            a = a.drop_duplicates(["date","region"])
            fig.add_scatter(x=a.date,y=a.value,mode="markers",name="Flagged months",
                            marker=dict(color="#dd5440",size=7,symbol="diamond"))
        fig.update_layout(height=430, legend_title_text="Region")
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Annual averages")
        yearly = view.groupby(["region", "year"], as_index=False)[variable].mean()
        fig2 = px.bar(yearly, x="year", y=variable, color="region", barmode="group",
                      title=f"Yearly average {variable_label}",
                      labels={"year": "Year", variable: variable_label})
        fig2.update_layout(height=430)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Seasonal profile (average by calendar month)")
    seasonal = view.groupby(["region", "month"], as_index=False)[variable].mean()
    fig3 = px.line(seasonal, x="month", y=variable, color="region", markers=True,
                   title="Seasonal cycle", labels={"month": "Month", variable: variable_label})
    fig3.update_xaxes(tickmode="array", tickvals=list(range(1, 13)),
                      ticktext=["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    fig3.update_layout(height=380)
    st.plotly_chart(fig3, use_container_width=True)

    if not trends.empty:
        st.subheader("Full-record trend statistics (OLS + monthly fixed effects, HAC uncertainty)")
        st.caption("Trend KPIs and this table use the full 1980–2024 record, not the date slider. R² includes seasonality; MK p-values are exploratory and not serial-correlation corrected. CI bounds are per year; slope headline is per decade.")
        t = trends[trends["region"].isin(selected_regions)]
        st.dataframe(
            t[["region", "indicator", "slope_per_decade", "ci_low", "ci_high",
               "r_squared", "p_value", "mk_trend", "mk_p_value",
               "theil_sen_slope_per_year"]].round(4),
            use_container_width=True,
        )

# ------------------------------ ANOMALIES ---------------------------------
with tab2:
    if anomalies.empty:
        st.info("No anomalies in the current dataset.")
    else:
        a = anomalies[anomalies["region"].isin(selected_regions)].copy()
        a = a[(a["date"] >= pd.Timestamp(date_range[0])) & (a["date"] <= pd.Timestamp(date_range[1]))]

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Anomalies by method")
            counts = a["method"].value_counts().rename_axis("method").reset_index(name="count")
            fig4 = px.bar(counts, x="method", y="count", color="method",
                          title="Detection method", labels={"count": "Anomalies"})
            fig4.update_layout(height=340, showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)
        with c2:
            st.subheader("Anomalies by direction")
            dirs = a["direction"].value_counts().rename_axis("direction").reset_index(name="count")
            fig5 = px.pie(dirs, names="direction", values="count", hole=0.45,
                          title="Anomaly type", color_discrete_sequence=px.colors.qualitative.Set2)
            fig5.update_layout(height=340)
            st.plotly_chart(fig5, use_container_width=True)

        st.subheader("Anomaly register")
        st.dataframe(
            a[["anomaly_id", "date", "region", "variable", "method", "value",
               "expected", "deviation", "score", "severity", "direction", "description"]],
            use_container_width=True, height=380,
        )
        st.download_button(
            "⬇️ Download anomalies (CSV)",
            a.to_csv(index=False).encode("utf-8"),
            file_name="anomalies.csv",
            mime="text/csv",
        )

# ------------------------------- FORECAST ---------------------------------
with tab3:
    st.caption("Forecast horizon: January 2025–December 2027 from the record ending December 2024. This is an educational, fixed-origin demonstration, not a forecast issued today. Bands are approximate; see methodology.")
    if forecast.empty:
        st.info("No forecast available - run `python main.py --step forecast`.")
    else:
        f = forecast[forecast["region"].isin(selected_regions)]
        sel = st.selectbox("Region", sorted(f["region"].unique().tolist()))
        f = f[f["region"] == sel]

        hist = df[df["region"] == sel][["date", "temp_mean_c"]].tail(120)
        merged = pd.concat([
            hist.rename(columns={"temp_mean_c": "value"}).assign(kind="Historical"),
            f[["date", "prediction"]].rename(columns={"prediction": "value"}).assign(kind="Forecast"),
        ], ignore_index=True)

        fig6 = px.line(merged, x="date", y="value", color="kind",
                       title=f"{sel} - historical vs. {f['model'].iloc[0]} forecast",
                       labels={"value": "Mean temperature (°C)", "date": "Date"})
        if f["ci_low"].notna().any():
            fig6.add_scatter(x=f["date"], y=f["ci_low"], mode="lines",
                             line=dict(width=0, color="gray"), name="Approximate lower band")
            fig6.add_scatter(x=f["date"], y=f["ci_high"], mode="lines",
                             line=dict(width=0, color="gray"), name="Approximate upper band",
                             fill="tonexty")
        fig6.update_layout(height=430)
        st.plotly_chart(fig6, use_container_width=True)

        if not metrics.empty:
            st.subheader("Model selection (60-month chronological validation)")
            m = metrics[metrics["region"] == sel].sort_values("RMSE")
            fig7 = px.bar(m, x="model", y="RMSE", color="model",
                          title="Forecast error by model (lower is better)",
                          labels={"RMSE": "RMSE (°C)", "model": "Model"})
            fig7.update_layout(height=330, showlegend=False)
            st.plotly_chart(fig7, use_container_width=True)
            st.dataframe(m.round(3), use_container_width=True)

        st.download_button(
            "⬇️ Download forecast (CSV)",
            f.to_csv(index=False).encode("utf-8"),
            file_name=f"forecast_{sel.lower().replace(' ', '_')}.csv",
            mime="text/csv",
        )

# --------------------------- DATA & DOWNLOADS -----------------------------
with tab4:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Processed dataset preview")
        st.dataframe(view.head(200), use_container_width=True, height=380)
        st.download_button(
            "⬇️ Download filtered data (CSV)",
            view.to_csv(index=False).encode("utf-8"),
            file_name="climate_filtered.csv",
            mime="text/csv",
        )
    with c2:
        st.subheader("Data quality")
        q = pd.DataFrame({
            "column": view.columns,
            "missing": [int(view[c].isna().sum()) for c in view.columns],
            "dtype": [str(view[c].dtype) for c in view.columns],
        })
        st.dataframe(q, use_container_width=True, height=380)
        st.markdown(
            f"""
**Cleaning summary**

| Metric | Value |
| --- | --- |
| Raw rows | {cfg.RAW_CSV.name if cfg.RAW_CSV.exists() else 'n/a'} |
| Analysis rows | {len(df):,} |
| Completeness | {100 * (1 - df[cfg.CLIMATE_COLUMNS].isna().sum().sum() / (len(df) * len(cfg.CLIMATE_COLUMNS))):.2f} % |
| Regions | {df['region'].nunique()} |
| Period | {df['date'].min():%Y-%m} → {df['date'].max():%Y-%m} |
"""
        )

# --------------------------------------------------------------------------
# Footer
# --------------------------------------------------------------------------
st.divider()
public_path = cfg.PROCESSED_DIR / "noaa_co2_monthly.csv"
if public_path.exists():
    st.subheader("PUBLIC DATA — NOAA/Scripps Mauna Loa CO2")
    public = pd.read_csv(public_path, parse_dates=["date"])
    st.caption("Real public observations, independently analyzed; NOT joined to simulated cities. Concentration in ppm, not emissions. Source: gml.noaa.gov/ccgg/trends/data.html")
    st.plotly_chart(px.line(public,x="date",y="co2_ppm",labels={"co2_ppm":"CO2 concentration (ppm)"}), use_container_width=True)
    st.download_button("Download public CO2 analysis CSV", public.to_csv(index=False), file_name="noaa_co2_monthly.csv", mime="text/csv")
st.divider()
st.markdown(
    """
<div style="text-align:center; color:#888; font-size:0.85rem;">
<b>Climate Trend Analyzer</b> · a data-science portfolio project ·
built with pandas, scikit-learn, statsmodels, Plotly and Streamlit ·
data is a high-fidelity simulation produced by <code>src/data_generator.py</code>
</div>
""",
    unsafe_allow_html=True,
)

```

**What this file does:** Dashboard reads saved results and distinguishes synthetic cities from public observations.


## `tests/test_pipeline.py`

```python
"""
tests/test_pipeline.py
======================
Automated tests for the Climate Trend Analyzer.

Run them with:

    pytest -v                    # from the project root
    python -m pytest -v tests/

The tests are written so that a beginner can read them and understand what
"correct" means for each part of the pipeline.  They are fast (the forecasting
test uses a short series) and do not require any network access.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as cfg  # noqa: E402
from src import anomaly_detection, data_generator, eda, features  # noqa: E402
from src import forecasting, preprocessing, trend_analysis  # noqa: E402


# --------------------------------------------------------------------------
# Fixtures - build the data once and reuse it across the tests
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def raw_df():
    return data_generator.generate_climate_dataset(seed=cfg.RANDOM_SEED)


@pytest.fixture(scope="module")
def clean_df(raw_df):
    clean, _ = preprocessing.clean_dataset(raw_df)
    return clean


@pytest.fixture(scope="module")
def featured_df(clean_df):
    return features.build_features(clean_df)


# --------------------------------------------------------------------------
# 1. Data generation
# --------------------------------------------------------------------------
def test_generator_creates_expected_shape(raw_df):
    """5 regions x 540 months = 2700 base records (+ injected duplicates)."""
    assert len(raw_df) >= 2700
    assert set(raw_df["region"].unique()) == set(cfg.REGION_NAMES)
    assert {"temp_mean_c", "rainfall_mm", "humidity_pct", "co2_ppm"} <= set(raw_df.columns)


def test_generator_is_deterministic():
    """Same seed -> identical data (reproducibility is essential)."""
    a = data_generator.generate_climate_dataset(seed=7)
    b = data_generator.generate_climate_dataset(seed=7)
    pd.testing.assert_frame_equal(a, b)


def test_raw_data_is_intentionally_dirty(raw_df):
    """The simulator must inject the defects the cleaning module fixes."""
    assert raw_df.isna().sum().sum() > 0, "expected missing values"
    assert raw_df.duplicated().sum() > 0, "expected duplicate rows"
    assert (raw_df["temp_mean_c"] < -100).any(), "expected impossible outliers"


# --------------------------------------------------------------------------
# 2. Cleaning
# --------------------------------------------------------------------------
def test_cleaning_removes_duplicates_and_bad_dates(clean_df):
    assert clean_df.duplicated(subset=["date", "region"]).sum() == 0
    assert clean_df["date"].isna().sum() == 0
    assert pd.api.types.is_datetime64_any_dtype(clean_df["date"])


def test_cleaning_removes_impossible_values(clean_df):
    """-999 °C readings must not survive the cleaning step."""
    for col, (lo, hi) in cfg.VALID_RANGES.items():
        assert clean_df[col].between(lo, hi).all(), f"{col} still out of range"


def test_cleaning_leaves_no_missing_values(clean_df):
    for col in cfg.CLIMATE_COLUMNS:
        assert clean_df[col].isna().sum() == 0


def test_mixed_date_formats_are_parsed(raw_df):
    """Both YYYY-MM-DD and MM/DD/YYYY must become real timestamps."""
    parsed = preprocessing.parse_dates(raw_df.copy(), "date")
    assert parsed["date"].isna().sum() == 0


# --------------------------------------------------------------------------
# 3. Feature engineering
# --------------------------------------------------------------------------
def test_features_are_created(featured_df):
    for col in ("year", "month", "season", "t", "temp_anomaly",
                "temp_mean_c_roll12_mean", "rain_pct_of_normal", "heatwave_event"):
        assert col in featured_df.columns, f"missing feature: {col}"


def test_anomaly_is_centred_on_zero(featured_df):
    """The climatology baseline must give ~zero mean anomaly per region."""
    m = featured_df.groupby("region")["temp_anomaly"].mean().abs().max()
    assert m < 1e-9, f"anomalies are not centred (max |mean| = {m})"


# --------------------------------------------------------------------------
# 4. Trend analysis  (the statistical heart of the project)
# --------------------------------------------------------------------------
def test_mann_kendall_detects_an_increasing_series():
    """MK must report 'increasing' for a clearly rising series."""
    series = pd.Series(np.arange(120) * 0.1 + np.random.default_rng(0).normal(0, 0.2, 120))
    res = trend_analysis.mann_kendall(series)
    assert res["mk_trend"] == "increasing"
    assert res["mk_p_value"] < 0.05


def test_mann_kendall_detects_a_decreasing_series():
    series = pd.Series(np.arange(120) * -0.1 + np.random.default_rng(1).normal(0, 0.2, 120))
    res = trend_analysis.mann_kendall(series)
    assert res["mk_trend"] == "decreasing"


def test_mann_kendall_on_flat_series_finds_no_trend():
    series = pd.Series(np.random.default_rng(2).normal(50, 3, 240))
    res = trend_analysis.mann_kendall(series)
    assert res["mk_trend"] == "no significant trend"


def test_ols_slope_matches_a_known_trend():
    """
    A series rising 0.5 per step must be recovered with slope 0.5.

    The length is a multiple of 12 so that every calendar position carries
    the same number of observations - the seasonal adjustment then removes
    the seasonal cycle without touching the linear slope.
    """
    series = pd.Series(np.arange(120) * 0.5)
    res = trend_analysis.ols_trend(series)
    assert res["slope_per_year"] == pytest.approx(0.5 * 12, rel=1e-6)


def test_trends_agree_between_ols_and_mann_kendall(featured_df):
    """After seasonal adjustment the two methods must tell the same story."""
    t = trend_analysis.analyze_trends(featured_df, ["temp_mean_c"])
    for _, r in t.iterrows():
        assert r["slope_per_year"] > 0, f"{r['region']}: OLS slope should be positive"
        assert r["mk_trend"] == "increasing", f"{r['region']}: MK disagrees with OLS"


def test_deseasonalization_removes_the_seasonal_cycle():
    """A pure sine wave must lose its amplitude after deseasonalisation."""
    idx = pd.RangeIndex(120)
    wave = pd.Series(10 * np.sin(2 * np.pi * np.arange(120) / 12), index=idx)
    flat = trend_analysis.deseasonalize(wave, period=12)
    assert flat.abs().max() < 1e-9


# --------------------------------------------------------------------------
# 5. Anomaly detection
# --------------------------------------------------------------------------
def test_anomaly_detection_returns_expected_schema(featured_df):
    res = anomaly_detection.run_anomaly_detection(featured_df)
    assert not res["anomalies"].empty
    for col in ("anomaly_id", "date", "region", "method", "score", "severity"):
        assert col in res["anomalies"].columns


def test_injected_extreme_events_are_detected(featured_df):
    """The simulated heat-wave months must be picked up by the detectors."""
    res = anomaly_detection.run_anomaly_detection(featured_df)
    hot = res["anomalies"][res["anomalies"]["direction"] == "hot"]
    assert len(hot) > 0, "no hot anomalies detected"


# --------------------------------------------------------------------------
# 6. Forecasting
# --------------------------------------------------------------------------
def test_forecast_metrics_are_finite(featured_df):
    region = featured_df[featured_df["region"] == cfg.REGION_NAMES[0]]
    res = forecasting.forecast_region(region, h=12, test_size=36)
    assert res, "forecasting returned nothing"
    assert np.isfinite(res["metrics"]["RMSE"]).all()
    assert len(res["forecast"]) == 12


def test_seasonal_naive_beats_naive(featured_df):
    """A seasonal series must be forecast better by the seasonal baseline."""
    region = featured_df[featured_df["region"] == cfg.REGION_NAMES[1]]
    s = region.sort_values("date")["temp_mean_c"]
    train, test = s.iloc[:-36].to_numpy(), s.iloc[-36:].to_numpy()
    rmse_naive = forecasting.evaluate(test, forecasting.naive_forecast(train, 36))["RMSE"]
    rmse_seas = forecasting.evaluate(test, forecasting.seasonal_naive_forecast(train, 36))["RMSE"]
    assert rmse_seas < rmse_naive


# --------------------------------------------------------------------------
# 7. EDA
# --------------------------------------------------------------------------
def test_eda_tables_have_expected_columns(featured_df):
    bundle = eda.run_eda(featured_df)
    assert "temp_mean_c" in bundle["correlations"].columns
    assert len(bundle["yearly"]) == featured_df["region"].nunique() * featured_df["year"].nunique()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))


def test_simulator_peaks_match_hemispheres(clean_df):
    means=clean_df.groupby(['region','month']).temp_mean_c.mean()
    assert means['London'].idxmax()==7
    assert means['Sydney'].idxmax()==1
    assert means['Hyderabad'].idxmax()==4


def test_forecast_does_not_use_validation_targets(featured_df):
    d=featured_df[featured_df.region=='London'].sort_values('date').copy()
    original=forecasting.ml_forecast(d,h=6,test_size=60)
    d.loc[d.index[-60:],'observed_temp_mean_c'] += 100
    d.loc[d.index[-60:],'temp_mean_c'] += 100
    changed=forecasting.ml_forecast(d,h=6,test_size=60)
    np.testing.assert_allclose(original['validation_prediction'],changed['validation_prediction'])


def test_forecast_ignores_leaky_eda_features(featured_df):
    d=featured_df[featured_df.region=='London'].copy()
    a=forecasting.ml_forecast(d,h=6)
    for c in ['temp_mean_c_roll12_mean','enso_proxy','co2_ppm']:
        d[c]=99999
    b=forecasting.ml_forecast(d,h=6)
    np.testing.assert_allclose(a['validation_prediction'],b['validation_prediction'])
    np.testing.assert_allclose(a['forecast'].prediction,b['forecast'].prediction)


def test_original_missing_targets_preserved(clean_df):
    assert clean_df.observed_temp_mean_c.isna().sum()>0
    assert clean_df.temp_mean_c.isna().sum()==0
    assert (clean_df.loc[clean_df.observed_temp_mean_c.isna(),'data_quality_flag']=='repaired').all()


def test_public_snapshot_is_real_and_valid():
    path=cfg.PROCESSED_DIR/'noaa_co2_monthly.csv'
    if not path.exists():
        pytest.skip('Run python -m src.public_data for the public companion')
    public=pd.read_csv(path)
    assert len(public)==540
    assert public.co2_ppm.between(300,500).all()
    assert public.date.is_unique


def test_metrics_exclude_missing_truth():
    result=forecasting.evaluate([1,np.nan,3],[1,100,5])
    assert result['n_evaluated']==2
    assert result['MAE']==1

```

**What this file does:** Scientific/data/leakage regression tests; execute with python -m pytest.


## `scripts/build_handbook.py`

```python
"""Assemble current results, recruiter README and complete file-by-file handbook.
Run from project root AFTER the analytical pipeline and tests:
    python scripts/build_handbook.py
Generated documentation derives result numbers from the actual saved outputs.
"""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'


def table(df):
    d=df.copy()
    for c in d.select_dtypes('float'):
        d[c]=d[c].map(lambda x:f'{x:.3f}')
    return '| '+' | '.join(d.columns)+' |\n| '+' | '.join(['---']*len(d.columns))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in d.itertuples(index=False,name=None))


def main():
    summary=json.loads((ROOT/'outputs/run_summary.json').read_text())
    public=json.loads((ROOT/'outputs/noaa_summary.json').read_text())
    n=summary['key_numbers']
    trends=pd.read_csv(ROOT/'outputs/tables/trend_summary.csv')
    t=trends[trends.indicator=='temp_mean_c'].copy()
    t['CI low (°C/decade)']=t.ci_low*10;t['CI high (°C/decade)']=t.ci_high*10
    t=t.rename(columns={'region':'City','slope_per_decade':'Slope (°C/decade)','r_squared':'Full-model R²'})
    trend_table=table(t[['City','Slope (°C/decade)','CI low (°C/decade)','CI high (°C/decade)','Full-model R²']])
    anomalies=pd.read_csv(ROOT/'outputs/tables/anomalies.csv')
    unique=len(anomalies[['date','region']].drop_duplicates())
    metrics=pd.read_csv(ROOT/'outputs/tables/model_metrics.csv')
    best=metrics.loc[metrics.groupby('region').RMSE.idxmin(),['region','model','MAE','RMSE','R2','n_evaluated']]
    readme=f'''# 🌍 Climate Trend Analyzer

**A runnable, tested student portfolio: synthetic regional climate analysis plus a separate real public CO₂ companion.**

[Start here](START_HERE.md) · [Complete A–P guide](docs/PROJECT_GUIDE.md) · [Full code by file](docs/FULL_CODE.md) · [Methodology](docs/METHODOLOGY.md) · [Dataset card](docs/DATASET_CARD.md)

> **Source honesty:** city temperature, rainfall, humidity and sea-level demonstrations are **synthetic**. NOAA/Scripps Mauna Loa CO₂ is **real public data**, analyzed separately with attribution and provenance. This is not an institutional monitoring system, a real-world regional climate study or a physical climate projection.

## Overview and problem

Climate records combine repeating seasons, long-term changes, missing readings and genuine extremes. This project turns a reproducible monthly dataset into auditable cleaned tables, season-adjusted trend statistics, an anomaly investigation register, baseline-aware forecasts, charts, an HTML report and an interactive dashboard.

The system illustrates analytics workflows relevant to environmental research, energy-demand planning, agriculture and city adaptation. **No business savings or real-world prediction benefit is measured or claimed.**

## Quick start

Python 3.11/3.12 recommended (local verification also used 3.13). No GPU, paid API or institutional login.

```bash
python -m venv .venv
# Windows PowerShell: .\\.venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --step all
python -m pytest -q
python -m streamlit run app/app.py
```

Open `outputs/reports/climate_trend_report.html` for the standalone embedded-chart report.
Detailed Windows/CMD/macOS/Linux/Colab instructions are in [guide F](docs/PROJECT_GUIDE.md#f-installation--from-scratch).

## Implemented features

- Seeded simulation: five climates, hemisphere-aware seasons, warming, autocorrelated variability and explicit hot/dry stress episodes.
- Auditable cleaning: mixed dates, duplicate keys, invalid readings, historical gap interpolation and preserved original temperature targets.
- EDA: annual temperature means, annual rainfall totals, seasonal patterns, anomalies and correlations.
- Trends: OLS time + month fixed effects, **HAC(12)** uncertainty, exploratory deseasonalized Mann–Kendall and Theil–Sen slopes.
- Four detectors: climatology z-score, STL residual, IQR and Isolation Forest.
- Forecasting: naive, seasonal-naive, drift, calendar/trend Ridge and training-AIC-selected ARIMA; identical fixed-origin validation.
- Real public-data companion: NOAA/Scripps concentration CSV, original source comments, retrieval UTC and SHA256.
- Streamlit: filters, KPIs, four tabs, download buttons and a separate public-data section.
- Five executed notebooks, automated tests, CI definition and professional documentation.

## Results from the bundled synthetic experiment

| Item | Actual generated result |
| --- | --- |
| Raw / clean observations | {summary['rows_raw']:,} / {n['rows_analysed']:,} |
| Coverage | Five cities, January 1980–December 2024 |
| Mean estimated synthetic warming | +{n['mean_warming_c_per_decade']:.3f} °C/decade |
| Fastest simulated warming | {n['fastest_warming_region']}, +{n['fastest_warming_c_per_decade']:.3f} °C/decade |
| Detector records | {len(anomalies)} method flags across {unique} distinct city-months |
| Forecast | 36 monthly dates, January 2025–December 2027, from end-2024 origin |
| Lowest validation RMSE among candidates | {n['best_forecast_rmse']:.3f} °C (not an independent final-test score) |
| Core analysis measurement completeness | {n['data_completeness_pct']:.1f}% after historical cleaning |

### Season-adjusted temperature slopes

{trend_table}

Confidence intervals above are converted to **per decade**. The CSV stores CI bounds **per year**. Full-model R² includes **seasonality as well as trend**; it is not warming-only explanatory power. MK p-values are exploratory and uncorrected for serial dependence/multiple testing.

### Best model per city — chronological validation

{table(best)}

Models predict all 60 validation dates from the same origin. Originally missing targets are excluded from scoring (`n_evaluated`), not filled with fabricated truth. Ridge uses only future-known time/month features; it never uses centered EDA windows, observed future CO₂ or target-derived ENSO proxies. ARIMA order is chosen using training AIC. The final validation block selects the model; a separate untouched test is a future improvement.

## Real public-data result — not simulation

The analyzed NOAA/Scripps snapshot contains **{public['n_months']} months / {public['n_complete_years']} complete years** in 1980–2024. Annual concentration changes from **{public['first_complete_year_mean_ppm']:.2f} ppm** in 1980 to **{public['last_complete_year_mean_ppm']:.2f} ppm** in 2024. A descriptive linear annual slope is **{public['linear_slope_ppm_per_year']:.3f} ppm/year**; the underlying trajectory is not assumed perfectly linear.

Source: [NOAA GML CO₂ data](https://gml.noaa.gov/ccgg/trends/data.html). Attribution: **Xin Lan, NOAA/GML; Ralph Keeling, Scripps Institution of Oceanography**. Read original source comments for interpolation/measurement-interruption notes. CO₂ is **concentration in ppm, not emissions**. Source data is not relicensed by the project MIT license.

![Public CO2 observations](outputs/figures/16_public_noaa_co2.png)

## Architecture

```text
Synthetic generator -> raw CSV -> quality audit -> clean + observed target
                                  |                |
                       retrospective EDA/features  past-only forecast path
                                  |                |
                    OLS/HAC + MK + four detectors  baselines/Ridge/ARIMA
                                  \\              /
                             charts + tables + report + dashboard

NOAA public CSV -> provenance/cache -> independent concentration analysis
                                  -> public chart + table + dashboard section
```

[Detailed module contracts](docs/ARCHITECTURE.md) · [Method equations and limitations](docs/METHODOLOGY.md).

## Technology choices

| Layer | Stack |
| --- | --- |
| Language/data | Python, pandas, NumPy |
| Statistics/ML | SciPy, statsmodels, scikit-learn |
| Plots | Matplotlib, Seaborn, Plotly |
| UI | Streamlit |
| Learning/testing | Jupyter, nbconvert, pytest, GitHub Actions |
| Persistence | CSV, JSON, PNG, Markdown, self-contained HTML |

[Guide B–C](docs/PROJECT_GUIDE.md#b-tech-stack-options) compares easiest/intermediate/advanced options and explains why this CPU-only intermediate approach was selected.

## Folder structure

```text
Climate-Trend-Analyzer/
  main.py, README.md, START_HERE.md, requirements*.txt, LICENSE
  src/             generator, loader, cleaning, features, EDA, trends,
                   anomalies, forecasting, public_data, plots, insights, reports
  app/app.py       Streamlit dashboard
  tests/           data/statistical/leakage tests
  notebooks/       five executed tutorials
  scripts/         portable notebook and handbook builders
  data/raw/        synthetic feed + original NOAA snapshot/provenance
  data/processed/  clean/featured synthetic tables + separate public CO2
  outputs/figures/ generated charts
  outputs/tables/  trend, anomaly, annual, forecast and model-selection tables
  outputs/reports/ Markdown + HTML analytical report
  images/          actual dashboard captures and curated proof charts
  docs/            complete A–P guide, full source, science/data/career/GitHub docs
  .github/         CI definition
```

## Run stages individually

```bash
python main.py --step simulate --regenerate
python main.py --step clean
python main.py --step features
python main.py --step eda
python main.py --step trends
python main.py --step anomalies
python main.py --step forecast
python main.py --step report
python main.py --summary
# Public track, offline cached snapshot:
python -m src.public_data
# Explicit network refresh:
python -m src.public_data --refresh
# Rebuild and execute the tutorial notebooks:
python scripts/build_notebooks.py --execute
```

`python main.py --no-forecast` runs the historical analysis faster. Existing forecast files may remain from a previous full run; use the full run for a coherent demo and check file timestamps. Refresh Streamlit's cache after regenerating inputs. For actual delivered logs see `outputs/latest_run.log`, `outputs/test_results.txt` and `outputs/notebook_execution.log`.

## Virtual simulation workflow

1. Define city baselines, warm peak months and illustrative slopes.
2. Generate the monthly calendar, cosine seasonality, multi-year oscillations and AR(1) noise.
3. Inject labeled three-month hot/dry experiments.
4. Add missing values, duplicates, impossible readings and mixed date strings.
5. Clean and audit; preserve original targets.
6. Explore seasonality, estimate slopes, inspect detector flags and measure planted-event recall.
7. Validate forecasts at a fixed origin, export charts/tables/report and inspect the dashboard.

These monthly persistence proxies are not daily WMO heatwave or validated drought-index declarations. The synthetic global-like sea-level field is not local sea-level monitoring at an inland city.

## Screenshots and charts

### Actual browser dashboard

![Actual dashboard capture](images/09_dashboard.png)

### Seasonal trend and detector examples

![Synthetic temperature record](outputs/figures/02_temperature_trend.png)
![HAC uncertainty on simulated slopes](outputs/figures/07_warming_rate_by_region.png)
![Flagged simulated months](outputs/figures/09_anomaly_detection.png)
![Forecast validation](outputs/figures/15_model_comparison.png)
![Fixed-origin projection](outputs/figures/14_forecast.png)

Non-ARIMA bands use ±1.96×validation RMSE: **approximate and uncalibrated**, not guaranteed 95% coverage or physical climate-model ranges. Trend/forecast origin and source type must remain visible in presentations.

[All proof/capture instructions](docs/SCREENSHOTS.md) · [Actual dashboard GIF](images/dashboard_demo.gif).

## Tests and CI

```bash
python -m pytest -v
```

**26 tests passed locally** in the delivered run. Tests cover seeded generation, mixed-date parsing, range repairs, feature behavior, known trend recovery, MK sign/direction, hemisphere peaks, original missing targets, baseline comparisons, public schema and forecast leakage.

The CI workflow is defined for Python 3.10/3.11/3.12 with unique artifact names. **Remote CI has not been claimed to pass before you publish and run it.** Set an actual CI badge only after creating your repository. Exact locally tested package versions are in `requirements-tested.txt`; portable ranges are in `requirements.txt`.

## Limitations and future improvements

- Regional measurements are synthetic. Public source adapters must preserve true scope/units and cannot fabricate missing variables.
- Full-record climatologies are retrospective; prospective anomaly detection needs a fixed past reference period.
- Full-model R² includes seasons; exploratory MK is not serial-correlation/multiple-testing corrected.
- Detector outputs overlap; cross-method scores are not calibrated risk scores.
- Forecast selection uses validation, not a final independent test; bands are approximate.
- No climate attribution, area-weighted global index, measured savings or official warning is produced.

Next: real station/reanalysis adapters, coverage-aware annual aggregation, fixed 30-year normals, rolling-origin + independent final testing, interval calibration, daily extremes, geospatial exposure and CMIP6 scenarios. [Ordered upgrade plan](docs/PROJECT_GUIDE.md#o-future-improvements--ordered-by-value).

## Learning outcomes and portfolio publishing

You can demonstrate auditable data cleaning, time-series reasoning, honest prediction protocols, complementary anomaly methods, reproducible software design and stakeholder communication. Learn the code and limitations before using the résumé bullets.

- [Full GitHub upload commands and topics](docs/GITHUB_PLAYBOOK.md)
- [Eight-day genuine learning/commit plan](docs/PROJECT_GUIDE.md#l-commit-strategy--eight-day-genuine-proof-plan)
- [Résumé, three LinkedIn posts, ten interview answers](docs/PROJECT_GUIDE.md#n-résumé-linkedin-and-interview-presentation)
- [Beginner troubleshooting](docs/PROJECT_GUIDE.md#p-troubleshooting--reason-solution-prevention)

## Author and attribution

**Student author: add your own name, profile links and contribution details before publishing.** Do not claim sole authorship of AI-assisted code or a fabricated development timeline. Local commits are genuine same-session build checkpoints, not an eight-day history. A GitHub push, your own narrated recording and permanent deployment require your own account/actions.

Code and project-generated simulation: [MIT](LICENSE). External NOAA/Scripps data: retain source attribution and usage notes. The source is publicly accessible; institutional endorsement is not implied.
'''
    (ROOT/'README.md').write_text(readme)
    explanations={
        'main.py':'Command-line runner: full workflow or an individual named stage.',
        'app/app.py':'Dashboard reads saved results and distinguishes synthetic cities from public observations.',
        'src/config.py':'Centralized filesystem paths, thresholds and simulation parameters.',
        'src/data_generator.py':'Reproducible synthetic measurement system, explicit injected episodes and dirty data.',
        'src/data_loader.py':'CSV/JSON access layer and dataset-profile helper.',
        'src/preprocessing.py':'Auditable historical cleaning with preserved original targets for temporal evaluation.',
        'src/features.py':'Retrospective exploratory features; these are not automatically safe prediction inputs.',
        'src/eda.py':'Descriptive statistics, correlations, seasonal and annual aggregations.',
        'src/trend_analysis.py':'Season-controlled OLS with HAC uncertainty and exploratory MK/Theil–Sen cross-checks.',
        'src/anomaly_detection.py':'Four complementary detectors; register rows are method flags, not unique events.',
        'src/forecasting.py':'Common fixed-origin validation with future-known predictors and train-only filling.',
        'src/public_data.py':'Separate public NOAA CO2 ingestion, attribution, checksum and concentration analysis.',
        'src/visualizations.py':'Shared chart functions and self-contained-image helpers.',
        'src/insights.py':'Natural-language findings computed from saved statistical results.',
        'src/report_generator.py':'Markdown and embedded-image HTML report assembly.',
        'src/pipeline.py':'Orchestration of the analysis stages and saved run metadata.',
        'tests/test_pipeline.py':'Scientific/data/leakage regression tests; execute with python -m pytest.',
        'scripts/build_notebooks.py':'Portable notebook construction and execution, failing on execution errors.',
        'scripts/build_handbook.py':'Builds this source listing and current-results README from actual saved outputs.',
    }
    files=[ROOT/'main.py',*sorted((ROOT/'src').glob('*.py')),ROOT/'app/app.py',ROOT/'tests/test_pipeline.py',*sorted((ROOT/'scripts').glob('*.py')),ROOT/'requirements.txt',ROOT/'requirements-tested.txt',ROOT/'.gitignore',ROOT/'.github/workflows/ci.yml',ROOT/'README.md']
    chunks=['# Full implementation — Climate Trend Analyzer\n\nEvery file below also exists as a runnable file in the repository. No placeholders replace analytical code. Filenames are relative to the project root. Notebook JSON is not pasted here: all five executed .ipynb files are included, and the complete builder below reproduces them.\n']
    for f in files:
        rel=f.relative_to(ROOT).as_posix()
        lang='python' if f.suffix=='.py' else ('yaml' if f.suffix=='.yml' else 'text')
        fence='````' if f.name=='README.md' else '```'
        chunks.append(f'\n## `{rel}`\n\n{fence}{lang}\n{f.read_text()}\n{fence}\n\n**What this file does:** {explanations.get(rel,"Project configuration, installation or recruiter-facing documentation. See the corresponding section in PROJECT_GUIDE.md.")}\n')
    code='\n'.join(chunks)
    (DOCS/'FULL_CODE.md').write_text(code)
    (DOCS/'COMPLETE_HANDBOOK.md').write_text((DOCS/'PROJECT_GUIDE.md').read_text()+'\n\n---\n\n# Appendix — complete executable source, file by file\n\n'+code)
    print('Built README.md, docs/FULL_CODE.md and docs/COMPLETE_HANDBOOK.md')


if __name__=='__main__':
    main()

```

**What this file does:** Builds this source listing and current-results README from actual saved outputs.


## `scripts/build_notebooks.py`

```python
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

```

**What this file does:** Portable notebook construction and execution, failing on execution errors.


## `requirements.txt`

```text
# Python 3.10-3.13. Conservative ranges; tested environment in requirements-tested.txt.
pandas>=2.2.3,<3
numpy>=1.26.4,<3
scipy>=1.13,<2
matplotlib>=3.9,<4
seaborn>=0.13.2,<0.14
plotly>=5.24,<7
scikit-learn>=1.5,<2
statsmodels>=0.14.4,<0.16
streamlit>=1.40,<2
pytest>=8,<10
nbformat>=5.10,<6
nbconvert>=7.16,<8
ipykernel>=6,<8
jupyterlab>=4,<5

```

**What this file does:** Project configuration, installation or recruiter-facing documentation. See the corresponding section in PROJECT_GUIDE.md.


## `requirements-tested.txt`

```text
# Exact installed packages used for Python 3.13 verification
pandas==2.2.3
numpy==2.3.5
scipy==1.17.1
matplotlib==3.10.9
seaborn==0.13.2
plotly==6.0.1
scikit-learn==1.6.1
statsmodels==0.15.0
streamlit==1.66.0
pytest==9.0.3
nbformat==5.11.1
nbconvert==7.17.1
ipykernel==6.31.0

```

**What this file does:** Project configuration, installation or recruiter-facing documentation. See the corresponding section in PROJECT_GUIDE.md.


## `.gitignore`

```text
# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.eggs/

# Virtual environments
.venv/
venv/
env/
ENV/

# ---------------------------------------------------------------------------
# Jupyter
# ---------------------------------------------------------------------------
.ipynb_checkpoints/
*.ipynb_checkpoints
profile_default/
ipython_config.py

# ---------------------------------------------------------------------------
# Testing / coverage
# ---------------------------------------------------------------------------
.pytest_cache/
.coverage
.coverage.*
htmlcov/
coverage.xml
.tox/

# ---------------------------------------------------------------------------
# OS / editor noise
# ---------------------------------------------------------------------------
.DS_Store
Thumbs.db
.idea/
.vscode/
*.swp

# ---------------------------------------------------------------------------
# Streamlit
# ---------------------------------------------------------------------------
.streamlit/secrets.toml

# ---------------------------------------------------------------------------
# Large model artefacts (the pipeline stores fitted models here)
# ---------------------------------------------------------------------------
models/*.joblib
models/*.pkl
!models/.gitkeep

# ---------------------------------------------------------------------------
# NOTE: data/processed/, outputs/figures/, outputs/tables/ and outputs/reports/
# are intentionally COMMITTED - they are the proof of work for this project.
# Only the very large binary artefacts are excluded.
# ---------------------------------------------------------------------------
*.parquet
*.h5
*.hdf5
*.nc

```

**What this file does:** Project configuration, installation or recruiter-facing documentation. See the corresponding section in PROJECT_GUIDE.md.


## `.github/workflows/ci.yml`

```yaml
name: CI

# ---------------------------------------------------------------------------
# Continuous Integration for the Climate Trend Analyzer
#
# Every push and pull request runs:
#   1. a lint / import check
#   2. the unit-test suite
#   3. a short end-to-end pipeline run (no forecasting, it is slow)
#
# The green badge at the top of the README is a visible, verifiable signal
# that the project actually works.
# ---------------------------------------------------------------------------
on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    name: Test on Python ${{ matrix.python-version }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - name: Check out the repository
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest

      - name: Verify every module imports cleanly
        run: |
          python -c "import src.config, src.data_generator, src.data_loader, \
          src.preprocessing, src.features, src.eda, src.trend_analysis, \
          src.anomaly_detection, src.forecasting, src.visualizations, \
          src.insights, src.report_generator, src.pipeline; print('imports OK')"

      - name: Run the test suite
        run: pytest -v --tb=short

      - name: Run the pipeline (fast mode)
        run: python main.py --step all --no-forecast

      - name: Upload the analytical outputs as an artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: climate-trend-analyzer-outputs-${{ matrix.python-version }}
          path: |
            outputs/figures/
            outputs/tables/
            outputs/reports/
          retention-days: 7

```

**What this file does:** Project configuration, installation or recruiter-facing documentation. See the corresponding section in PROJECT_GUIDE.md.


## `README.md`

````text
# 🌍 Climate Trend Analyzer

**A runnable, tested student portfolio: synthetic regional climate analysis plus a separate real public CO₂ companion.**

[Start here](START_HERE.md) · [Complete A–P guide](docs/PROJECT_GUIDE.md) · [Full code by file](docs/FULL_CODE.md) · [Methodology](docs/METHODOLOGY.md) · [Dataset card](docs/DATASET_CARD.md)

> **Source honesty:** city temperature, rainfall, humidity and sea-level demonstrations are **synthetic**. NOAA/Scripps Mauna Loa CO₂ is **real public data**, analyzed separately with attribution and provenance. This is not an institutional monitoring system, a real-world regional climate study or a physical climate projection.

## Overview and problem

Climate records combine repeating seasons, long-term changes, missing readings and genuine extremes. This project turns a reproducible monthly dataset into auditable cleaned tables, season-adjusted trend statistics, an anomaly investigation register, baseline-aware forecasts, charts, an HTML report and an interactive dashboard.

The system illustrates analytics workflows relevant to environmental research, energy-demand planning, agriculture and city adaptation. **No business savings or real-world prediction benefit is measured or claimed.**

## Quick start

Python 3.11/3.12 recommended (local verification also used 3.13). No GPU, paid API or institutional login.

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --step all
python -m pytest -q
python -m streamlit run app/app.py
```

Open `outputs/reports/climate_trend_report.html` for the standalone embedded-chart report.
Detailed Windows/CMD/macOS/Linux/Colab instructions are in [guide F](docs/PROJECT_GUIDE.md#f-installation--from-scratch).

## Implemented features

- Seeded simulation: five climates, hemisphere-aware seasons, warming, autocorrelated variability and explicit hot/dry stress episodes.
- Auditable cleaning: mixed dates, duplicate keys, invalid readings, historical gap interpolation and preserved original temperature targets.
- EDA: annual temperature means, annual rainfall totals, seasonal patterns, anomalies and correlations.
- Trends: OLS time + month fixed effects, **HAC(12)** uncertainty, exploratory deseasonalized Mann–Kendall and Theil–Sen slopes.
- Four detectors: climatology z-score, STL residual, IQR and Isolation Forest.
- Forecasting: naive, seasonal-naive, drift, calendar/trend Ridge and training-AIC-selected ARIMA; identical fixed-origin validation.
- Real public-data companion: NOAA/Scripps concentration CSV, original source comments, retrieval UTC and SHA256.
- Streamlit: filters, KPIs, four tabs, download buttons and a separate public-data section.
- Five executed notebooks, automated tests, CI definition and professional documentation.

## Results from the bundled synthetic experiment

| Item | Actual generated result |
| --- | --- |
| Raw / clean observations | 2,715 / 2,700 |
| Coverage | Five cities, January 1980–December 2024 |
| Mean estimated synthetic warming | +0.298 °C/decade |
| Fastest simulated warming | London, +0.398 °C/decade |
| Detector records | 362 method flags across 259 distinct city-months |
| Forecast | 36 monthly dates, January 2025–December 2027, from end-2024 origin |
| Lowest validation RMSE among candidates | 1.315 °C (not an independent final-test score) |
| Core analysis measurement completeness | 100.0% after historical cleaning |

### Season-adjusted temperature slopes

| City | Slope (°C/decade) | CI low (°C/decade) | CI high (°C/decade) | Full-model R² |
| --- | --- | --- | --- | --- |
| Hyderabad | 0.269 | 0.097 | 0.441 | 0.883 |
| London | 0.398 | 0.231 | 0.564 | 0.932 |
| New York | 0.318 | 0.153 | 0.483 | 0.974 |
| Singapore | 0.228 | 0.049 | 0.408 | 0.428 |
| Sydney | 0.279 | 0.119 | 0.439 | 0.899 |

Confidence intervals above are converted to **per decade**. The CSV stores CI bounds **per year**. Full-model R² includes **seasonality as well as trend**; it is not warming-only explanatory power. MK p-values are exploratory and uncorrected for serial dependence/multiple testing.

### Best model per city — chronological validation

| region | model | MAE | RMSE | R2 | n_evaluated |
| --- | --- | --- | --- | --- | --- |
| Hyderabad | Ridge (calendar + trend) | 1.153 | 1.637 | 0.845 | 59 |
| London | Ridge (calendar + trend) | 1.335 | 1.689 | 0.893 | 58 |
| New York | Ridge (calendar + trend) | 0.919 | 1.315 | 0.974 | 60 |
| Singapore | Ridge (calendar + trend) | 1.141 | 1.821 | 0.390 | 55 |
| Sydney | Ridge (calendar + trend) | 1.207 | 1.597 | 0.889 | 58 |

Models predict all 60 validation dates from the same origin. Originally missing targets are excluded from scoring (`n_evaluated`), not filled with fabricated truth. Ridge uses only future-known time/month features; it never uses centered EDA windows, observed future CO₂ or target-derived ENSO proxies. ARIMA order is chosen using training AIC. The final validation block selects the model; a separate untouched test is a future improvement.

## Real public-data result — not simulation

The analyzed NOAA/Scripps snapshot contains **540 months / 45 complete years** in 1980–2024. Annual concentration changes from **338.76 ppm** in 1980 to **424.60 ppm** in 2024. A descriptive linear annual slope is **1.916 ppm/year**; the underlying trajectory is not assumed perfectly linear.

Source: [NOAA GML CO₂ data](https://gml.noaa.gov/ccgg/trends/data.html). Attribution: **Xin Lan, NOAA/GML; Ralph Keeling, Scripps Institution of Oceanography**. Read original source comments for interpolation/measurement-interruption notes. CO₂ is **concentration in ppm, not emissions**. Source data is not relicensed by the project MIT license.

![Public CO2 observations](outputs/figures/16_public_noaa_co2.png)

## Architecture

```text
Synthetic generator -> raw CSV -> quality audit -> clean + observed target
                                  |                |
                       retrospective EDA/features  past-only forecast path
                                  |                |
                    OLS/HAC + MK + four detectors  baselines/Ridge/ARIMA
                                  \              /
                             charts + tables + report + dashboard

NOAA public CSV -> provenance/cache -> independent concentration analysis
                                  -> public chart + table + dashboard section
```

[Detailed module contracts](docs/ARCHITECTURE.md) · [Method equations and limitations](docs/METHODOLOGY.md).

## Technology choices

| Layer | Stack |
| --- | --- |
| Language/data | Python, pandas, NumPy |
| Statistics/ML | SciPy, statsmodels, scikit-learn |
| Plots | Matplotlib, Seaborn, Plotly |
| UI | Streamlit |
| Learning/testing | Jupyter, nbconvert, pytest, GitHub Actions |
| Persistence | CSV, JSON, PNG, Markdown, self-contained HTML |

[Guide B–C](docs/PROJECT_GUIDE.md#b-tech-stack-options) compares easiest/intermediate/advanced options and explains why this CPU-only intermediate approach was selected.

## Folder structure

```text
Climate-Trend-Analyzer/
  main.py, README.md, START_HERE.md, requirements*.txt, LICENSE
  src/             generator, loader, cleaning, features, EDA, trends,
                   anomalies, forecasting, public_data, plots, insights, reports
  app/app.py       Streamlit dashboard
  tests/           data/statistical/leakage tests
  notebooks/       five executed tutorials
  scripts/         portable notebook and handbook builders
  data/raw/        synthetic feed + original NOAA snapshot/provenance
  data/processed/  clean/featured synthetic tables + separate public CO2
  outputs/figures/ generated charts
  outputs/tables/  trend, anomaly, annual, forecast and model-selection tables
  outputs/reports/ Markdown + HTML analytical report
  images/          actual dashboard captures and curated proof charts
  docs/            complete A–P guide, full source, science/data/career/GitHub docs
  .github/         CI definition
```

## Run stages individually

```bash
python main.py --step simulate --regenerate
python main.py --step clean
python main.py --step features
python main.py --step eda
python main.py --step trends
python main.py --step anomalies
python main.py --step forecast
python main.py --step report
python main.py --summary
# Public track, offline cached snapshot:
python -m src.public_data
# Explicit network refresh:
python -m src.public_data --refresh
# Rebuild and execute the tutorial notebooks:
python scripts/build_notebooks.py --execute
```

`python main.py --no-forecast` runs the historical analysis faster. Existing forecast files may remain from a previous full run; use the full run for a coherent demo and check file timestamps. Refresh Streamlit's cache after regenerating inputs. For actual delivered logs see `outputs/latest_run.log`, `outputs/test_results.txt` and `outputs/notebook_execution.log`.

## Virtual simulation workflow

1. Define city baselines, warm peak months and illustrative slopes.
2. Generate the monthly calendar, cosine seasonality, multi-year oscillations and AR(1) noise.
3. Inject labeled three-month hot/dry experiments.
4. Add missing values, duplicates, impossible readings and mixed date strings.
5. Clean and audit; preserve original targets.
6. Explore seasonality, estimate slopes, inspect detector flags and measure planted-event recall.
7. Validate forecasts at a fixed origin, export charts/tables/report and inspect the dashboard.

These monthly persistence proxies are not daily WMO heatwave or validated drought-index declarations. The synthetic global-like sea-level field is not local sea-level monitoring at an inland city.

## Screenshots and charts

### Actual browser dashboard

![Actual dashboard capture](images/09_dashboard.png)

### Seasonal trend and detector examples

![Synthetic temperature record](outputs/figures/02_temperature_trend.png)
![HAC uncertainty on simulated slopes](outputs/figures/07_warming_rate_by_region.png)
![Flagged simulated months](outputs/figures/09_anomaly_detection.png)
![Forecast validation](outputs/figures/15_model_comparison.png)
![Fixed-origin projection](outputs/figures/14_forecast.png)

Non-ARIMA bands use ±1.96×validation RMSE: **approximate and uncalibrated**, not guaranteed 95% coverage or physical climate-model ranges. Trend/forecast origin and source type must remain visible in presentations.

[All proof/capture instructions](docs/SCREENSHOTS.md) · [Actual dashboard GIF](images/dashboard_demo.gif).

## Tests and CI

```bash
python -m pytest -v
```

**26 tests passed locally** in the delivered run. Tests cover seeded generation, mixed-date parsing, range repairs, feature behavior, known trend recovery, MK sign/direction, hemisphere peaks, original missing targets, baseline comparisons, public schema and forecast leakage.

The CI workflow is defined for Python 3.10/3.11/3.12 with unique artifact names. **Remote CI has not been claimed to pass before you publish and run it.** Set an actual CI badge only after creating your repository. Exact locally tested package versions are in `requirements-tested.txt`; portable ranges are in `requirements.txt`.

## Limitations and future improvements

- Regional measurements are synthetic. Public source adapters must preserve true scope/units and cannot fabricate missing variables.
- Full-record climatologies are retrospective; prospective anomaly detection needs a fixed past reference period.
- Full-model R² includes seasons; exploratory MK is not serial-correlation/multiple-testing corrected.
- Detector outputs overlap; cross-method scores are not calibrated risk scores.
- Forecast selection uses validation, not a final independent test; bands are approximate.
- No climate attribution, area-weighted global index, measured savings or official warning is produced.

Next: real station/reanalysis adapters, coverage-aware annual aggregation, fixed 30-year normals, rolling-origin + independent final testing, interval calibration, daily extremes, geospatial exposure and CMIP6 scenarios. [Ordered upgrade plan](docs/PROJECT_GUIDE.md#o-future-improvements--ordered-by-value).

## Learning outcomes and portfolio publishing

You can demonstrate auditable data cleaning, time-series reasoning, honest prediction protocols, complementary anomaly methods, reproducible software design and stakeholder communication. Learn the code and limitations before using the résumé bullets.

- [Full GitHub upload commands and topics](docs/GITHUB_PLAYBOOK.md)
- [Eight-day genuine learning/commit plan](docs/PROJECT_GUIDE.md#l-commit-strategy--eight-day-genuine-proof-plan)
- [Résumé, three LinkedIn posts, ten interview answers](docs/PROJECT_GUIDE.md#n-résumé-linkedin-and-interview-presentation)
- [Beginner troubleshooting](docs/PROJECT_GUIDE.md#p-troubleshooting--reason-solution-prevention)

## Author and attribution

**Student author: add your own name, profile links and contribution details before publishing.** Do not claim sole authorship of AI-assisted code or a fabricated development timeline. Local commits are genuine same-session build checkpoints, not an eight-day history. A GitHub push, your own narrated recording and permanent deployment require your own account/actions.

Code and project-generated simulation: [MIT](LICENSE). External NOAA/Scripps data: retain source attribution and usage notes. The source is publicly accessible; institutional endorsement is not implied.

````

**What this file does:** Project configuration, installation or recruiter-facing documentation. See the corresponding section in PROJECT_GUIDE.md.
