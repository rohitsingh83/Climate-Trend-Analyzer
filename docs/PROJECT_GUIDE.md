# Climate Trend Analyzer — Complete Student Build Guide

**A practical handbook for building, running, explaining and publishing this project.**

The runnable repository is already implemented. This guide explains the design and provides the learning, GitHub and career steps. `FULL_CODE.md` contains the complete source file-by-file; it is not pseudocode. `README.md` is the recruiter-facing landing page. Work through the notebooks in order before claiming the project on your résumé.

> Integrity first: the five-city dataset is synthetic. The NOAA/Scripps CO₂ companion is real public data. They are kept separate. No government access, real sensor deployment, real-world savings, institutional affiliation or physical climate projection is claimed. All local commits were created during this build, not over eight days; the eight-day schedule below is a suggested learning plan, not a fabricated history.

## Contents — requested A–P order

A. Project explanation • B. Tech stack options • C. Selected best approach • D. Architecture • E. Folder structure • F. Installation • G. Full code • H. Virtual simulation • I. Run instructions • J. GitHub upload • K. README • L. Commit strategy • M. Proof checklist • N. Career presentation • O. Future improvements • P. Troubleshooting

---

## A. Project explanation

### A1. In plain language

A Climate Trend Analyzer is a system that reads many years of climate measurements and helps you see what changes slowly, what repeats every year, and what looks unusual. Think of a long household electricity bill: summer bills rise every year, but you also want to know whether the overall baseline is rising. Temperature and rainfall have the same problem: a hot summer is not automatically evidence of long-term warming.

This project answers:
1. How quickly is each simulated city's average temperature changing?
2. Which months are unusually hot, cold or wet relative to their season?
3. How do rainfall and humidity vary through the year?
4. Which simple forecasting method works best on a later, unseen period?
5. What does a separate real public CO₂ series show?

The output is not merely a trained model. It includes cleaned datasets, auditable quality counters, charts, statistical tables, a detector register, validation scores, an interactive dashboard and an automatically generated report.

### A2. In technical language

The system is a modular monthly panel/time-series pipeline. The primary key is `(region, date)` and the synthetic record contains 540 monthly observations for each of five regions, January 1980–December 2024. Cleaning normalizes dates and numeric types, removes duplicate keys, identifies physically impossible readings and interpolates historical gaps. The original observed temperature target is retained for temporal evaluation.

Exploration uses regional/calendar-month climatologies, descriptive summaries, annual aggregates, lag features and retrospective rolling statistics. Long-term slopes are estimated using OLS with calendar-month fixed effects, with Newey–West/HAC(12) covariance for uncertainty. A deseasonalized Mann–Kendall test and Theil–Sen slope provide exploratory cross-checks; MK is not serial-correlation corrected. Anomaly detection combines calendar-month z-scores, robust STL residuals, Tukey fences and Isolation Forest. Forecasting compares fixed-origin multi-step baselines, calendar/trend Ridge and training-AIC-selected ARIMA. Model choice uses a chronological 60-month validation block, not a final unbiased test set.

### A3. Real-world problem and relevance

| Stakeholder | Question | How this kind of system helps | What additional work production needs |
| --- | --- | --- | --- |
| Government analyst | Are seasonal water-demand assumptions changing? | Annual rainfall summaries and uncertainty | Official quality-controlled stations, long reference period |
| Research organization | Is a trend statistically distinguishable from noise? | Season-adjusted slopes, robust uncertainty | Sensitivity analysis, autocorrelation-aware nonparametric inference |
| Climate analyst | Which months deserve investigation? | Traceable detector register | Station metadata and expert review |
| Smart-city planner | Are prolonged hot periods becoming a planning concern? | Seasonal patterns and heat-stress proxies | Daily extremes, vulnerability and infrastructure exposure |
| Environmental agency | Can recurring reports be reproduced? | Versioned code, data provenance, generated reports | Governance, access control and operational monitoring |
| Energy analyst | Could warming change cooling demand? | Regional temperature trend | Electricity load and causal/operational validation |
| Agritech analyst | When are unusual dry months observed? | Rainfall ratios and drought proxies | Soil moisture, crop calendar and calibrated drought index |
| Insurance analyst | Which hazards need assessment? | Frequency summaries and outlier candidates | Asset exposure, calibrated return periods and loss data |

These are use cases, not measured savings. The project does not establish any market size, employer adoption, crop-loss reduction or cost-benefit percentage. Do not reuse uncited promotional statistics from the original project brief as if this build verified them.

### A4. What each indicator tells you

- **Temperature:** long-term level change after seasonal adjustment; anomalies express deviation from local month normals.
- **Rainfall:** monthly totals and annual sums reveal wet/dry variation. A missing month is not zero rainfall; partial years require coverage checks.
- **Humidity:** describes co-variation, not a causal relationship inferred from a correlation heatmap.
- **CO₂:** atmospheric concentration is measured in **ppm**; emissions are a mass per time (e.g. tonnes/year). These are not interchangeable.
- **Sea level:** the simulator uses a global-like illustrative series relative to its 1980 baseline. It is not a local sea-level measurement at inland Hyderabad.
- **Seasonal shifts:** the current project compares seasonal profiles and hemisphere-dependent peaks. It does not yet infer a changing monsoon-onset date; that requires daily data and a defined onset algorithm.
- **Ice/glaciers:** extension only, not an implemented metric.

### A5. Full workflow

`collect/cache → inspect → clean → engineer → explore → estimate trends → detect anomalies → validate forecasts → visualize → report → communicate`.

Collection records units, coverage and provenance. Cleaning protects data quality without deleting legitimate extreme weather. Features distinguish historical descriptive variables from predictors known at forecast time. EDA guides methods. Trend inference controls for the calendar. Detectors nominate cases for investigation. Forecast evaluation compares against credible baselines. Reporting communicates uncertainty and source limitations.

