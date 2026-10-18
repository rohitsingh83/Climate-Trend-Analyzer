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
