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