### A6. Implementation phases, outputs, mistakes and verification

| Phase | What to do and why | Expected output | Common mistake | Completion check |
| --- | --- | --- | --- | --- |
| 1 — environment | Install Python, isolate packages in `.venv` | Working interpreter and imports | Installing into another interpreter | `python -m pip --version` points into `.venv` |
| 2 — structure | Read config and create modules by responsibility | `src/`, `data/`, `outputs/`, docs | One enormous notebook with hidden state | Import every module independently |
| 3 — collection | Generate synthetic CSV; inspect NOAA snapshot provenance | Two clearly separated raw sources | Calling synthetic numbers real observations | Inspect CSV headers and source card |
| 4 — cleaning | Parse mixed dates, deduplicate, validate ranges, impute | Clean table and quality audit | Global mean imputation; deleting all extremes | Unique `(region,date)`, valid ranges, no missing core analysis values |
| 5 — EDA | Inspect distributions, coverage, annual and seasonal charts | Summary and correlation tables | Comparing an annual sum with monthly means | Recompute one year manually and compare |
| 6 — features | Create calendar, climatology, lag and event variables | Featured CSV | Feeding centered windows into prediction | Forecast function only accepts calendar/time features |
| 7 — trends | Fit time + month effects; compute HAC uncertainty and MK | 25 indicator-region rows | Treating seasonal R² as trend-only explanatory power | Synthetic known-slope test; report full-model R² label |
| 8 — anomalies | Run four detectors with explicit thresholds | Detector register | Counting method rows as independent events | Compare total records to unique `(date,region)` count |
| 9 — forecasting | Reserve last 60 months and predict full block | Model comparison and 36-month forecast | Random split; using observed future lags | Target-perturbation leakage test passes |
| 10 — communication | Produce charts and written insights from results | PNGs, Markdown, self-contained HTML | Narrative contradicts computed values | Read every insight and check its table |
| 11 — tests | Run unit and statistical regression tests | Saved pytest log | Only checking that code does not crash | See passing leakage, trend and season tests |
| 12 — publishing | Clean identity placeholders, push and inspect Actions | Public repository and real CI result | Claiming a badge is green before CI runs | Open Actions run and inspect logs |
| 13 — presentation | Practice a demo and limitation discussion | Résumé bullets and demo | Claiming production deployment or climate causation | Explain synthetic vs public tracks in one sentence |

---

## B. Tech stack options

| | Option A — easiest | Option B — intermediate | Option C — advanced |
| --- | --- | --- | --- |
| Tools | Python, pandas, NumPy, Matplotlib, Jupyter | A + SciPy, statsmodels, scikit-learn, Plotly, Streamlit, pytest | B + xarray, Dask, GeoPandas, Zarr/NetCDF, orchestration/cloud |
| Analysis | Cleaning, annual/seasonal charts, simple linear trend and z-score | Seasonal fixed effects, HAC CI, STL, Isolation Forest, baseline/Ridge/ARIMA comparison | Gridded ensembles, geospatial risk, CMIP6 scenarios, calibrated extremes |
| Difficulty | Beginner, roughly 2–4 focused study days | Beginner-to-intermediate, approximately 8–14 study days | Advanced, several weeks or months |
| GPU | No | No | Usually no for statistics; optional for deep learning |
| Outcome | One readable exploratory notebook | Reproducible tested package, dashboard, report and evidence | Distributed research-style workflow |
| Best use | First contact with time series | **Strong student GitHub proof without unnecessary complexity** | Upgrade after mastering validation and real data |

Time estimates are learning estimates, not guarantees. Deep learning is not automatically better: a simple model that fairly beats seasonal-naive is a stronger interview story than an unevaluated LSTM.

## C. Selected best approach

**Option B, implemented with a simple forecasting feature set.** Historical analysis can be rich; forecasting should stay honest. Ridge uses `time_index`, `sin(month)` and `cos(month)` only. These predictors are known for any future date and cannot leak current/future target values. There is no GPU, paid API, institutional login, sensor purchase, Docker requirement or unnecessary database.

Two tracks:
1. **Synthetic cities:** the entire clean → EDA → trends → anomalies → forecast → dashboard workflow, offline and reproducible.
2. **Public observations:** NOAA/Scripps Mauna Loa CO₂, a bundled snapshot with attribution and checksum, independently analyzed for 1980–2024. No fictional regional measurements are created from it.

A statistical extrapolation is not a physical climate projection or a validated weather warning. Monthly three-month hot/dry runs are **educational persistence proxies**, not daily meteorological heatwave declarations or a validated SPI/SPEI drought index.

## D. Architecture

```text
Synthetic generator -> raw climate CSV -> quality-control -> clean + observed target
                                                     |
                         retrospective features / EDA / trend / anomaly register
                                                     |
                         independent forecast path (original observations only)
                         train-only filling -> calendar Ridge / baselines / ARIMA
                                                     |
                         tables + figures + narrative + Streamlit + HTML report

Public NOAA CSV -> attribution + SHA256 -> unit/sentinel checks -> monthly/annual CO2
                                                     |
                         separate public chart + summary + dashboard companion
```

The synthetic pipeline is orchestrated in `src/pipeline.py`. Each module has a public function with a small input/output contract; `main.py` is the CLI. Paths and thresholds live in `src/config.py`. The dashboard reads persisted tables and does not retrain models on each click. Network refresh is explicit (`python -m src.public_data --refresh`); the regular run uses the bundled snapshot.

See `ARCHITECTURE.md` for the per-module contract and `METHODOLOGY.md` for equations and assumptions.

## E. Folder structure

