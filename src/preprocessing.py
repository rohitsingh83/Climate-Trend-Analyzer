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
