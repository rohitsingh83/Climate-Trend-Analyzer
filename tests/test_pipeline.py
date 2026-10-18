"""
tests/test_pipeline.py
======================
Automated tests for the Climate Trend Analyzer.

Run them with:

    pytest -v                    # from the project root
    python -m pytest -v tests/

The tests are written so that a beginner can read them and understand what
"correct" means for each part of the pipeline.  They are fast (the forecasting
test uses a short series) and do not require any network access.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as cfg  # noqa: E402
from src import anomaly_detection, data_generator, eda, features  # noqa: E402
from src import forecasting, preprocessing, trend_analysis  # noqa: E402


# --------------------------------------------------------------------------
# Fixtures - build the data once and reuse it across the tests
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def raw_df():
    return data_generator.generate_climate_dataset(seed=cfg.RANDOM_SEED)


@pytest.fixture(scope="module")
def clean_df(raw_df):
    clean, _ = preprocessing.clean_dataset(raw_df)
    return clean


@pytest.fixture(scope="module")
def featured_df(clean_df):
    return features.build_features(clean_df)


# --------------------------------------------------------------------------
# 1. Data generation
# --------------------------------------------------------------------------
def test_generator_creates_expected_shape(raw_df):
    """5 regions x 540 months = 2700 base records (+ injected duplicates)."""
    assert len(raw_df) >= 2700
    assert set(raw_df["region"].unique()) == set(cfg.REGION_NAMES)
    assert {"temp_mean_c", "rainfall_mm", "humidity_pct", "co2_ppm"} <= set(raw_df.columns)


def test_generator_is_deterministic():
    """Same seed -> identical data (reproducibility is essential)."""
    a = data_generator.generate_climate_dataset(seed=7)
    b = data_generator.generate_climate_dataset(seed=7)
    pd.testing.assert_frame_equal(a, b)


def test_raw_data_is_intentionally_dirty(raw_df):
    """The simulator must inject the defects the cleaning module fixes."""
    assert raw_df.isna().sum().sum() > 0, "expected missing values"
    assert raw_df.duplicated().sum() > 0, "expected duplicate rows"
    assert (raw_df["temp_mean_c"] < -100).any(), "expected impossible outliers"


# --------------------------------------------------------------------------
# 2. Cleaning
# --------------------------------------------------------------------------
def test_cleaning_removes_duplicates_and_bad_dates(clean_df):
    assert clean_df.duplicated(subset=["date", "region"]).sum() == 0
    assert clean_df["date"].isna().sum() == 0
    assert pd.api.types.is_datetime64_any_dtype(clean_df["date"])


def test_cleaning_removes_impossible_values(clean_df):
    """-999 °C readings must not survive the cleaning step."""
    for col, (lo, hi) in cfg.VALID_RANGES.items():
        assert clean_df[col].between(lo, hi).all(), f"{col} still out of range"


def test_cleaning_leaves_no_missing_values(clean_df):
    for col in cfg.CLIMATE_COLUMNS:
        assert clean_df[col].isna().sum() == 0


def test_mixed_date_formats_are_parsed(raw_df):
    """Both YYYY-MM-DD and MM/DD/YYYY must become real timestamps."""
    parsed = preprocessing.parse_dates(raw_df.copy(), "date")
    assert parsed["date"].isna().sum() == 0


# --------------------------------------------------------------------------
# 3. Feature engineering
# --------------------------------------------------------------------------
def test_features_are_created(featured_df):
    for col in ("year", "month", "season", "t", "temp_anomaly",
                "temp_mean_c_roll12_mean", "rain_pct_of_normal", "heatwave_event"):
        assert col in featured_df.columns, f"missing feature: {col}"


def test_anomaly_is_centred_on_zero(featured_df):
    """The climatology baseline must give ~zero mean anomaly per region."""
    m = featured_df.groupby("region")["temp_anomaly"].mean().abs().max()
    assert m < 1e-9, f"anomalies are not centred (max |mean| = {m})"


# --------------------------------------------------------------------------
# 4. Trend analysis  (the statistical heart of the project)
# --------------------------------------------------------------------------
def test_mann_kendall_detects_an_increasing_series():
    """MK must report 'increasing' for a clearly rising series."""
    series = pd.Series(np.arange(120) * 0.1 + np.random.default_rng(0).normal(0, 0.2, 120))
    res = trend_analysis.mann_kendall(series)
    assert res["mk_trend"] == "increasing"
    assert res["mk_p_value"] < 0.05


def test_mann_kendall_detects_a_decreasing_series():
    series = pd.Series(np.arange(120) * -0.1 + np.random.default_rng(1).normal(0, 0.2, 120))
    res = trend_analysis.mann_kendall(series)
    assert res["mk_trend"] == "decreasing"


def test_mann_kendall_on_flat_series_finds_no_trend():
    series = pd.Series(np.random.default_rng(2).normal(50, 3, 240))
    res = trend_analysis.mann_kendall(series)
    assert res["mk_trend"] == "no significant trend"


def test_ols_slope_matches_a_known_trend():
    """
    A series rising 0.5 per step must be recovered with slope 0.5.

    The length is a multiple of 12 so that every calendar position carries
    the same number of observations - the seasonal adjustment then removes
    the seasonal cycle without touching the linear slope.
    """
    series = pd.Series(np.arange(120) * 0.5)
    res = trend_analysis.ols_trend(series)
    assert res["slope_per_year"] == pytest.approx(0.5 * 12, rel=1e-6)


def test_trends_agree_between_ols_and_mann_kendall(featured_df):
    """After seasonal adjustment the two methods must tell the same story."""
    t = trend_analysis.analyze_trends(featured_df, ["temp_mean_c"])
    for _, r in t.iterrows():
        assert r["slope_per_year"] > 0, f"{r['region']}: OLS slope should be positive"
        assert r["mk_trend"] == "increasing", f"{r['region']}: MK disagrees with OLS"


def test_deseasonalization_removes_the_seasonal_cycle():
    """A pure sine wave must lose its amplitude after deseasonalisation."""
    idx = pd.RangeIndex(120)
    wave = pd.Series(10 * np.sin(2 * np.pi * np.arange(120) / 12), index=idx)
    flat = trend_analysis.deseasonalize(wave, period=12)
    assert flat.abs().max() < 1e-9


# --------------------------------------------------------------------------
# 5. Anomaly detection
# --------------------------------------------------------------------------
def test_anomaly_detection_returns_expected_schema(featured_df):
    res = anomaly_detection.run_anomaly_detection(featured_df)
    assert not res["anomalies"].empty
    for col in ("anomaly_id", "date", "region", "method", "score", "severity"):
        assert col in res["anomalies"].columns


def test_injected_extreme_events_are_detected(featured_df):
    """The simulated heat-wave months must be picked up by the detectors."""
    res = anomaly_detection.run_anomaly_detection(featured_df)
    hot = res["anomalies"][res["anomalies"]["direction"] == "hot"]
    assert len(hot) > 0, "no hot anomalies detected"


# --------------------------------------------------------------------------
# 6. Forecasting
# --------------------------------------------------------------------------
def test_forecast_metrics_are_finite(featured_df):
    region = featured_df[featured_df["region"] == cfg.REGION_NAMES[0]]
    res = forecasting.forecast_region(region, h=12, test_size=36)
    assert res, "forecasting returned nothing"
    assert np.isfinite(res["metrics"]["RMSE"]).all()
    assert len(res["forecast"]) == 12


def test_seasonal_naive_beats_naive(featured_df):
    """A seasonal series must be forecast better by the seasonal baseline."""
    region = featured_df[featured_df["region"] == cfg.REGION_NAMES[1]]
    s = region.sort_values("date")["temp_mean_c"]
    train, test = s.iloc[:-36].to_numpy(), s.iloc[-36:].to_numpy()
    rmse_naive = forecasting.evaluate(test, forecasting.naive_forecast(train, 36))["RMSE"]
    rmse_seas = forecasting.evaluate(test, forecasting.seasonal_naive_forecast(train, 36))["RMSE"]
    assert rmse_seas < rmse_naive


# --------------------------------------------------------------------------
# 7. EDA
# --------------------------------------------------------------------------
def test_eda_tables_have_expected_columns(featured_df):
    bundle = eda.run_eda(featured_df)
    assert "temp_mean_c" in bundle["correlations"].columns
    assert len(bundle["yearly"]) == featured_df["region"].nunique() * featured_df["year"].nunique()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))


def test_simulator_peaks_match_hemispheres(clean_df):
    means=clean_df.groupby(['region','month']).temp_mean_c.mean()
    assert means['London'].idxmax()==7
    assert means['Sydney'].idxmax()==1
    assert means['Hyderabad'].idxmax()==4


def test_forecast_does_not_use_validation_targets(featured_df):
    d=featured_df[featured_df.region=='London'].sort_values('date').copy()
    original=forecasting.ml_forecast(d,h=6,test_size=60)
    d.loc[d.index[-60:],'observed_temp_mean_c'] += 100
    d.loc[d.index[-60:],'temp_mean_c'] += 100
    changed=forecasting.ml_forecast(d,h=6,test_size=60)
    np.testing.assert_allclose(original['validation_prediction'],changed['validation_prediction'])


def test_forecast_ignores_leaky_eda_features(featured_df):
    d=featured_df[featured_df.region=='London'].copy()
    a=forecasting.ml_forecast(d,h=6)
    for c in ['temp_mean_c_roll12_mean','enso_proxy','co2_ppm']:
        d[c]=99999
    b=forecasting.ml_forecast(d,h=6)
    np.testing.assert_allclose(a['validation_prediction'],b['validation_prediction'])
    np.testing.assert_allclose(a['forecast'].prediction,b['forecast'].prediction)


def test_original_missing_targets_preserved(clean_df):
    assert clean_df.observed_temp_mean_c.isna().sum()>0
    assert clean_df.temp_mean_c.isna().sum()==0
    assert (clean_df.loc[clean_df.observed_temp_mean_c.isna(),'data_quality_flag']=='repaired').all()


def test_public_snapshot_is_real_and_valid():
    path=cfg.PROCESSED_DIR/'noaa_co2_monthly.csv'
    if not path.exists():
        pytest.skip('Run python -m src.public_data for the public companion')
    public=pd.read_csv(path)
    assert len(public)==540
    assert public.co2_ppm.between(300,500).all()
    assert public.date.is_unique


def test_metrics_exclude_missing_truth():
    result=forecasting.evaluate([1,np.nan,3],[1,100,5])
    assert result['n_evaluated']==2
    assert result['MAE']==1
