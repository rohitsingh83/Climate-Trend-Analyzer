#!/usr/bin/env python3
"""
main.py
=======
**Command-line entry point** for the Climate Trend Analyzer.

Examples
--------
    python main.py                      # run the complete pipeline
    python main.py --step all           # same, explicitly
    python main.py --step clean         # only clean the data
    python main.py --no-forecast        # skip the (slow) forecasting stage
    python main.py --regenerate         # rebuild the simulated raw dataset
    python main.py --summary            # print the headline numbers only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# make `src` importable when the script is run from any directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import config as cfg  # noqa: E402
from src import pipeline  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="Climate Trend Analyzer",
        description="Analyse climate time series: trends, anomalies and forecasts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--step",
        default="all",
        choices=["all", "simulate", "clean", "features", "eda", "trends",
                 "anomalies", "forecast", "visualize", "report", "summary"],
        help="Run a single stage instead of the whole pipeline (default: all).",
    )
    p.add_argument(
        "--regenerate",
        action="store_true",
        help="Force regeneration of the simulated raw dataset.",
    )
    p.add_argument(
        "--no-forecast",
        action="store_true",
        help="Skip the forecasting stage (faster, useful for a quick demo).",
    )
    p.add_argument(
        "--summary",
        action="store_true",
        help="Print the headline numbers from the last run and exit.",
    )
    return p


def print_summary() -> None:
    import json

    if cfg.RUN_SUMMARY_JSON.exists():
        data = json.loads(cfg.RUN_SUMMARY_JSON.read_text())
        print("=" * 62)
        print("CLIMATE TREND ANALYZER - LAST RUN SUMMARY")
        print("=" * 62)
        for k, v in data.items():
            if k in ("figures", "key_numbers"):
                continue
            print(f"{k:22s}: {v}")
        print("-" * 62)
        for k, v in data.get("key_numbers", {}).items():
            print(f"{k:22s}: {v}")
    else:
        print("No run summary found - execute `python main.py` first.")


def main() -> int:
    args = build_parser().parse_args()

    if args.summary or args.step == "summary":
        print_summary()
        return 0

    # ------------------------------------------------------------------
    # FULL PIPELINE (the default and the recommended way to run it)
    # ------------------------------------------------------------------
    if args.step == "all":
        bundle = pipeline.run_pipeline(
            do_forecast=not args.no_forecast,
            force_simulate=args.regenerate,
        )
        numbers = bundle["key_numbers"]
        print("\nHEADLINE NUMBERS")
        for k, v in numbers.items():
            print(f"  {k:32s}: {v}")
        return 0

    # ------------------------------------------------------------------
    # SINGLE STAGES (useful while learning / debugging)
    # ------------------------------------------------------------------
    if args.step == "simulate":
        pipeline.stage_simulate(force=args.regenerate)
        return 0

    if args.step == "clean":
        pipeline.stage_clean()
        return 0

    if args.step == "features":
        pipeline.stage_features()
        return 0

    # from here on we need the featured dataset
    from src import data_loader

    featured = data_loader.load_featured(cfg.FEATURED_CSV)

    if args.step == "eda":
        pipeline.stage_eda(featured)
        return 0

    if args.step == "trends":
        pipeline.stage_trends(featured)
        return 0

    if args.step == "anomalies":
        pipeline.stage_anomalies(featured)
        return 0

    if args.step == "forecast":
        pipeline.stage_forecast(featured, do_forecast=not args.no_forecast)
        return 0

    if args.step in ("visualize", "report"):
        raw = data_loader.load_raw(cfg.RAW_CSV)
        bundle = {
            "raw": raw,
            "clean": data_loader.load_clean(cfg.CLEAN_CSV),
            "featured": featured,
            "clean_report": pipeline.preprocessing.clean_dataset(raw)[1],
            "eda": pipeline.eda_mod.run_eda(featured),
            "trend_results": pipeline.trend_analysis.run_trend_analysis(featured),
            "anomaly_results": pipeline.anomaly_detection.run_anomaly_detection(featured),
            "forecast_results": (
                pipeline.fc_mod.run_forecasting(featured)
                if not args.no_forecast
                else {"metrics": pd.DataFrame(), "forecast": pd.DataFrame(), "results": []}
            ),
        }
        bundle["figures"] = pipeline.stage_visualize(bundle)
        pipeline.stage_insights(bundle)
        pipeline.stage_report(bundle)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