```text
Climate-Trend-Analyzer/
  main.py                       command-line runner
  README.md                     public landing page
  START_HERE.md                 fastest safe entry point
  requirements.txt              compatible dependency ranges
  requirements-tested.txt       exact local verification versions
  LICENSE                       MIT for project code, not a relicensing of NOAA
  .gitignore                    excludes venv, caches and secrets
  .github/workflows/ci.yml       CI for Python 3.10 / 3.11 / 3.12
  app/app.py                    interactive Streamlit dashboard
  src/                          modular source code (see section G)
  tests/test_pipeline.py         automated scientific and data tests
  scripts/build_notebooks.py     portable notebook builder/executor
  scripts/build_handbook.py      assembles full code and handbook
  notebooks/01...05*.ipynb       five executed tutorial notebooks
  data/raw/                     synthetic CSV + unchanged NOAA source + provenance
  data/processed/               clean, featured, public CO2 tables
  models/                       reserved for optional fitted-model serialization
  outputs/figures/              generated analysis PNGs
  outputs/tables/               analytical CSV tables
  outputs/reports/              Markdown and embedded-image HTML reports
  outputs/latest_run.log        actual saved local execution log
  outputs/test_results.txt       actual local pytest output
  outputs/run_summary.json       synthetic run metadata
  outputs/noaa_summary.json      separate public-data results
  images/                       actual dashboard captures and curated charts
  docs/PROJECT_GUIDE.md          this A–P handbook
  docs/FULL_CODE.md              complete runnable code file-by-file
  docs/METHODOLOGY.md            statistical choices and caveats
  docs/DATASET_CARD.md           source, units, defects and license notes
  docs/SCREENSHOTS.md            capture and recording checklist
  docs/CAREER_KIT.md             ready-to-edit interview/résumé copy
  docs/GITHUB_PLAYBOOK.md        publishing and genuine proof strategy
```

The source of truth for a generated chart is its generating function, not a manually edited image. Empty reserved directories are not essential for execution and are recreated by config if needed. The archive includes all code and example outputs; no `node_modules`, `.venv` or package cache is included.

## F. Installation — from scratch

### F1. Hardware/software

A modern CPU, 4 GB RAM minimum (8 GB preferred) and roughly 2 GB free for Python/packages are adequate for this small CSV project. No GPU. Internet is needed for initial package installation and optional public-source refresh, not for the bundled offline run. Install Python **3.11 or 3.12 recommended** and Git. The delivered run was also verified with Python 3.13. Use VS Code with Python/Jupyter extensions or JupyterLab.

### F2. Windows PowerShell

```powershell
# Extract the ZIP first, then open its project directory:
cd Climate-Trend-Analyzer
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import pandas,numpy,scipy,sklearn,statsmodels,streamlit; print('Imports OK')"
python main.py --step all
python -m pytest -v
python -m streamlit run app/app.py
```

