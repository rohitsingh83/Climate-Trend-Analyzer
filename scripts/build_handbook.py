"""Assemble current results, recruiter README and complete file-by-file handbook.
Run from project root AFTER the analytical pipeline and tests:
    python scripts/build_handbook.py
Generated documentation derives result numbers from the actual saved outputs.
"""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'


def table(df):
    d=df.copy()
    for c in d.select_dtypes('float'):
        d[c]=d[c].map(lambda x:f'{x:.3f}')
    return '| '+' | '.join(d.columns)+' |\n| '+' | '.join(['---']*len(d.columns))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in d.itertuples(index=False,name=None))


def main():
    summary=json.loads((ROOT/'outputs/run_summary.json').read_text())
    public=json.loads((ROOT/'outputs/noaa_summary.json').read_text())
    n=summary['key_numbers']
    trends=pd.read_csv(ROOT/'outputs/tables/trend_summary.csv')
    t=trends[trends.indicator=='temp_mean_c'].copy()
    t['CI low (°C/decade)']=t.ci_low*10;t['CI high (°C/decade)']=t.ci_high*10
    t=t.rename(columns={'region':'City','slope_per_decade':'Slope (°C/decade)','r_squared':'Full-model R²'})
    trend_table=table(t[['City','Slope (°C/decade)','CI low (°C/decade)','CI high (°C/decade)','Full-model R²']])
    anomalies=pd.read_csv(ROOT/'outputs/tables/anomalies.csv')
    unique=len(anomalies[['date','region']].drop_duplicates())
    metrics=pd.read_csv(ROOT/'outputs/tables/model_metrics.csv')
    best=metrics.loc[metrics.groupby('region').RMSE.idxmin(),['region','model','MAE','RMSE','R2','n_evaluated']]
    readme=f'''# 🌍 Climate Trend Analyzer

**A runnable, tested student portfolio: synthetic regional climate analysis plus a separate real public CO₂ companion.**

[Start here](START_HERE.md) · [Complete A–P guide](docs/PROJECT_GUIDE.md) · [Full code by file](docs/FULL_CODE.md) · [Methodology](docs/METHODOLOGY.md) · [Dataset card](docs/DATASET_CARD.md)

> **Source honesty:** city temperature, rainfall, humidity and sea-level demonstrations are **synthetic**. NOAA/Scripps Mauna Loa CO₂ is **real public data**, analyzed separately with attribution and provenance. This is not an institutional monitoring system, a real-world regional climate study or a physical climate projection.

## Overview and problem

Climate records combine repeating seasons, long-term changes, missing readings and genuine extremes. This project turns a reproducible monthly dataset into auditable cleaned tables, season-adjusted trend statistics, an anomaly investigation register, baseline-aware forecasts, charts, an HTML report and an interactive dashboard.

The system illustrates analytics workflows relevant to environmental research, energy-demand planning, agriculture and city adaptation. **No business savings or real-world prediction benefit is measured or claimed.**

## Quick start

Python 3.11/3.12 recommended (local verification also used 3.13). No GPU, paid API or institutional login.

```bash
python -m venv .venv
# Windows PowerShell: .\\.venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --step all
python -m pytest -q
python -m streamlit run app/app.py
```

Open `outputs/reports/climate_trend_report.html` for the standalone embedded-chart report.
Detailed Windows/CMD/macOS/Linux/Colab instructions are in [guide F](docs/PROJECT_GUIDE.md#f-installation--from-scratch).

## Implemented features

- Seeded simulation: five climates, hemisphere-aware seasons, warming, autocorrelated variability and explicit hot/dry stress episodes.
- Auditable cleaning: mixed dates, duplicate keys, invalid readings, historical gap interpolation and preserved original temperature targets.
- EDA: annual temperature means, annual rainfall totals, seasonal patterns, anomalies and correlations.
- Trends: OLS time + month fixed effects, **HAC(12)** uncertainty, exploratory deseasonalized Mann–Kendall and Theil–Sen slopes.
- Four detectors: climatology z-score, STL residual, IQR and Isolation Forest.
- Forecasting: naive, seasonal-naive, drift, calendar/trend Ridge and training-AIC-selected ARIMA; identical fixed-origin validation.
- Real public-data companion: NOAA/Scripps concentration CSV, original source comments, retrieval UTC and SHA256.
- Streamlit: filters, KPIs, four tabs, download buttons and a separate public-data section.
- Five executed notebooks, automated tests, CI definition and professional documentation.

## Results from the bundled synthetic experiment

| Item | Actual generated result |
| --- | --- |
| Raw / clean observations | {summary['rows_raw']:,} / {n['rows_analysed']:,} |
| Coverage | Five cities, January 1980–December 2024 |
| Mean estimated synthetic warming | +{n['mean_warming_c_per_decade']:.3f} °C/decade |
| Fastest simulated warming | {n['fastest_warming_region']}, +{n['fastest_warming_c_per_decade']:.3f} °C/decade |
| Detector records | {len(anomalies)} method flags across {unique} distinct city-months |
| Forecast | 36 monthly dates, January 2025–December 2027, from end-2024 origin |
| Lowest validation RMSE among candidates | {n['best_forecast_rmse']:.3f} °C (not an independent final-test score) |
| Core analysis measurement completeness | {n['data_completeness_pct']:.1f}% after historical cleaning |

### Season-adjusted temperature slopes

{trend_table}

Confidence intervals above are converted to **per decade**. The CSV stores CI bounds **per year**. Full-model R² includes **seasonality as well as trend**; it is not warming-only explanatory power. MK p-values are exploratory and uncorrected for serial dependence/multiple testing.

### Best model per city — chronological validation

{table(best)}

Models predict all 60 validation dates from the same origin. Originally missing targets are excluded from scoring (`n_evaluated`), not filled with fabricated truth. Ridge uses only future-known time/month features; it never uses centered EDA windows, observed future CO₂ or target-derived ENSO proxies. ARIMA order is chosen using training AIC. The final validation block selects the model; a separate untouched test is a future improvement.

## Real public-data result — not simulation

The analyzed NOAA/Scripps snapshot contains **{public['n_months']} months / {public['n_complete_years']} complete years** in 1980–2024. Annual concentration changes from **{public['first_complete_year_mean_ppm']:.2f} ppm** in 1980 to **{public['last_complete_year_mean_ppm']:.2f} ppm** in 2024. A descriptive linear annual slope is **{public['linear_slope_ppm_per_year']:.3f} ppm/year**; the underlying trajectory is not assumed perfectly linear.

Source: [NOAA GML CO₂ data](https://gml.noaa.gov/ccgg/trends/data.html). Attribution: **Xin Lan, NOAA/GML; Ralph Keeling, Scripps Institution of Oceanography**. Read original source comments for interpolation/measurement-interruption notes. CO₂ is **concentration in ppm, not emissions**. Source data is not relicensed by the project MIT license.

![Public CO2 observations](outputs/figures/16_public_noaa_co2.png)

## Architecture

```text
Synthetic generator -> raw CSV -> quality audit -> clean + observed target
                                  |                |
                       retrospective EDA/features  past-only forecast path
                                  |                |
                    OLS/HAC + MK + four detectors  baselines/Ridge/ARIMA
                                  \\              /
                             charts + tables + report + dashboard

NOAA public CSV -> provenance/cache -> independent concentration analysis
                                  -> public chart + table + dashboard section
```

[Detailed module contracts](docs/ARCHITECTURE.md) · [Method equations and limitations](docs/METHODOLOGY.md).

## Technology choices

| Layer | Stack |
| --- | --- |
| Language/data | Python, pandas, NumPy |
| Statistics/ML | SciPy, statsmodels, scikit-learn |
| Plots | Matplotlib, Seaborn, Plotly |
| UI | Streamlit |
| Learning/testing | Jupyter, nbconvert, pytest, GitHub Actions |
| Persistence | CSV, JSON, PNG, Markdown, self-contained HTML |

[Guide B–C](docs/PROJECT_GUIDE.md#b-tech-stack-options) compares easiest/intermediate/advanced options and explains why this CPU-only intermediate approach was selected.

## Folder structure

```text
Climate-Trend-Analyzer/
  main.py, README.md, START_HERE.md, requirements*.txt, LICENSE
  src/             generator, loader, cleaning, features, EDA, trends,
                   anomalies, forecasting, public_data, plots, insights, reports
  app/app.py       Streamlit dashboard
  tests/           data/statistical/leakage tests
  notebooks/       five executed tutorials
  scripts/         portable notebook and handbook builders
  data/raw/        synthetic feed + original NOAA snapshot/provenance
  data/processed/  clean/featured synthetic tables + separate public CO2
  outputs/figures/ generated charts
  outputs/tables/  trend, anomaly, annual, forecast and model-selection tables
  outputs/reports/ Markdown + HTML analytical report
  images/          actual dashboard captures and curated proof charts
  docs/            complete A–P guide, full source, science/data/career/GitHub docs
  .github/         CI definition
```

## Run stages individually

```bash
python main.py --step simulate --regenerate
python main.py --step clean
python main.py --step features
python main.py --step eda
python main.py --step trends
python main.py --step anomalies
python main.py --step forecast
python main.py --step report
python main.py --summary
# Public track, offline cached snapshot:
python -m src.public_data
# Explicit network refresh:
python -m src.public_data --refresh
# Rebuild and execute the tutorial notebooks:
python scripts/build_notebooks.py --execute
```

`python main.py --no-forecast` runs the historical analysis faster. Existing forecast files may remain from a previous full run; use the full run for a coherent demo and check file timestamps. Refresh Streamlit's cache after regenerating inputs. For actual delivered logs see `outputs/latest_run.log`, `outputs/test_results.txt` and `outputs/notebook_execution.log`.

## Virtual simulation workflow

1. Define city baselines, warm peak months and illustrative slopes.
2. Generate the monthly calendar, cosine seasonality, multi-year oscillations and AR(1) noise.
3. Inject labeled three-month hot/dry experiments.
4. Add missing values, duplicates, impossible readings and mixed date strings.
5. Clean and audit; preserve original targets.
6. Explore seasonality, estimate slopes, inspect detector flags and measure planted-event recall.
7. Validate forecasts at a fixed origin, export charts/tables/report and inspect the dashboard.

These monthly persistence proxies are not daily WMO heatwave or validated drought-index declarations. The synthetic global-like sea-level field is not local sea-level monitoring at an inland city.

## Screenshots and charts

### Actual browser dashboard

![Actual dashboard capture](images/09_dashboard.png)

### Seasonal trend and detector examples

![Synthetic temperature record](outputs/figures/02_temperature_trend.png)
![HAC uncertainty on simulated slopes](outputs/figures/07_warming_rate_by_region.png)
![Flagged simulated months](outputs/figures/09_anomaly_detection.png)
![Forecast validation](outputs/figures/15_model_comparison.png)
![Fixed-origin projection](outputs/figures/14_forecast.png)

Non-ARIMA bands use ±1.96×validation RMSE: **approximate and uncalibrated**, not guaranteed 95% coverage or physical climate-model ranges. Trend/forecast origin and source type must remain visible in presentations.

[All proof/capture instructions](docs/SCREENSHOTS.md) · [Actual dashboard GIF](images/dashboard_demo.gif).

## Tests and CI

```bash
python -m pytest -v
```

**26 tests passed locally** in the delivered run. Tests cover seeded generation, mixed-date parsing, range repairs, feature behavior, known trend recovery, MK sign/direction, hemisphere peaks, original missing targets, baseline comparisons, public schema and forecast leakage.

The CI workflow is defined for Python 3.10/3.11/3.12 with unique artifact names. **Remote CI has not been claimed to pass before you publish and run it.** Set an actual CI badge only after creating your repository. Exact locally tested package versions are in `requirements-tested.txt`; portable ranges are in `requirements.txt`.

## Limitations and future improvements

- Regional measurements are synthetic. Public source adapters must preserve true scope/units and cannot fabricate missing variables.
- Full-record climatologies are retrospective; prospective anomaly detection needs a fixed past reference period.
- Full-model R² includes seasons; exploratory MK is not serial-correlation/multiple-testing corrected.
- Detector outputs overlap; cross-method scores are not calibrated risk scores.
- Forecast selection uses validation, not a final independent test; bands are approximate.
- No climate attribution, area-weighted global index, measured savings or official warning is produced.

Next: real station/reanalysis adapters, coverage-aware annual aggregation, fixed 30-year normals, rolling-origin + independent final testing, interval calibration, daily extremes, geospatial exposure and CMIP6 scenarios. [Ordered upgrade plan](docs/PROJECT_GUIDE.md#o-future-improvements--ordered-by-value).

## Learning outcomes and portfolio publishing

You can demonstrate auditable data cleaning, time-series reasoning, honest prediction protocols, complementary anomaly methods, reproducible software design and stakeholder communication. Learn the code and limitations before using the résumé bullets.

- [Full GitHub upload commands and topics](docs/GITHUB_PLAYBOOK.md)
- [Eight-day genuine learning/commit plan](docs/PROJECT_GUIDE.md#l-commit-strategy--eight-day-genuine-proof-plan)
- [Résumé, three LinkedIn posts, ten interview answers](docs/PROJECT_GUIDE.md#n-résumé-linkedin-and-interview-presentation)
- [Beginner troubleshooting](docs/PROJECT_GUIDE.md#p-troubleshooting--reason-solution-prevention)

## Author and attribution

**Student author: add your own name, profile links and contribution details before publishing.** Do not claim sole authorship of AI-assisted code or a fabricated development timeline. Local commits are genuine same-session build checkpoints, not an eight-day history. A GitHub push, your own narrated recording and permanent deployment require your own account/actions.

Code and project-generated simulation: [MIT](LICENSE). External NOAA/Scripps data: retain source attribution and usage notes. The source is publicly accessible; institutional endorsement is not implied.
'''
    (ROOT/'README.md').write_text(readme)
    explanations={
        'main.py':'Command-line runner: full workflow or an individual named stage.',
        'app/app.py':'Dashboard reads saved results and distinguishes synthetic cities from public observations.',
        'src/config.py':'Centralized filesystem paths, thresholds and simulation parameters.',
        'src/data_generator.py':'Reproducible synthetic measurement system, explicit injected episodes and dirty data.',
        'src/data_loader.py':'CSV/JSON access layer and dataset-profile helper.',
        'src/preprocessing.py':'Auditable historical cleaning with preserved original targets for temporal evaluation.',
        'src/features.py':'Retrospective exploratory features; these are not automatically safe prediction inputs.',
        'src/eda.py':'Descriptive statistics, correlations, seasonal and annual aggregations.',
        'src/trend_analysis.py':'Season-controlled OLS with HAC uncertainty and exploratory MK/Theil–Sen cross-checks.',
        'src/anomaly_detection.py':'Four complementary detectors; register rows are method flags, not unique events.',
        'src/forecasting.py':'Common fixed-origin validation with future-known predictors and train-only filling.',
        'src/public_data.py':'Separate public NOAA CO2 ingestion, attribution, checksum and concentration analysis.',
        'src/visualizations.py':'Shared chart functions and self-contained-image helpers.',
        'src/insights.py':'Natural-language findings computed from saved statistical results.',
        'src/report_generator.py':'Markdown and embedded-image HTML report assembly.',
        'src/pipeline.py':'Orchestration of the analysis stages and saved run metadata.',
        'tests/test_pipeline.py':'Scientific/data/leakage regression tests; execute with python -m pytest.',
        'scripts/build_notebooks.py':'Portable notebook construction and execution, failing on execution errors.',
        'scripts/build_handbook.py':'Builds this source listing and current-results README from actual saved outputs.',
    }
    files=[ROOT/'main.py',*sorted((ROOT/'src').glob('*.py')),ROOT/'app/app.py',ROOT/'tests/test_pipeline.py',*sorted((ROOT/'scripts').glob('*.py')),ROOT/'requirements.txt',ROOT/'requirements-tested.txt',ROOT/'.gitignore',ROOT/'.github/workflows/ci.yml',ROOT/'README.md']
    chunks=['# Full implementation — Climate Trend Analyzer\n\nEvery file below also exists as a runnable file in the repository. No placeholders replace analytical code. Filenames are relative to the project root. Notebook JSON is not pasted here: all five executed .ipynb files are included, and the complete builder below reproduces them.\n']
    for f in files:
        rel=f.relative_to(ROOT).as_posix()
        lang='python' if f.suffix=='.py' else ('yaml' if f.suffix=='.yml' else 'text')
        fence='````' if f.name=='README.md' else '```'
        chunks.append(f'\n## `{rel}`\n\n{fence}{lang}\n{f.read_text()}\n{fence}\n\n**What this file does:** {explanations.get(rel,"Project configuration, installation or recruiter-facing documentation. See the corresponding section in PROJECT_GUIDE.md.")}\n')
    code='\n'.join(chunks)
    (DOCS/'FULL_CODE.md').write_text(code)
    (DOCS/'COMPLETE_HANDBOOK.md').write_text((DOCS/'PROJECT_GUIDE.md').read_text()+'\n\n---\n\n# Appendix — complete executable source, file by file\n\n'+code)
    print('Built README.md, docs/FULL_CODE.md and docs/COMPLETE_HANDBOOK.md')


if __name__=='__main__':
    main()
