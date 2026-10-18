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
    ax.set_title("Global Temperature Trend by Region (1980-2024)")
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
    axes[0].plot(gy.index, gy.values, lw=3, color="black", label="All regions")
    axes[0].set_title("Yearly Mean Temperature by Region (1980-2024)")
    axes[0].set_xlabel("Year"); axes[0].set_ylabel("Mean temperature (°C)")
    axes[0].legend(fontsize=8, ncol=2)

    axes[1].bar(gy.index, gy.values, color="#ff7f0e", alpha=0.75)
    axes[1].axhline(gy.mean(), color="black", ls="--", lw=1.5,
                    label=f"Mean {gy.mean():.2f}°C")
    axes[1].set_title("Global Mean Temperature per Year")
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
    ax.set_title("Warming Rate by Region (OLS trend, 95% CI, °C per decade)")
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
                 label=f"Global fit: R²={r**2:.3f}, p={p:.2e}")
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
                        color="#d62728", alpha=0.15, label="95% prediction interval")
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
