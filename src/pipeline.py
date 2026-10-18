"""
pipeline.py
===========
**End-to-end orchestration.**

`run_pipeline()` executes the full workflow in the correct order and returns a
single *bundle* (a dict of DataFrames) that every downstream consumer
(report, dashboard, tests) uses.

Stages
------
    simulate -> clean -> features -> eda -> trends -> anomalies -> forecast
             -> visualise -> insights -> report

Each stage is a separate function so it can also be run on its own from
`main.py` (e.g. `python main.py --step trends`).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from . import config as cfg
from . import (
    anomaly_detection,
    data_generator,
    data_loader,
    eda as eda_mod,
    features as feat_mod,
    forecasting as fc_mod,
    insights as ins_mod,
    preprocessing,
    report_generator,
    trend_analysis,
    visualizations as viz,
)


def _log(msg: str, start: float) -> None:
    print(f"[pipeline] {msg}  (+{time.time() - start:.1f}s)")


# --------------------------------------------------------------------------
# Individual stages
# --------------------------------------------------------------------------
def stage_simulate(force: bool = False) -> pd.DataFrame:
    """Create the raw (imperfect) dataset if it does not exist yet."""
    if cfg.RAW_CSV.exists() and not force:
        print(f"[pipeline] Raw dataset already present: {cfg.RAW_CSV}")
        return data_loader.load_raw(cfg.RAW_CSV)
    raw = data_generator.write_raw_dataset(cfg.RAW_CSV, seed=cfg.RANDOM_SEED)
    print(f"[pipeline] Simulated raw dataset written: {cfg.RAW_CSV} {raw.shape}")
    return raw


def stage_clean(raw: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """Clean the raw dataset and store the clean master table."""
    raw = raw if raw is not None else data_loader.load_raw(cfg.RAW_CSV)
    clean, report = preprocessing.clean_dataset(raw)
    clean.to_csv(cfg.CLEAN_CSV, index=False)
    preprocessing.quality_report_table(report).to_csv(cfg.TABLES_DIR / "cleaning_audit.csv", index=False)
    data_loader.save_json(report, cfg.OUTPUTS_DIR / "cleaning_audit.json")
    print(f"[pipeline] Clean dataset -> {cfg.CLEAN_CSV} {clean.shape}")
    return clean, report


def stage_features(clean: pd.DataFrame | None = None) -> pd.DataFrame:
    """Engineer the model-ready features."""
    clean = clean if clean is not None else data_loader.load_clean(cfg.CLEAN_CSV)
    feat = feat_mod.build_features(clean)
    feat = feat_mod.add_cyclical_month(feat)
    feat.to_csv(cfg.FEATURED_CSV, index=False)
    print(f"[pipeline] Featured dataset -> {cfg.FEATURED_CSV} {feat.shape}")
    return feat


def stage_eda(featured: pd.DataFrame) -> dict:
    """Exploratory data analysis."""
    bundle = eda_mod.run_eda(featured)
    data_loader.save_table(bundle["yearly"], cfg.YEARLY_CSV)
    data_loader.save_table(bundle["correlations"].reset_index(names="indicator"), cfg.CORR_CSV)
    print(f"[pipeline] EDA complete ({len(bundle['yearly'])} yearly rows)")
    return bundle


def stage_trends(featured: pd.DataFrame) -> dict:
    """Trend analysis (OLS + Mann-Kendall + decomposition)."""
    res = trend_analysis.run_trend_analysis(featured)
    data_loader.save_table(res["trends"], cfg.TREND_CSV)
    print(f"[pipeline] Trend analysis complete ({len(res['trends'])} region x indicator rows)")
    return res


def stage_anomalies(featured: pd.DataFrame) -> dict:
    """Anomaly detection ensemble."""
    res = anomaly_detection.run_anomaly_detection(featured)
    data_loader.save_table(res["anomalies"], cfg.ANOMALY_CSV)
    print(f"[pipeline] Anomaly detection complete ({len(res['anomalies'])} anomalies)")
    return res


def stage_forecast(featured: pd.DataFrame, do_forecast: bool = True) -> dict:
    """Model comparison + 36-month projection."""
    if not do_forecast:
        print("[pipeline] Forecasting skipped (--no-forecast)")
        return {"metrics": pd.DataFrame(), "forecast": pd.DataFrame(), "results": []}
    res = fc_mod.run_forecasting(featured)
    if not res["metrics"].empty:
        data_loader.save_table(res["metrics"], cfg.METRICS_CSV)
    if not res["forecast"].empty:
        data_loader.save_table(res["forecast"], cfg.FORECAST_CSV)
    print(f"[pipeline] Forecasting complete ({len(res['forecast'])} projected rows)")
    return res


def stage_visualize(bundle: dict) -> dict:
    """Create every figure used in the report and the README."""
    raw = bundle.get("raw")
    clean = bundle["clean"]
    featured = bundle["featured"]
    anomalies = bundle["anomaly_results"]["anomalies"]

    figs: dict = {}
    figs["architecture"] = viz.plot_architecture_diagram()
    if raw is not None:
        figs["raw"] = viz.plot_raw_preview(raw)
        figs["quality"] = viz.plot_data_quality(raw, clean)
    figs["temperature"] = viz.plot_temperature_trend(featured)
    figs["rainfall"] = viz.plot_rainfall_trend(featured)
    figs["heatmap"] = viz.plot_seasonal_heatmap(featured)
    figs["seasonal_profile"] = viz.plot_seasonal_profile(featured)
    figs["yearly"] = viz.plot_yearly_comparison(featured)
    figs["warming_bar"] = viz.plot_regional_warming_bar(
        bundle["trend_results"]["trends"]
    )
    figs["decomposition"] = viz.plot_decomposition(
        bundle["trend_results"]["decomposition"]
    )
    figs["anomaly"] = viz.plot_anomaly_detection(featured, anomalies)
    figs["anomaly_timeline"] = viz.plot_anomaly_timeline(anomalies)
    figs["extreme_events"] = viz.plot_extreme_events(featured)
    figs["co2"] = viz.plot_co2_vs_temperature(featured)
    figs["sea_level"] = viz.plot_sea_level_rise(featured)
    if bundle["forecast_results"].get("results"):
        figs["forecast"] = viz.plot_forecast(bundle["forecast_results"])
        figs["model_comparison"] = viz.plot_model_comparison(
            bundle["forecast_results"]["metrics"]
        )
    return figs


def stage_insights(bundle: dict) -> str:
    """Generate the natural-language insights and the key-numbers dict."""
    text = ins_mod.generate_insights(bundle)
    numbers = ins_mod.key_numbers(bundle)
    bundle["insights_text"] = text
    bundle["key_numbers"] = numbers
    return text


def stage_report(bundle: dict) -> None:
    """Write the Markdown + HTML reports and the insights document."""
    report_generator.build_markdown_report(bundle)
    report_generator.build_html_report(bundle)
    report_generator.write_insights_doc(bundle)


# --------------------------------------------------------------------------
# Full pipeline
# --------------------------------------------------------------------------
def run_pipeline(
    do_forecast: bool = True,
    force_simulate: bool = False,
    verbose: bool = True,
) -> dict:
    """
    Run the complete analytical workflow.

    Returns the analysis bundle (all DataFrames + results).
    """
    t0 = time.time()
    if verbose:
        print("=" * 70)
        print("CLIMATE TREND ANALYZER - END-TO-END PIPELINE")
        print("=" * 70)

    raw = stage_simulate(force=force_simulate)
    _log("stage 1/9  ingestion done", t0)

    clean, clean_report = stage_clean(raw)
    _log("stage 2/9  cleaning done", t0)

    featured = stage_features(clean)
    _log("stage 3/9  feature engineering done", t0)

    eda_bundle = stage_eda(featured)
    _log("stage 4/9  EDA done", t0)

    trend_results = stage_trends(featured)
    _log("stage 5/9  trend analysis done", t0)

    anomaly_results = stage_anomalies(featured)
    _log("stage 6/9  anomaly detection done", t0)

    forecast_results = stage_forecast(featured, do_forecast=do_forecast)
    _log("stage 7/9  forecasting done", t0)

    bundle = {
        "raw": raw,
        "clean": clean,
        "featured": featured,
        "clean_report": clean_report,
        "eda": eda_bundle,
        "trend_results": trend_results,
        "anomaly_results": anomaly_results,
        "forecast_results": forecast_results,
    }

    bundle["figures"] = stage_visualize(bundle)
    _log("stage 8/9  visualisations done", t0)

    # Real observations are a separate companion track, never synthetic joins.
    from .public_data import analyze as analyze_public, PATH as public_path
    if public_path.exists():
        bundle["public_data"] = analyze_public()
        bundle["figures"]["public_noaa"] = cfg.FIGURES_DIR / "16_public_noaa_co2.png"
    stage_insights(bundle)
    stage_report(bundle)
    _log("stage 9/9  insights + report done", t0)

    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "runtime_seconds": round(time.time() - t0, 1),
        "seed": cfg.RANDOM_SEED,
        "rows_raw": int(len(raw)),
        "rows_clean": int(len(clean)),
        "rows_featured": int(len(featured)),
        "regions": sorted(featured["region"].unique().tolist()),
        "date_min": str(featured["date"].min().date()),
        "date_max": str(featured["date"].max().date()),
        "anomalies": int(len(bundle["anomaly_results"]["anomalies"])),
        "figures": [str(p) for p in bundle["figures"].values()],
        "key_numbers": bundle["key_numbers"],
    }
    data_loader.save_json(summary, cfg.RUN_SUMMARY_JSON)

    if verbose:
        print("=" * 70)
        print(f"PIPELINE COMPLETE in {summary['runtime_seconds']}s")
        print(f"  figures   : {len(bundle['figures'])}  -> {cfg.FIGURES_DIR}")
        print(f"  tables    : {len(list(cfg.TABLES_DIR.glob('*.csv')))} -> {cfg.TABLES_DIR}")
        print(f"  report    : {cfg.REPORTS_DIR / 'climate_trend_report.html'}")
        print("=" * 70)
    return bundle


if __name__ == "__main__":
    run_pipeline()