If Python 3.11 is not installed, use `py -3.12` or your installed supported interpreter. If activation is blocked, you need not weaken machine-wide execution policy: run `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and use that executable for later commands. For CMD activation: `.venv\Scripts\activate.bat`.

### F3. macOS/Linux

```bash
cd Climate-Trend-Analyzer
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import pandas,numpy,scipy,sklearn,statsmodels,streamlit; print('Imports OK')"
python main.py --step all
python -m pytest -v
python -m streamlit run app/app.py
```

On Ubuntu, a missing `venv` module may require `sudo apt install python3-venv`. On macOS use an installed Python 3.11/3.12 rather than modifying system Python.

### F4. Record your own environment

```bash
python --version
python -m pip --version
python -m pip check
python -m pip freeze > requirements-local.txt
```

Do not replace curated `requirements.txt` with every unrelated package from a global Python environment. `requirements-tested.txt` records exact versions used in this workspace; it is environment-specific and not a promise that all those wheels work on every older Python version.

### F5. Google Colab

Colab already provides a Python notebook runtime; do **not** `pip install google-colab` to create one locally. Upload and unzip the project in Colab, then run:

```python
%cd /content/Climate-Trend-Analyzer
!pip install -r requirements.txt
!python main.py --step all
!python -m pytest -q
from IPython.display import Image, display
display(Image('outputs/figures/02_temperature_trend.png'))
```

Use notebooks and generated reports in Colab. Exposing Streamlit from Colab requires separate tunneling; local execution or a proper hosted deployment is simpler and safer.

## G. Full code, file-by-file

**Every complete implementation file appears in [`FULL_CODE.md`](FULL_CODE.md)** in filename → full code → explanation order. The same files already exist as runnable files; you do not need to copy code out of Markdown to run them. This separation keeps this handbook readable while still shipping all executable code.

| File | What it does |
| --- | --- |
| `main.py` | CLI argument parsing and full/single-stage execution |
| `src/config.py` | Central paths, variables, simulation parameters and thresholds |
| `src/data_generator.py` | Hemisphere-aware climate simulation, planted hot/dry episodes and dirty-data injection |
| `src/data_loader.py` | Raw/clean/featured readers, CSV/JSON persistence helpers |
| `src/preprocessing.py` | Mixed-date parsing, duplicate removal, range checks, historical interpolation and preserved observed target |
| `src/features.py` | Calendar, hemisphere seasons, descriptive rolling, climatology, lags and persistent event flags |
| `src/eda.py` | Descriptive, annual, seasonal and correlation summaries |
| `src/trend_analysis.py` | Month-fixed-effect OLS, HAC uncertainty, MK, Theil–Sen and STL |
| `src/anomaly_detection.py` | Four detectors and a method-level, not deduplicated, register |
| `src/forecasting.py` | Calendar Ridge, naive/seasonal/drift baselines, AIC-selected ARIMA, identical fixed-origin validation |
| `src/public_data.py` | NOAA download/cache, provenance, real concentration analysis and chart |
| `src/visualizations.py` | Consistent PNG plot functions |
| `src/insights.py` | Data-derived findings and machine-readable headline numbers |
| `src/report_generator.py` | Markdown and self-contained HTML reports |
| `src/pipeline.py` | Wires the workflow together and saves results |
| `app/app.py` | Four-tab dashboard plus separate public-data companion |
| `tests/test_pipeline.py` | Tests for quality, trends, seasonality, leakage and public schema |
| `scripts/build_notebooks.py` | Generates and executes the five tutorial notebooks |

### Reading order for a beginner

Read config → generator → preprocessing → features → EDA first. Then understand OLS and seasonal controls before reading the custom MK function. Treat Isolation Forest and ARIMA as optional deeper study after you can explain the baselines. If the code feels too large, run `--no-forecast` and learn one stage at a time. An advanced upgrade should improve a measured weakness, not simply add a fashionable model.

## H. Virtual simulation workflow

### H1. What is virtual here?

It is **software simulation of climate measurements and data-collection defects**, not access to NASA's systems, a digital twin calibrated to a real city, or an ESP32 hardware simulator. The synthetic generator stands in for a monthly data feed. The real public companion is an openly downloadable CSV.

### H2. Represent the data

A row contains month-start `date`, city `region`, country, latitude, longitude, mean/min/max temperature in °C, rainfall total in mm, humidity in %, concentration in ppm, a global-like sea-level indicator in mm and explicit injected-event labels. Use one row per city-month; never mix daily rainfall totals and monthly mean temperature without defining aggregation.

### H3. Build realistic statistical structure

1. Create 540 monthly dates for 1980–2024.
2. Give each city a baseline temperature and annual amplitude.
3. Use `amplitude * cos(2π(month−peak)/12)` so the intended peak is warmest (London July, Sydney January).
4. Add a modest region-specific linear warming term.
5. Add oscillations around 4.3 and 2.1 years as educational ENSO-like variability.
6. Add AR(1) weather noise with correlation 0.25 plus independent noise.
7. Inject three three-month hot episodes of +4.5 °C per city; save exact labels.
8. Simulate nonnegative gamma-distributed rainfall, with a July-oriented monsoon factor for Hyderabad. Inject three dry episodes by reducing rainfall to 15% of its generated value.
9. Make humidity inversely associated with local temperature, clipped to valid physical bounds.
10. Simulate illustrative accelerating CO₂ and sea level; **do not interpret these as measured city drivers or causal attribution**.
11. Deliberately add missing readings, duplicate keys, impossible temperatures and alternate date strings.

### H4. Execute and inspect, step by step

```bash
python main.py --step simulate --regenerate
python main.py --step clean
python main.py --step features
python main.py --step eda
python main.py --step trends
python main.py --step anomalies
python main.py --step forecast
python main.py --step report
python -m src.public_data
python -m streamlit run app/app.py
```

Inspect the raw data before cleaning; compare the cleaning audit after. Read one trend row, one detector row and one forecast validation row. Use the notebooks to check recall against the explicit injected events. Low recall is a result to investigate, not a number to conceal. Different methods and business thresholds identify different concepts of unusualness.

### H5. How the analysis finds the patterns

- **Long-term trend:** time coefficient after controlling for calendar month; HAC uncertainty accounts approximately for serial dependence.
- **Temperature anomaly:** observed monthly mean minus that city's calendar-month normal; z-score divides by the month-specific spread.
- **Rain anomaly:** deviations relative to the month-specific rainfall distribution. Gamma-skewed dry months may not cross a symmetric negative z threshold; a separate rainfall-ratio drought proxy helps illustrate this limitation.
- **STL:** separates trend/seasonality/residual and flags unusual residuals.
- **Forecast:** future-known time/calendar variables only; the last 60 months are withheld and predicted as a block before selecting a winner.

The full-record climatology is a **retrospective descriptive baseline**, not a fixed official 1991–2020 climate normal. A prospective detector must fit its baseline on a historical reference period only. A three-month run is flagged once the third month has arrived; it does not retrospectively label the first two months as known events at their start.

### H6. Save proof

Save input preview, quality counters, annual/seasonal charts, trend table with units, method register, model comparison, forecast, HTML report and dashboard captures. Keep terminal logs and test results. Explain that labels describe planted synthetic episodes, not externally verified weather disasters. See section M for names and capture steps.

## I. How to run and what success looks like

### I1. One-command path

```bash
python main.py --step all
python main.py --summary
```

The run should complete without traceback and create processed data, charts, tables, the Markdown/HTML report, insights and run metadata. Runtime depends on laptop and package versions; inspect `outputs/latest_run.log` for the actual delivered execution, not a fabricated console transcript.

### I2. Notebook path

```bash
python -m jupyterlab
# Open notebooks/01_Data_Loading_and_Cleaning.ipynb, then 02 → 05.
# Or regenerate all tutorial notebooks and execute them:
python scripts/build_notebooks.py --execute
```

Run from project root or its `notebooks/` child. Restart the notebook kernel and Run All to prove it does not depend on hidden cell state. The builder exits on execution error rather than silently shipping failing notebooks.

### I3. Public source path

```bash
python -m src.public_data              # analyze cached snapshot, offline
python -m src.public_data --refresh    # explicitly retrieve new public snapshot
```

Results: `data/processed/noaa_co2_monthly.csv`, `outputs/tables/noaa_co2_annual.csv`, `outputs/noaa_summary.json`, `outputs/figures/16_public_noaa_co2.png`. The complete source file contains newer observations too, but the analysis intentionally uses the completed common window through December 2024. Refresh may revise historical observations; check the provenance checksum.

### I4. Dashboard path

```bash
python -m streamlit run app/app.py
```

Select regions and indicator; adjust date range; inspect Trends, Anomalies, Forecast and Data tabs. Download filtered CSVs. Trend KPI/table use the **full record**, explicitly labeled; the date slider controls displayed series and anomaly records. Forecast is a demonstration issued from the end-2024 record, not a live forecast issued on the day you run the project.

### I5. Expected files and table interpretation

- `trend_summary.csv`: `slope_per_decade` is per decade; `ci_low/ci_high` are **per year**. Multiply bounds by 10 for a decade interval. `r_squared` belongs to the whole trend-plus-season model, not trend alone.
- `anomalies.csv`: multiple methods can flag the same month. Report both method-record count and deduplicated `(date,region)` count.
- `model_metrics.csv`: MAE/RMSE in °C, R², number of actually observed validation targets. Missing targets are excluded from scoring, not replaced with interpolated truth.
- `forecast_next_36m.csv`: January 2025–December 2027, point estimate and approximate bounds. Ridge/baseline bands use `±1.96 × validation RMSE`; coverage is uncalibrated and parameter/regime uncertainty is incomplete.
- `yearly_summary.csv`: rainfall is annual sum, temperature is annual mean, for the complete synthetic calendar.
- `climate_trend_report.html`: standalone embedded charts, so downloaded viewing does not need external image/font services.

All current numerical examples appear in the README and actual generated tables. Package versions can change ARIMA convergence/order slightly; cross-platform bitwise-identical images and timestamps are not promised.

## J. GitHub upload steps

### J1. Prepare identity and content

1. Set your name, links and contact details in README; do not leave placeholders.
2. Read the code and rerun it yourself. State AI assistance honestly where applicable; do not claim to have written components you cannot explain.
3. Keep code, requirements, tests, notebooks, small input data, provenance, charts, tables and documentation.
4. Exclude `.venv`, package caches, API tokens, `.env`, IDE secrets and large raw satellite archives.
5. In GitHub choose **New repository** → `climate-trend-analyzer` → Public → description below. If pushing an existing local repository, create an **empty** remote (no additional README).

**Repository description:** `Reproducible climate analytics portfolio: synthetic multi-city trends, anomaly detection, leakage-safe forecasting, NOAA CO2 companion and Streamlit dashboard.`

**Topics:** `python`, `data-science`, `climate-data`, `time-series`, `pandas`, `streamlit`, `anomaly-detection`, `forecasting`, `portfolio-project`, `noaa`.

### J2. Copy-paste commands

Replace `YOUR_USERNAME` with your real username; this is the only intentional placeholder in these commands. If the extracted project has no `.git` directory, initialize it:

```bash
git init -b main
git config user.name "Your Name"
git config user.email "YOUR_VERIFIED_OR_NOREPLY_EMAIL"
git status
git add .
git commit -m "feat: add reproducible climate analysis portfolio"
git remote add origin https://github.com/YOUR_USERNAME/climate-trend-analyzer.git
git push -u origin main
```

If you use the provided local repository and preserve its build history, do **not** run `git init` again. Set your own identity for future commits, then add the remote and push. The existing build commits are genuine same-session development checkpoints, not your personal day-by-day work history.

Use Git Credential Manager/browser authentication, SSH or a scoped token when prompted. Do not paste tokens in shell command strings or commit them to the repository. GitHub account passwords are not used for HTTPS Git authentication.

### J3. Inspect the hosted result

- Open README; check relative image links and the public data attribution.
- Open Actions; verify a real successful run. Local passing tests are not proof that remote CI passed.
- Add About description, topics and a legitimate live demo URL only after deployment.
- Pin the repository to your **profile**. Repositories themselves do not offer a generic “pin files” feature; put important links in the README and use Releases for a packaged version.
- Create `v1.0.0` release only when verified: `git tag -a v1.0.0 -m "Portfolio release"` then `git push origin v1.0.0`.

### J4. Screenshots and video

```bash
git add images/09_dashboard.png docs/SCREENSHOTS.md
git commit -m "docs: add real dashboard capture and proof checklist"
git push
```

Reference images using relative Markdown links. Upload a short video through a GitHub issue/README editor or release asset and link its actual resulting URL. Do not invent a hosted URL. Large videos should not be repeatedly committed to Git; keep a short optimized GIF below a few MB or link a release/video host. Capturing your own narrated demo is stronger than claiming screenshots prove authorship.

## K. README.md

The complete professional README already exists at repository root and is reproduced verbatim in `FULL_CODE.md`. It includes overview, problem, value, stack, architecture, install/run commands, dataset details, results, charts/dashboard, limitations, future work, learning outcomes and author customization instructions. It intentionally distinguishes measured local results from aspirational industry use.

Before publishing, replace author placeholders. Add a dynamic CI badge only after substituting your actual repository slug; never substitute a static “passing” badge for a real successful workflow. Inspect the rendered README after pushing.

## L. Commit strategy — eight-day genuine proof plan

| Learning day | What to implement/inspect and commit | Screenshot/video proof | Suggested commit | Notes for LinkedIn/résumé |
| --- | --- | --- | --- | --- |
| 1 | Environment, config, folder layout, README draft | Import check + tree | `chore: set up reproducible climate analysis environment` | Why CPU-only and CSV are adequate |
| 2 | Generator, real source provenance, cleaning | Raw preview, missing values, audit report | `feat(data): add synthetic climate feed and auditable cleaning` | Distinguish errors from legitimate extremes |
| 3 | EDA and descriptive features | Seasonal profile, annual summary | `feat(eda): add regional seasonal and annual exploration` | Rain totals vs temperature means |
| 4 | OLS seasonal controls, HAC uncertainty, MK | Slope table and CI chart | `feat(trends): estimate season-adjusted climate trends` | R² includes seasons; correlation caveats |
| 5 | Four detectors and planted-event evaluation | Detector register and event chart | `feat(anomalies): register and validate unusual climate months` | Explain false positives and overlapping flags |
| 6 | Baselines, Ridge, ARIMA, chronological validation | Error chart and leakage test | `feat(forecast): compare fixed-origin models without target leakage` | Validation is not independent final testing |
| 7 | Dashboard, report and exported assets | Filter interaction recording | `feat(app): add interactive climate evidence dashboard` | Decision-relevant outputs and uncertainty |
| 8 | Tests, CI, final README, career notes | Real Actions run, repository and demo | `docs: document reproducibility and portfolio evidence` | Honest limitations and next experiment |

Do not backdate commits or spread same-session generated work across invented days. Use the schedule to learn and make real improvements. A meaningful follow-up commit could add a coverage check, an independently held-out test year, or an explanation of a false-positive event.

## M. Screenshots, outputs and demo checklist

| Asset | Recommended filename | Where/how to obtain |
| --- | --- | --- |
| Dataset preview | `images/01_dataset_preview.png` | Notebook 01 or a labeled source preview |
| Missing values / preprocessing | `images/02_data_cleaning.png` | Before/after chart + audit table |
| Temperature trend | `images/03_temperature_trend.png` | Copy generated trend PNG |
| Rainfall trend | `images/04_rainfall_trend.png` | Copy annual rainfall PNG |
| Seasonal pattern | `images/05_seasonal_heatmap.png` | Copy anomaly heatmap |
| Yearly comparison | `images/06_yearly_comparison.png` | Copy annual comparison PNG |
| Anomaly detection | `images/07_anomaly_detection.png` | Copy detector-marked series |
| Forecast | `images/08_forecast.png` | Copy forecast PNG with band caveat |
| Final dashboard | `images/09_dashboard.png` | Actual browser screenshot, not a design mockup |
| Public data | `images/09d_public_co2.png` | Copy actual public-data chart |
| GitHub repo | `images/10_github_repo.png` | Capture **after your real push** |
| README preview | `images/11_readme_preview.png` | Capture actual GitHub rendering |
| Terminal | `images/12_terminal_output.png` | Your own local successful run |

The delivered `outputs/figures/` charts and dashboard screenshots are provided. GitHub/repository screenshots and your own narrated screen recording cannot honestly exist before you publish and record them; capture those yourself using the checklist.

README image example:

```markdown
![Dashboard using synthetic city data](images/09_dashboard.png)
*Four-tab dashboard, with the simulation/public-source distinction visible.*
```

Save CSV evidence: cleaning audit, trend statistics, detector register, model validation, forecast and NOAA annual means. Save logs as text as well as screenshots; text is searchable and easier to audit.

**90-second recording:** 0–15s run command and log; 15–30s explain source labels; 30–45s show season-adjusted trend and uncertainty; 45–60s show overlapping detectors; 60–75s show baseline comparison and forecast caveat; 75–90s filter dashboard and download a table. Speak in your own words. Use OBS, Xbox Game Bar, macOS screen recording or another trusted recorder. Do not disclose desktop notifications, credentials or private information.

## N. Résumé, LinkedIn and interview presentation

### N1. Three résumé bullets — edit only after personally verifying

- Built a reproducible Python climate-analytics pipeline for **2,700 synthetic monthly observations across five cities**, delivering auditable preprocessing, seasonal trend analysis and an interactive Streamlit dashboard.
- Implemented complementary statistical/ML anomaly detectors and compared calendar Ridge, ARIMA and naive baselines using **60-month chronological validation**, with explicit checks preventing future-target and exploratory-feature leakage.
- Added an independently analyzed **NOAA/Scripps public CO₂** companion with provenance/checksum tracking, generated charts and reports, executed tutorial notebooks and automated quality/statistical tests.

These bullets do not claim real-world forecast accuracy, crop-loss savings, production deployment or sole authorship of AI-assisted code. Substitute your measured result only if you can describe its evaluation protocol.

### N2. Three LinkedIn post variants

**Short project announcement**

> I built Climate Trend Analyzer, a reproducible Python portfolio project that separates seasonality, long-term trends and unusual months in synthetic multi-city climate data. It includes auditable cleaning, statistical analysis, baseline-aware forecasting and a Streamlit dashboard. A separate NOAA/Scripps CO₂ companion demonstrates real public-source handling. The biggest lesson: a good-looking model chart is not evidence of a fair forecast. [Add your real repository link.] #Python #DataScience #TimeSeries

**Technical learning post**

> In my Climate Trend Analyzer project, centered rolling means looked useful—until I checked what would be available at forecast time. I separated retrospective EDA from prediction, used future-known calendar/time features, and tested that changing withheld targets does not change validation predictions. I also learned why full-model R² with seasonal effects is not “variance explained by warming.” Code, limitations and reproducible outputs are in my repository. [Actual link.] #MachineLearning #DataAnalytics

**Business-facing post**

> Climate analytics is about decisions, not just trend lines. My student project turns a reproducible simulated climate feed into quality audits, season-adjusted slopes, anomaly investigation tables and a dashboard. It illustrates how energy, agriculture and planning teams might use such outputs, without claiming production readiness or measured business savings. Public NOAA CO₂ observations are shown separately from simulation data. Feedback on the methodology is welcome. [Actual link.] #ClimateAnalytics #Portfolio

### N3. Ten interview questions with strong sample answers

**1. Explain the project.**

I built a modular pipeline that analyzes a 45-year synthetic monthly climate record across five cities and a separate real public CO₂ record. It cleans data, controls for seasonality when estimating trends, records unusual months, compares forecast baselines and produces an interactive dashboard and report. I explicitly separate simulation results from observations.

**2. What problem does it solve?**

It turns messy longitudinal measurements into reproducible evidence. The main challenges are distinguishing seasonal change from long-term change, avoiding deletion of genuine extremes and communicating uncertainty. In production the same architecture would need quality-controlled observations, station metadata and domain validation.

**3. Why synthetic data if public data exists?**

Synthetic data lets me test the full multi-variable workflow offline and know where hot/dry episodes were planted. Public data is useful for authenticity but often has a different schema and coverage. I added NOAA CO₂ as a separate observed track instead of inventing city rainfall or temperature columns to match it.

**4. How did you clean missing and impossible values?**

I parsed explicit date formats, removed duplicate city-month keys and converted impossible values to missing. Historical descriptive analysis uses per-region time interpolation with a median fallback. For forecasting I preserve the original temperature observations, fill training data inside the training window only and exclude missing validation targets from metrics. I retain flags so repairs are auditable.

**5. Why not regress raw temperature directly on time?**

Seasonality dominates monthly temperature variation. I include calendar-month fixed effects to absorb that cycle and estimate a separate time coefficient. HAC(12) uncertainty is more appropriate than naive independent-error uncertainty for correlated monthly residuals. The reported model R² includes both trend and seasonality, so it cannot be described as warming's explanatory power alone.

**6. What does Mann–Kendall add?**

It is a nonparametric monotonic-trend check based on pairwise signs, paired with a robust Theil–Sen slope. Here it is run after deseasonalization. The current MK implementation does not correct serial correlation or multiple testing, so its p-values are exploratory; I rely on robust uncertainty and disclose that limitation rather than calling it definitive confirmation.

**7. What is an anomaly, and how do you evaluate it?**

It is unusual relative to a defined baseline, not simply a high absolute value. I use month-specific z-scores, STL residuals, IQR and Isolation Forest because they detect different kinds of unusualness. A method-level register can contain multiple flags per month. Planted episode labels let me measure recall; precision and threshold sensitivity should also be checked. No detector output is a verified disaster declaration.

**8. How did you avoid data leakage and evaluate the forecast?**

All candidates predict the entire final 60-month validation block from a fixed origin. Ridge uses only time and cyclical calendar features, not centered rolling means, the full-record anomaly baseline, future CO₂ or an ENSO proxy derived from the target. The scaler is trained only on training data; ARIMA order is selected using training AIC. A target-perturbation test verifies future targets cannot affect validation predictions. Model selection uses validation, so a separate final test or nested rolling-origin study is still needed.

**9. Why are MAE/RMSE used, and what does the interval mean?**

MAE and RMSE are interpretable in degrees Celsius, with RMSE penalizing large errors. MAPE is omitted because Celsius has an arbitrary zero and can be near zero or negative. Ridge's displayed band is an approximate residual-width band from validation RMSE, not calibrated 95% coverage, not an IPCC range and not a complete uncertainty model. ARIMA has model-based intervals, which also depend on assumptions.

**10. What would you improve first?**

I would add quality-controlled real regional observations with coverage flags, a fixed 30-year anomaly baseline, a truly independent test period and rolling-origin validation. Then I would calibrate intervals and threshold sensitivity before adding complex models. Geospatial exposure data and physical scenarios would be separate production upgrades.

### N4. Explain it to HR in 30 seconds

> I created a reproducible analysis tool that shows how a long climate record changes over time, finds unusual months and presents results in a dashboard. I used simulation to safely test the full workflow and a separate public NOAA dataset to demonstrate real data handling. My focus was clean data, honest validation and clear reporting rather than just training a model.

### N5. Explain it technically in 60–90 seconds

> The input is a monthly city panel with a unique city-date key. I separate historical cleaning and exploration from forecasting. Trends use OLS time plus monthly fixed effects with HAC covariance, alongside deseasonalized MK/Theil–Sen checks. Four detectors feed a traceable method register. Calendar Ridge, ARIMA and naive baselines share a fixed-origin chronological validation protocol. Original missing targets are preserved, and predictions do not depend on future observed covariates. The pipeline exports tables, charts and an HTML report, and the Streamlit app reads those outputs. A separate NOAA station CO₂ companion records attribution and checksum. Limitations include synthetic regional data, exploratory MK inference and uncalibrated prediction bands.

**Real-world value confidently, not exaggerated:** demonstrate how an analyst can reproduce a finding, inspect quality decisions, challenge a flagged month and export evidence. Do not claim that a monthly statistical toy forecast can warn of tomorrow's heatwave, attribute global warming or replace institutional climate modeling.

## O. Future improvements — ordered by value

| Upgrade | Student implementation path | What to verify |
| --- | --- | --- |
| Real region comparison | Add source-specific NASA POWER/NOAA/Open-Meteo archive adapter; preserve source IDs, units and time basis | Attribution, station/reanalysis differences, coverage and independent source checks |
| City forecasting | Add rolling-origin folds and one untouched test period | Each fold uses past-only preprocessing and same horizon |
| Stable anomaly normals | Fit 1991–2020 normals if data supports complete coverage | At least reference-period coverage; no future baseline leakage |
| Interval calibration | Add blocked/conformal-style residual calibration with an honest calibration window | Empirical coverage and width by horizon, not only a nominal label |
| Rainfall extremes | Model skew with gamma/quantiles; add SPI/SPEI with correct accumulation | Zero handling, reference period and calibration |
| Daily heat events | Load daily Tmin/Tmax and use a documented percentile/persistence definition | Date continuity, station changes and false-positive review |
| Pollution relationship | Join public PM2.5/AQI by location/date with meteorological controls | Source alignment; trend correlation is not causation |
| Satellite/geospatial | Learn xarray/GeoPandas, use documented grid cells and CRS | Area weights, cloud/no-data masks, projections |
| Automated reports | Schedule refresh, quality checks and report generation in a CI cron job | Failed downloads do not silently reuse unlabeled stale results |
| Climate risk score | Combine hazard, exposure and vulnerability with transparent weights | Calibration to observed losses; avoid a fabricated universal score |
| Physical scenarios | Compare CMIP6 SSP ensembles, not mere extrapolated regressions | Baseline alignment, bias adjustment, ensemble/model uncertainty |
| Sensor extension | Log a calibrated temperature/humidity sensor for a short local weather demo | Short weather records are not long climate baselines |

Hardware is **optional and not required**. An MQ-135 is not a selective, calibrated atmospheric CO₂ instrument; do not label its raw resistance or generic air-quality reading as CO₂ ppm. Use an appropriately calibrated NDIR sensor if pursuing that extension. ESP32 GPIO is 3.3V; never feed 5V analog output directly. A basic rain-detection plate does not measure calibrated rainfall totals in mm. Long-term climate inference still requires long records and proper instruments.

## P. Troubleshooting — reason, solution, prevention

| Problem | Likely reason | Solution | Prevention |
| --- | --- | --- | --- |
| `python` not found | PATH/interpreter issue | Windows `py`; Unix `python3`; install supported Python | Check `--version` before creating env |
| `ModuleNotFoundError` | Wrong environment or incomplete install | `python -m pip install -r requirements.txt` | Use the same interpreter for pip and execution |
| NumPy/SciPy wheel/compiler failure | Unsupported Python/package combination | Use Python 3.11/3.12 and fresh venv; upgrade pip | Avoid forcing old pinned NumPy on Python 3.13 |
| Package conflict | Reusing global env | New `.venv`; run `pip check` | Keep project env isolated |
| PowerShell activation blocked | Execution policy | Use `.venv\Scripts\python.exe` directly | Avoid changing machine-wide policy |
| CSV not found | Running wrong step or directory | Run from project root; first `python main.py` | Read config paths; keep archive structure |
| Permission error writing outputs | Protected directory or file open in Excel | Extract to a writable folder; close locked CSV | Avoid Program Files/system directories |
| Dates become NaT | Unsupported or ambiguous format | Explicitly add a source format to parser and test it | Do not guess day/month order |
| Time interpolation error | Missing DatetimeIndex or unsorted dates | Clean through provided module, which reindexes by date | Do not interpolate unsorted mixed station rows |
| Duplicate rows persist | Deduping entire rows rather than keys | Deduplicate `(region,date)` | Validate uniqueness at ingestion |
| Missing values remain | Whole column/region absent | Reject insufficient data or document a deliberate source adapter | Do not fabricate a measurement from another variable |
| Strange huge graph spikes | Sentinel values not cleaned | Validate physical ranges before EDA | Run raw/clean range checks |
| Plot window does not open | Headless Matplotlib uses Agg | Open saved PNG, notebook image or report | Treat saved figures as primary outputs |
| Forecast grid error | Missing months/irregular cadence | Reindex monthly and explicitly define gap handling | Validate source cadence; do not compress time |
| Very high R² but weak trend | Seasonal effects dominate model fit | Interpret slope and robust CI separately | Label full-model R² |
| MK direction wrong in custom code | Reversed pairwise sign | Use `sign(x_j-x_i)`; run increasing/decreasing tests | Keep statistical regression tests |
| MK significance too optimistic | Serial dependence/multiple tests | Treat MK as exploratory; add corrected/seasonal MK or block bootstrap | Do not advertise unimplemented pre-whitening |
| Too many anomalies | Threshold/contamination or skewed rainfall | Inspect methods separately, assess sensitivity and precision | Do not tune thresholds only for impressive counts |
| No drought z flags | Rain skew and nonnegative lower bound | Use separate rainfall-ratio proxy; investigate gamma/quantile modeling | Match detector to distribution |
| Forecast implausibly accurate | Target leakage or validation treated as test | Run perturbation tests, exclude centered/target-derived features | Forecast from fixed information available at origin |
| ARIMA fails/convergence warning | Poor order or unstable initialization | Training AIC search skips failures; keep a baseline fallback | Save failures and validate finiteness |
| Forecast dates look old | Demonstration record stops in 2024 | Read fixed-origin label; extend source before a new issue date | Separate data cutoff and execution time |
| MAPE weird/huge | Celsius near zero/negative or arbitrary origin | Use MAE/RMSE; MAPE intentionally omitted | Keep units meaningful |
| Band says 95% but misses often | Approximate residual band not calibrated | Measure empirical coverage, calibrate by horizon | Label approximate rather than guaranteed |
| NOAA download fails | No network, source change or rate limiting | Analyze bundled snapshot; retry refresh later; inspect response | Keep provenance and fail clearly, never synthesize real data |
| Dashboard empty | Pipeline not run | `python main.py --step all`, then rerun app | Include processed outputs or documented setup |
| Dashboard stale after rerun | Cached CSV reads | Clear Streamlit cache/restart server | Refresh after regenerating results |
| Port already used | Another app on 8501 | `streamlit run app/app.py --server.port 8502` | Stop old process |
| Notebook imports fail | Wrong notebook working directory | Start Jupyter from project root | Use portable root detection; Restart and Run All |
| Notebook output differs | Kernel state, package version or regeneration | Restart, Run All, inspect current tables | Do not manually hard-code result narratives |
| Git not recognized | Git not installed/PATH | Install Git and reopen terminal | Verify `git --version` |
| `remote origin already exists` | Remote already configured | `git remote -v`; use `git remote set-url origin ACTUAL_URL` | Inspect before adding |
| `src refspec main does not match` | No commit or branch name mismatch | Commit first; `git branch -M main` | Check `git status`/`git branch` |
| Push rejected | Remote has commits absent locally | Inspect and `git pull --rebase origin main`, resolve carefully | Create empty remote for existing project; do not force-push blindly |
| Authentication failed | Password/token/SSH issue | Use credential manager, browser auth or correctly scoped token | Never store credentials in repo |
| GitHub large file rejection | Video/large raw archive committed | Remove from history safely; use Releases/LFS where appropriate | Check sizes before committing |
| README image broken | Wrong path/case | Use exact repository-relative file names | Inspect rendered README after push |
| CI fails but local passes | Version/OS difference or artifact collision | Read Actions logs; unique artifact name per Python version | Test supported matrix; avoid claiming remote CI before it runs |

**Final completion rule:** run the pipeline, execute all notebooks, run tests, open the report and interact with the dashboard yourself. The evidence is the runnable code and inspectable outputs—not an impressive claim without a reproducible method.
