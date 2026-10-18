"""
app.py
======
**Streamlit dashboard** for the Climate Trend Analyzer.

Run it with:

    streamlit run app/app.py

What it does
------------
* loads the analysis-ready dataset produced by the pipeline
* lets the user filter by region, indicator and time window
* shows headline KPIs (mean level, warming rate, anomalies, forecast)
* renders interactive Plotly charts (trend, seasonality, anomalies, forecast)
* exposes the anomaly register and the trend table for download
* shows the auto-generated insights

This is the "demo" a recruiter or interviewer can click through in 60 seconds.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# make the `src` package importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import config as cfg  # noqa: E402

st.set_page_config(
    page_title="Climate Trend Analyzer",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Data loading (cached so the app stays fast)
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data():
    """Load the featured dataset, the trend table, the anomalies and forecasts."""
    data = {}
    if cfg.FEATURED_CSV.exists():
        data["featured"] = pd.read_csv(cfg.FEATURED_CSV, parse_dates=["date"])
    if cfg.TREND_CSV.exists():
        data["trends"] = pd.read_csv(cfg.TREND_CSV)
    if cfg.ANOMALY_CSV.exists():
        data["anomalies"] = pd.read_csv(cfg.ANOMALY_CSV, parse_dates=["date"])
    if cfg.FORECAST_CSV.exists():
        data["forecast"] = pd.read_csv(cfg.FORECAST_CSV, parse_dates=["date"])
    if cfg.METRICS_CSV.exists():
        data["metrics"] = pd.read_csv(cfg.METRICS_CSV)
    return data


DATA = load_data()

if "featured" not in DATA:
    st.error(
        "No processed data found. Run the pipeline first:\n\n"
        "```bash\npython main.py --step all\n```"
    )
    st.stop()

df = DATA["featured"]
trends = DATA.get("trends", pd.DataFrame())
anomalies = DATA.get("anomalies", pd.DataFrame())
forecast = DATA.get("forecast", pd.DataFrame())
metrics = DATA.get("metrics", pd.DataFrame())

# --------------------------------------------------------------------------
# Sidebar controls
# --------------------------------------------------------------------------
st.sidebar.title("🌍 Climate Trend Analyzer")
st.sidebar.caption("Long-term trends, anomalies and forecasts from monthly climate data")

regions = sorted(df["region"].unique().tolist())
selected_regions = st.sidebar.multiselect(
    "Regions", regions, default=regions,
    help="Choose one or more regions to compare.",
)

variable_map = {
    "Mean temperature (°C)": "temp_mean_c",
    "Rainfall (mm)": "rainfall_mm",
    "Humidity (%)": "humidity_pct",
    "CO₂ (ppm)": "co2_ppm",
    "Sea level (mm)": "sea_level_mm",
}
variable_label = st.sidebar.selectbox("Indicator", list(variable_map.keys()))
variable = variable_map[variable_label]

min_date, max_date = df["date"].min(), df["date"].max()
date_range = st.sidebar.slider(
    "Date range",
    min_value=min_date.to_pydatetime(),
    max_value=max_date.to_pydatetime(),
    value=(min_date.to_pydatetime(), max_date.to_pydatetime()),
    format="YYYY-MM-DD",
)

show_anomalies = st.sidebar.checkbox("Highlight anomalies", value=True)
st.sidebar.divider()
st.sidebar.markdown(
    f"""
**Dataset**  \n
`{len(df):,}` monthly records · `{df['region'].nunique()}` regions · \
`{df['date'].min():%Y-%m}` → `{df['date'].max():%Y-%m}`

