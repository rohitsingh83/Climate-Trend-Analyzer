# Architecture

> How the Climate Trend Analyzer is put together, and why.

---

## 1. Design principles

| Principle | How it shows up in the code |
| --- | --- |
| **Separation of concerns** | Every stage is a module in `src/` with one job. `preprocessing.py` does not plot; `visualizations.py` does not compute statistics. |
| **Single source of truth** | `src/config.py` holds every path, threshold and simulation parameter. Change a number once, the whole project follows. |
| **Reproducibility** | The simulator is seeded (`RANDOM_SEED = 42`). The same numbers appear on every machine, every run. |
| **Auditability** | The cleaning stage returns a report dictionary of every counter; the report prints it as a table. |
| **No hidden state** | Each function takes a DataFrame and returns a DataFrame. The pipeline is the only place that wires them together. |
| **Testability** | 26 pytest tests cover the statistics, not just the plumbing. |

---

## 2. Block diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        1. DATA INGESTION                                │
│   data_generator.py  →  data/raw/climate_raw.csv  (messy on purpose)    │
│   data_loader.py     →  load_raw() / load_clean() / load_featured()     │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │  DataFrame (raw, 2,715 rows)
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       2. CLEANING  (preprocessing.py)                   │
│   standardise columns → parse mixed dates → drop duplicates →           │
│   coerce numerics → flag impossible values → impute (time + median)     │
│   OUTPUT: data/processed/climate_clean.csv   +  cleaning report dict   │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │  DataFrame (clean, 2,700 rows, 0 NaN)
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                3. FEATURE ENGINEERING  (features.py)                    │
│   calendar (year/month/season/decade/t) · 12-mo rolling mean & std ·    │
│   climatology baseline → anomalies (°C, %, z) · lags (1,2,3,12) ·        │
│   heat-wave & drought flags · ENSO proxy · cyclical month encoding       │
│   OUTPUT: data/processed/climate_featured.csv                           │
└───────┬──────────────────────────────────────────┬───────────────────────┘
        │                                          │
        ▼                                          ▼
┌────────────────────────┐            ┌────────────────────────────────────┐
│  4. EDA  (eda.py)      │            │  5. TREND ANALYSIS                 │
│  summary statistics    │            │  (trend_analysis.py)               │
│  correlation matrix    │            │  • seasonal decomposition (STL)    │
│  yearly aggregates     │            │  • OLS + month fixed effects       │
│  seasonal profile      │            │  • Mann-Kendall (from scratch)     │
│  warmest years         │            │  • Theil-Sen slope                 │
└───────────┬────────────┘            └───────────────┬────────────────────┘
            │                                         │
            ▼                                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    6. ANOMALY DETECTION  (anomaly_detection.py)         │
