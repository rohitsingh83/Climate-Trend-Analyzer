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
    try:
        from statsmodels.regression.linear_model import OLS
        robust = OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags":12}, use_t=True)
        se = float(robust.bse[1])
        slope_per_year = float(beta[1] * 12.0)
        p_value = float(robust.pvalues[1])
        bounds = np.asarray(robust.conf_int())[1] * 12
        ci = float((bounds[1]-bounds[0])/2)
    except Exception:
        slope_per_year = float(beta[1] * 12.0)
        p_value = float(raw_res.pvalue) if not np.isnan(raw_res.pvalue) else 0.0
        ci = float(raw_res.stderr * 12.0 * 1.96) if raw_res.stderr else 0.0

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
