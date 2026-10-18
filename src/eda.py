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