│   climatology z-score  ·  STL residual  ·  IQR fences  ·  Isolation     │
│   Forest  →  merged ANOMALY REGISTER (id, method, score, severity)      │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     7. FORECASTING  (forecasting.py)                    │
│   Naive · Seasonal naive · Drift · Ridge(eng. features) · ARIMA(grid)   │
│   → 60-month hold-out back-testing (MAE / RMSE / MAPE / R²)             │
│   → best model refit → 36-month projection with 95 % interval           │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│        8. INSIGHTS  →  9. VISUALISATION  →  10. REPORTING               │
│   insights.py            visualizations.py      report_generator.py     │
│   auto-written findings  17 publication charts   Markdown + HTML + CSV │
└───────────────────────────────┬──────────────────────────────────────────┘
                                ▼
              ┌─────────────────────────────────────────────┐
              │  CONSUMERS                                  │
              │  • Streamlit dashboard (app/app.py)         │
              │  • docs/INSIGHTS.md                         │
              │  • outputs/reports/climate_trend_report.md  │
              │  • outputs/tables/*.csv  (analyst hand-off)  │
              └─────────────────────────────────────────────┘
```

---

## 3. Module-by-module

| Module | Responsibility | Key public functions | Output |
| --- | --- | --- | --- |
| `config.py` | All paths, thresholds, simulation parameters | `PROJECT_ROOT`, `REGIONS`, `ANOMALY_Z_THRESHOLD` | — |
| `data_generator.py` | Simulates a realistic climate record + realistic defects | `generate_climate_dataset()`, `write_raw_dataset()` | `data/raw/climate_raw.csv` |
| `data_loader.py` | Access layer for every file the pipeline reads/writes | `load_raw()`, `load_clean()`, `load_featured()`, `save_table()` | — |
| `preprocessing.py` | Cleaning & quality control | `clean_dataset()`, `parse_dates()`, `quality_report_table()` | `data/processed/climate_clean.csv` |
| `features.py` | Feature engineering | `build_features()`, `add_climatology()`, `add_event_flags()` | `data/processed/climate_featured.csv` |
| `eda.py` | Exploratory analysis | `run_eda()`, `summary_statistics()`, `correlation_matrix()` | `outputs/tables/yearly_summary.csv` |
| `trend_analysis.py` | Trend statistics | `ols_trend()`, `mann_kendall()`, `deseasonalize()`, `seasonal_decomposition()` | `outputs/tables/trend_summary.csv` |
| `anomaly_detection.py` | Anomaly register | `detect_anomalies()`, `zscore_anomalies()`, `stl_anomalies()`, `iqr_outliers()`, `isolation_forest_anomalies()` | `outputs/tables/anomalies.csv` |
| `forecasting.py` | Model comparison & projection | `run_forecasting()`, `forecast_region()`, `arima_grid_search()`, `evaluate()` | `outputs/tables/model_metrics.csv`, `forecast_next_36m.csv` |
| `visualizations.py` | Every figure | `plot_temperature_trend()`, `plot_anomaly_detection()`, `plot_forecast()`, … | `outputs/figures/*.png` |
| `insights.py` | Natural-language findings | `generate_insights()`, `key_numbers()` | text block + dict |
| `report_generator.py` | Written deliverables | `build_markdown_report()`, `build_html_report()` | `outputs/reports/*` |
| `pipeline.py` | Orchestration | `run_pipeline()`, `stage_*()` | everything above |

---

## 4. Data flow contract

Each stage accepts and returns a **DataFrame with a documented schema** - this is what makes the pipeline replaceable.

| Stage | Key in | Key out | Row count |
| --- | --- | --- | --- |
| Ingestion | — | `date, region, country, latitude, longitude, temp_mean_c, temp_min_c, temp_max_c, rainfall_mm, humidity_pct, co2_ppm, sea_level_mm, sim_heatwave, sim_drought` | 2,715 |
| Cleaning | raw | same columns + `year, month, data_quality_flag` | 2,700 |
| Features | clean | + `quarter, season, decade, t, temp_clim, temp_std_clim, temp_anomaly, temp_anomaly_z, temp_anomaly_pct, rain_normal, rain_std_clim, rain_anomaly_pct, rain_anomaly_z, rain_pct_of_normal, *_roll12_mean, *_roll12_std, *_lag1/2/3/12, heatwave_month, heatwave_event, drought_month, drought_event, extreme_event, enso_proxy, month_sin, month_cos` | 2,700 |
| EDA | featured | 8 summary tables | — |
| Trends | featured | 25 rows (5 regions × 5 indicators) | — |
| Anomalies | featured | one row per method flag (overlaps possible) | method-level records |
| Forecast | featured | 5 × 36 = 180 projected rows | 180 |

**Swapping in a real dataset** only requires placing a CSV with the same column names in `data/raw/` with an appropriate source adapter; arbitrary datasets are not drop-in replacements.

---

## 5. Extending the system

| Extension | Where to add it |
| --- | --- |
| A new climate indicator | `config.CLIMATE_COLUMNS` + `config.VALID_RANGES` + the simulator's `_simulate_region` |
| A new region | `config.REGIONS` (one row) |
| A new anomaly method | a `*_anomalies()` function in `anomaly_detection.py` returning the standard schema |
| A new forecasting model | a function in `forecasting.py` returning `{"model", "metrics", "forecast"}` |
| A new chart | a `plot_*()` function in `visualizations.py` + one call in `pipeline.stage_visualize` |
| A live API feed | replace `data_loader.load_raw()` - the rest of the system is unchanged |


## Final validated implementation notes

- Forecasting bypasses retrospective centered/target-derived features. Ridge uses calendar/time only.
- ARIMA order is chosen by training AIC; a 60-month validation block chooses among models.
- Original target observations are retained; missing validation truth is not interpolated.
- OLS uncertainty uses HAC(12); full-model R² includes seasonal fixed effects. MK is exploratory, not pre-whitened.
- `src/public_data.py` independently analyzes real NOAA/Scripps CO₂, preserving attribution/checksum. It never joins it to synthetic city data.
- Public-source replacement needs a source-specific schema/coverage adapter, not renamed fictional variables.
- The full, current A–P guide and file-by-file source listing are in PROJECT_GUIDE.md and FULL_CODE.md.
