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
