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
                            f"{r['rain_normal']:.0f} mm ({r['rain_anomaly_pct']:.0f}% of normal, {z:+.1f}σ)"
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