**Built with**  \n
pandas · NumPy · SciPy · scikit-learn · statsmodels · Plotly · Streamlit
"""
)

# --------------------------------------------------------------------------
# Filter the data
# --------------------------------------------------------------------------
mask = (
    df["region"].isin(selected_regions)
    & (df["date"] >= pd.Timestamp(date_range[0]))
    & (df["date"] <= pd.Timestamp(date_range[1]))
)
view = df[mask].copy()
if view.empty:
    st.warning("No data in the selected range - widen the filters.")
    st.stop()

# --------------------------------------------------------------------------
# Header + KPI cards
# --------------------------------------------------------------------------
st.title("Climate Trend Analyzer")
st.markdown(
    f"**{variable_label}** · {len(selected_regions)} region(s) · "
    f"{view['date'].min():%d %b %Y} → {view['date'].max():%d %b %Y} · "
    f"{len(view):,} observations"
)

kpi = st.columns(5)

# 1. mean level
kpi[0].metric("Mean level", f"{view[variable].mean():.2f}")

# 2. warming / trend rate (only meaningful for temperature)
if variable == "temp_mean_c" and not trends.empty:
    t = trends[(trends["indicator"] == "temp_mean_c") & (trends["region"].isin(selected_regions))]
    if not t.empty:
        kpi[1].metric("Warming rate", f"{t['slope_per_decade'].mean():+.3f} °C/decade")
        kpi[2].metric("Trend significance", f"{int((t['p_value'] < 0.05).sum())}/{len(t)} regions",
                      help="p < 0.05 in the seasonal fixed-effects OLS model")
    else:
        kpi[1].metric("Warming rate", "n/a")
        kpi[2].metric("Trend significance", "n/a")
else:
    kpi[1].metric("Change over window", f"{view[variable].iloc[-1] - view[variable].iloc[0]:+.2f}")
    kpi[2].metric("Std deviation", f"{view[variable].std():.2f}")

# 4. anomalies
if not anomalies.empty:
    a = anomalies[anomalies["region"].isin(selected_regions)]
    kpi[3].metric("Anomalies detected", f"{len(a):,}")
else:
    kpi[3].metric("Anomalies detected", "0")

# 5. forecast quality
if not metrics.empty:
    best = metrics[metrics["region"].isin(selected_regions)]
    if not best.empty:
        kpi[4].metric("Best model", best.iloc[0]["model"], help=f"RMSE = {best.iloc[0]['RMSE']:.3f}")
    else:
        kpi[4].metric("Best model", "n/a")
else:
    kpi[4].metric("Best model", "n/a")

# --------------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["📈 Trends", "🌀 Anomalies", "🔮 Forecast", "📋 Data & Downloads"]
)

# ------------------------------- TRENDS -----------------------------------
with tab1:
    import plotly.express as px

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Observed series with 12-month rolling mean")
        long = view[["date", "region", variable]].rename(columns={variable: "value"})
        roll = (
            view.sort_values("date")
            .groupby("region")[variable]
            .rolling(12, center=True, min_periods=6)
            .mean()
            .reset_index(level=0, drop=True)
        )
        long["rolling_mean"] = roll.reindex(long.index)
        fig = px.line(
            long, x="date", y="value", color="region",
            title=f"{variable_label} over time",
            labels={"value": variable_label, "date": "Date", "region": "Region"},
        )
        fig.add_scatter(x=long["date"], y=long["rolling_mean"], mode="lines",
                        line=dict(width=3, dash="dot"), name="12-month rolling mean")
        fig.update_layout(height=430, legend_title_text="Region")
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Annual averages")
        yearly = view.groupby(["region", "year"], as_index=False)[variable].mean()
        fig2 = px.bar(yearly, x="year", y=variable, color="region", barmode="group",
                      title=f"Yearly average {variable_label}",
                      labels={"year": "Year", variable: variable_label})
        fig2.update_layout(height=430)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Seasonal profile (average by calendar month)")
    seasonal = view.groupby(["region", "month"], as_index=False)[variable].mean()
    fig3 = px.line(seasonal, x="month", y=variable, color="region", markers=True,
                   title="Seasonal cycle", labels={"month": "Month", variable: variable_label})
    fig3.update_xaxes(tickmode="array", tickvals=list(range(1, 13)),
                      ticktext=["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    fig3.update_layout(height=380)
    st.plotly_chart(fig3, use_container_width=True)

    if not trends.empty:
        st.subheader("Trend statistics (seasonal fixed-effects OLS + Mann-Kendall)")
        t = trends[trends["region"].isin(selected_regions)]
        st.dataframe(
            t[["region", "indicator", "slope_per_decade", "ci_low", "ci_high",
               "r_squared", "p_value", "mk_trend", "mk_p_value",
               "theil_sen_slope_per_year"]].round(4),
            use_container_width=True,
        )

# ------------------------------ ANOMALIES ---------------------------------
with tab2:
    if anomalies.empty:
        st.info("No anomalies in the current dataset.")
    else:
        a = anomalies[anomalies["region"].isin(selected_regions)].copy()
        a = a[(a["date"] >= pd.Timestamp(date_range[0])) & (a["date"] <= pd.Timestamp(date_range[1]))]

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Anomalies by method")
            counts = a["method"].value_counts().rename_axis("method").reset_index(name="count")
            fig4 = px.bar(counts, x="method", y="count", color="method",
                          title="Detection method", labels={"count": "Anomalies"})
            fig4.update_layout(height=340, showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)
        with c2:
            st.subheader("Anomalies by direction")
            dirs = a["direction"].value_counts().rename_axis("direction").reset_index(name="count")
            fig5 = px.pie(dirs, names="direction", values="count", hole=0.45,
                          title="Anomaly type", color_discrete_sequence=px.colors.qualitative.Set2)
            fig5.update_layout(height=340)
            st.plotly_chart(fig5, use_container_width=True)

        st.subheader("Anomaly register")
        st.dataframe(
            a[["anomaly_id", "date", "region", "variable", "method", "value",
               "expected", "deviation", "score", "severity", "direction", "description"]],
            use_container_width=True, height=380,
        )
        st.download_button(
            "⬇️ Download anomalies (CSV)",
            a.to_csv(index=False).encode("utf-8"),
            file_name="anomalies.csv",
            mime="text/csv",
        )

# ------------------------------- FORECAST ---------------------------------
with tab3:
    if forecast.empty:
        st.info("No forecast available - run `python main.py --step forecast`.")
    else:
        f = forecast[forecast["region"].isin(selected_regions)]
        sel = st.selectbox("Region", sorted(f["region"].unique().tolist()))
        f = f[f["region"] == sel]

        hist = df[df["region"] == sel][["date", "temp_mean_c"]].tail(120)
        merged = pd.concat([
            hist.rename(columns={"temp_mean_c": "value"}).assign(kind="Historical"),
            f[["date", "prediction"]].rename(columns={"prediction": "value"}).assign(kind="Forecast"),
        ], ignore_index=True)

        fig6 = px.line(merged, x="date", y="value", color="kind",
                       title=f"{sel} - historical vs. {f['model'].iloc[0]} forecast",
                       labels={"value": "Mean temperature (°C)", "date": "Date"})
        if f["ci_low"].notna().any():
            fig6.add_scatter(x=f["date"], y=f["ci_low"], mode="lines",
                             line=dict(width=0, color="gray"), name="95% lower")
            fig6.add_scatter(x=f["date"], y=f["ci_high"], mode="lines",
                             line=dict(width=0, color="gray"), name="95% upper",
                             fill="tonexty")
        fig6.update_layout(height=430)
        st.plotly_chart(fig6, use_container_width=True)

        if not metrics.empty:
            st.subheader("Model back-testing (60-month hold-out)")
            m = metrics[metrics["region"] == sel].sort_values("RMSE")
            fig7 = px.bar(m, x="model", y="RMSE", color="model",
                          title="Forecast error by model (lower is better)",
                          labels={"RMSE": "RMSE (°C)", "model": "Model"})
            fig7.update_layout(height=330, showlegend=False)
            st.plotly_chart(fig7, use_container_width=True)
            st.dataframe(m.round(3), use_container_width=True)

        st.download_button(
            "⬇️ Download forecast (CSV)",
            f.to_csv(index=False).encode("utf-8"),
            file_name=f"forecast_{sel.lower().replace(' ', '_')}.csv",
            mime="text/csv",
        )

# --------------------------- DATA & DOWNLOADS -----------------------------
with tab4:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Processed dataset preview")
        st.dataframe(view.head(200), use_container_width=True, height=380)
        st.download_button(
            "⬇️ Download filtered data (CSV)",
            view.to_csv(index=False).encode("utf-8"),
            file_name="climate_filtered.csv",
            mime="text/csv",
        )
    with c2:
        st.subheader("Data quality")
        q = pd.DataFrame({
            "column": view.columns,
            "missing": [int(view[c].isna().sum()) for c in view.columns],
            "dtype": [str(view[c].dtype) for c in view.columns],
        })
        st.dataframe(q, use_container_width=True, height=380)
        st.markdown(
            f"""
**Cleaning summary**

| Metric | Value |
| --- | --- |
| Raw rows | {cfg.RAW_CSV.name if cfg.RAW_CSV.exists() else 'n/a'} |
| Analysis rows | {len(df):,} |
| Completeness | {100 * (1 - df[cfg.CLIMATE_COLUMNS].isna().sum().sum() / (len(df) * len(cfg.CLIMATE_COLUMNS))):.2f} % |
| Regions | {df['region'].nunique()} |
| Period | {df['date'].min():%Y-%m} → {df['date'].max():%Y-%m} |
"""
        )

# --------------------------------------------------------------------------
# Footer
# --------------------------------------------------------------------------
st.divider()
st.markdown(
    """
<div style="text-align:center; color:#888; font-size:0.85rem;">
<b>Climate Trend Analyzer</b> · a data-science portfolio project ·
built with pandas, scikit-learn, statsmodels, Plotly and Streamlit ·
data is a high-fidelity simulation produced by <code>src/data_generator.py</code>
</div>
""",
    unsafe_allow_html=True,
)
