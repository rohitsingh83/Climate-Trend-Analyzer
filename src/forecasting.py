"""
forecasting.py
==============
**Future climate projection (forecasting).**

The module deliberately compares a *hierarchy* of models so the choice is
evidence-based rather than opinion-based:

1. **Naive**                 - "next month = this month" (the benchmark)
2. **Seasonal naive**        - "next month = same month last year" (captures seasonality)
3. **Drift / linear trend**  - "the historical slope continues"
4. **Ridge regression on engineered features** (sklearn) - the ML approach
5. **ARIMA** (statsmodels)   - the classic statistical time-series model

All models are evaluated on the **same hold-out window** (last 60 months)
with MAE / RMSE / MAPE / R^2, and the winner is refit on the full series to
project the next 36 months with a 95 % prediction interval.

Leakage control
---------------
Features used for prediction are built with `.shift()` / rolling windows that
only look *backwards*, and the scaler is fitted on training data only.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from . import config as cfg

warnings.filterwarnings("ignore")


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------
def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Standard regression metrics for a forecast."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_true - y_pred
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mape = float(np.mean(np.abs(err) / np.abs(y_true)) * 100)
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    r2 = float(1 - ss_res / ss_tot) if ss_tot else np.nan
    return {"MAE": mae, "RMSE": rmse, "MAPE": mape, "R2": r2}


# --------------------------------------------------------------------------
# Baselines
# --------------------------------------------------------------------------
def naive_forecast(train: np.ndarray, h: int) -> np.ndarray:
    return np.repeat(train[-1], h)


def seasonal_naive_forecast(train: np.ndarray, h: int, period: int = 12) -> np.ndarray:
    """Forecast = value of the same month one year earlier."""
    out = []
    for i in range(h):
        idx = len(train) - period + (i % period)
        out.append(train[max(idx, 0)])
    return np.array(out)


def drift_forecast(train: np.ndarray, h: int) -> np.ndarray:
    """Naive + the average historical drift (per step)."""
    if len(train) < 2:
        return np.repeat(train[-1], h)
    slope = (train[-1] - train[0]) / (len(train) - 1)
    return train[-1] + slope * np.arange(1, h + 1)


# --------------------------------------------------------------------------
# Feature-based ML model
# --------------------------------------------------------------------------
def build_ml_dataset(df: pd.DataFrame, target: str = "temp_mean_c") -> pd.DataFrame:
    """
    Build a supervised table per region with strictly backward-looking features.
    """
    from .features import add_cyclical_month

    d = add_cyclical_month(df)
    feats = [
        "t", "month_sin", "month_cos",
        f"{target}_lag1", f"{target}_lag2", f"{target}_lag3", f"{target}_lag12",
        f"{target}_roll12_mean", "co2_ppm", "enso_proxy",
    ]
    feats = [f for f in feats if f in d.columns]
    d = d.dropna(subset=[target] + [f for f in feats if f in d.columns])
    return d, feats


def ml_forecast(
    df: pd.DataFrame,
    target: str = "temp_mean_c",
    h: int = cfg.FORECAST_HORIZON,
    test_size: int = cfg.TEST_SIZE,
) -> dict:
    """
    Ridge regression on engineered features.

    The model is trained on the first (n - test_size) rows and scored on the
    held-out tail; afterwards it is refit on everything for the final horizon.
    """
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    d, feats = build_ml_dataset(df, target)
    if len(d) < test_size + 24:
        return {}

    train = d.iloc[:-test_size]
    test = d.iloc[-test_size:]

    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=1.0)),
        ]
    )
    pipe.fit(train[feats], train[target])
    pred = pipe.predict(test[feats])

    metrics = evaluate(test[target].to_numpy(), pred)

    # ---- refit on everything, then project the future --------------------
    pipe.fit(d[feats], d[target])

    # ---- refit on everything, then project the future recursively --------
    pipe.fit(d[feats], d[target])

    future_rows = []
    hist = d.copy()
    for step in range(1, h + 1):
        last = hist.iloc[-1]                       # last KNOWN observation
        last_date = pd.Timestamp(last["date"]) + pd.offsets.MonthBegin(1)
        m = last_date.month
        ang = 2 * np.pi * m / 12.0
        row = {
            "t": float(last["t"]) + step,
            "month_sin": float(np.sin(ang)),
            "month_cos": float(np.cos(ang)),
            f"{target}_lag1": float(last[target]),
            f"{target}_lag2": float(hist.iloc[-2][target]),
            f"{target}_lag3": float(hist.iloc[-3][target]),
            f"{target}_lag12": float(hist.iloc[-12][target]),
            f"{target}_roll12_mean": float(hist.iloc[-12:][target].mean()),
            "co2_ppm": float(last["co2_ppm"] + 2.1 / 12.0),
            "enso_proxy": float(last["enso_proxy"]),
        }
        pred = float(pipe.predict(pd.DataFrame([row])[feats])[0])
        row["date"] = last_date
        row[target] = pred                         # feed the prediction back in
        future_rows.append({"date": last_date, "prediction": pred, **{
            k: v for k, v in row.items() if k not in ("date", target)}})
        hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)

    future = pd.DataFrame(future_rows)
    return {"model": "Ridge (engineered features)", "metrics": metrics,
            "forecast": future, "features": feats, "fitted": pipe}


# --------------------------------------------------------------------------
# ARIMA
# --------------------------------------------------------------------------
def arima_forecast(
    series: pd.Series,
    h: int = cfg.FORECAST_HORIZON,
    order: tuple = (1, 1, 1),
    test_size: int = cfg.TEST_SIZE,
) -> dict:
    """Fit an ARIMA model, evaluate on the hold-out, then forecast."""
    from statsmodels.tsa.arima.model import ARIMA

    s = series.dropna().astype(float)
    if len(s) < 36:
        return {}
    train, test = s.iloc[:-test_size], s.iloc[-test_size:]

    try:
        model = ARIMA(train.to_numpy(), order=order)
        fit = model.fit()
        pred = np.asarray(fit.forecast(steps=test_size), dtype=float)
        metrics = evaluate(test.to_numpy(), pred)

        full = ARIMA(s.to_numpy(), order=order).fit()
        fc = full.get_forecast(steps=h)
        ci = fc.conf_int(alpha=0.05)
        return {
            "model": f"ARIMA{order}",
            "metrics": metrics,
            "forecast_mean": np.asarray(fc.predicted_mean, dtype=float),
            "forecast_ci_low": np.asarray(ci[:, 0], dtype=float),
            "forecast_ci_high": np.asarray(ci[:, 1], dtype=float),
            "order": order,
        }
    except Exception as exc:  # pragma: no cover
        print(f"[forecasting] ARIMA{order} failed: {exc}")
        return {}


def arima_grid_search(
    series: pd.Series,
    h: int = cfg.FORECAST_HORIZON,
    test_size: int = cfg.TEST_SIZE,
) -> dict:
    """Small, fast grid search over (p,d,q) picked by hold-out RMSE."""
    best, best_rmse = None, np.inf
    for p in range(cfg.ARIMA_MAX_P + 1):
        for d in (0, 1):
            for q in range(cfg.ARIMA_MAX_Q + 1):
                if p == 0 and q == 0 and d == 0:
                    continue
                res = arima_forecast(series, h=h, order=(p, d, q), test_size=test_size)
                if not res:
                    continue
                rmse = res["metrics"]["RMSE"]
                if rmse < best_rmse:
                    best, best_rmse = res, rmse
    return best or {}


# --------------------------------------------------------------------------
# Orchestration for one region
# --------------------------------------------------------------------------
def forecast_region(
    df_region: pd.DataFrame,
    target: str = "temp_mean_c",
    h: int = cfg.FORECAST_HORIZON,
    test_size: int = cfg.TEST_SIZE,
) -> dict:
    """Compare every model for a single region and return the best one."""
    d = df_region.sort_values("date").copy()
    s = d[target].astype(float)
    if len(s) < test_size + 36:
        return {}

    train = s.iloc[:-test_size].to_numpy()
    test = s.iloc[-test_size:].to_numpy()

    results = []

    for name, preds in [
        ("Naive", naive_forecast(train, len(test))),
        ("Seasonal naive", seasonal_naive_forecast(train, len(test))),
        ("Drift (linear)", drift_forecast(train, len(test))),
    ]:
        results.append({"model": name, "metrics": evaluate(test, preds), "forecast": None})

    ml = ml_forecast(d, target=target, h=h, test_size=test_size)
    if ml:
        results.append({"model": ml["model"], "metrics": ml["metrics"], "forecast": ml["forecast"]})

    arima = arima_grid_search(s, h=h, test_size=test_size)
    if arima:
        results.append({"model": arima["model"], "metrics": arima["metrics"], "forecast": "arima"})

    metrics_df = pd.DataFrame(
        [{"model": r["model"], **r["metrics"]} for r in results]
    ).sort_values("RMSE").reset_index(drop=True)

    best_name = metrics_df.iloc[0]["model"]
    best = next(r for r in results if r["model"] == best_name)

    # ---- assemble the final forecast table for the winner ----------------
    future_dates = pd.date_range(
        start=d["date"].max() + pd.offsets.MonthBegin(1), periods=h, freq="MS"
    )
    if best["forecast"] is not None and not isinstance(best["forecast"], str):
        fc_df = best["forecast"][["date", "prediction"]].copy()
        fc_df["ci_low"] = np.nan
        fc_df["ci_high"] = np.nan
    elif isinstance(best["forecast"], dict) or best["forecast"] == "arima":
        if best["model"].startswith("ARIMA"):
            fc_df = pd.DataFrame(
                {
                    "date": future_dates,
                    "prediction": arima["forecast_mean"],
                    "ci_low": arima["forecast_ci_low"],
                    "ci_high": arima["forecast_ci_high"],
                }
            )
        else:
            fc_df = pd.DataFrame({"date": future_dates, "prediction": np.nan,
                                  "ci_low": np.nan, "ci_high": np.nan})
    else:
        # a baseline won: recompute it for the full horizon
        full_train = s.to_numpy()
        if best["model"] == "Naive":
            vals = naive_forecast(full_train, h)
        elif best["model"] == "Seasonal naive":
            vals = seasonal_naive_forecast(full_train, h)
        else:
            vals = drift_forecast(full_train, h)
        fc_df = pd.DataFrame({"date": future_dates, "prediction": vals,
                              "ci_low": np.nan, "ci_high": np.nan})

    fc_df.insert(0, "region", d["region"].iloc[0])
    fc_df["model"] = best["model"]
    fc_df["target"] = target

    return {
        "region": d["region"].iloc[0],
        "best_model": best_name,
        "metrics": metrics_df,
        "forecast": fc_df,
        "arima": arima,
        "ml": ml,
        "history": d[["date", target]].copy(),
    }


def run_forecasting(
    df: pd.DataFrame,
    target: str = "temp_mean_c",
    h: int = cfg.FORECAST_HORIZON,
    test_size: int = cfg.TEST_SIZE,
) -> dict:
    """Forecast every region; returns metrics, forecast table and history."""
    results, metrics_all, forecasts = [], [], []
    for region, grp in df.groupby("region"):
        res = forecast_region(grp, target=target, h=h, test_size=test_size)
        if not res:
            continue
        results.append(res)
        m = res["metrics"].copy()
        m["region"] = region
        metrics_all.append(m)
        forecasts.append(res["forecast"])

    metrics_df = (
        pd.concat(metrics_all, ignore_index=True)
        .sort_values(["region", "RMSE"])
        .reset_index(drop=True)
        if metrics_all
        else pd.DataFrame()
    )
    fc_df = (
        pd.concat(forecasts, ignore_index=True).sort_values(["region", "date"])
        if forecasts
        else pd.DataFrame()
    )
    return {
        "metrics": metrics_df,
        "forecast": fc_df,
        "results": results,
        "target": target,
    }


if __name__ == "__main__":
    from .data_loader import load_featured

    res = run_forecasting(load_featured())
    print(res["metrics"].to_string(index=False))
