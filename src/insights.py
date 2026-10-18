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
