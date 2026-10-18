# Screenshot & Proof Checklist

> The exact assets to capture, where to put them, and how to reference them in the README.
> This file is your **proof-of-work manifest** - tick the boxes as you go.

---

## 1. Where to put the files

```
images/                       <- put ALL screenshots here (README references them)
├── 01_dataset_preview.png
├── 02_data_cleaning.png
├── 03_temperature_trend.png
├── 04_rainfall_trend.png
├── 05_seasonal_heatmap.png
├── 06_yearly_comparison.png
├── 07_anomaly_detection.png
├── 08_forecast.png
├── 09_dashboard.png
├── 10_github_repo.png
├── 11_readme_preview.png
└── 12_terminal_output.png
```

The **analysis charts themselves are already generated** by the pipeline into
`outputs/figures/` - copy them into `images/` only if you want a separate "hero" set:

```bash
cp outputs/figures/02_temperature_trend.png images/03_temperature_trend.png
cp outputs/figures/09_anomaly_detection.png images/07_anomaly_detection.png
cp outputs/figures/14_forecast.png images/08_forecast.png
```

---

## 2. Capture checklist

| # | Asset | How to capture it | What must be visible |
| --- | --- | --- | --- |
| 1 | **Dataset preview** | `df.head()` in notebook 01 | Column names, first rows, `date` as text (the mixed format is visible) |
| 2 | **Data-quality profile** | `data_loader.dataset_info(raw)` | Missing counts, dtypes, duplicate count |
| 3 | **Before/after cleaning** | `outputs/figures/01_data_quality.png` | Both bar charts + correlation heatmap |
| 4 | **Cleaning report table** | `preprocessing.quality_report_table(report)` | Rows in/out, duplicates removed, values imputed, completeness |
| 5 | **Temperature trend** | `outputs/figures/02_temperature_trend.png` | 5 region lines + 12-month rolling means + the rising envelope |
| 6 | **Rainfall trend** | `outputs/figures/03_rainfall_trend.png` | Annual totals + fitted trend lines with p-values |
| 7 | **Seasonal heatmap** | `outputs/figures/04_seasonal_heatmap.png` | Month × year anomaly grid, blue→red |
| 8 | **Seasonal profile** | `outputs/figures/05_seasonal_profile.png` | Monthly temperature, monthly rainfall, per-region cycle |
| 9 | **Yearly comparison** | `outputs/figures/06_yearly_comparison.png` | Yearly bars per region + global mean line |
| 10 | **Warming-rate bar chart** | `outputs/figures/07_warming_rate_by_region.png` | °C/decade with 95 % CI error bars |
| 11 | **Decomposition** | `outputs/figures/08_seasonal_decomposition.png` | Observed / trend / seasonal / residual panels |
| 12 | **Anomaly detection** | `outputs/figures/09_anomaly_detection.png` | Red hot anomalies, blue cold anomalies on the series |
| 13 | **Anomaly table** | `outputs/tables/anomalies.csv` head in a notebook cell | `anomaly_id, date, region, method, score, severity, description` |
| 14 | **Anomaly timeline** | `outputs/figures/10_anomaly_timeline.png` | Region × year heatmap of anomaly counts |
| 15 | **Extreme events per decade** | `outputs/figures/11_extreme_events_by_decade.png` | Heat-wave + drought months per decade |
| 16 | **CO₂ vs temperature** | `outputs/figures/12_co2_vs_temperature.png` | Scatter + regression line with R² and p |
| 17 | **Forecast** | `outputs/figures/14_forecast.png` | History + dashed projection + shaded 95 % interval |
| 18 | **Model comparison** | `outputs/figures/15_model_comparison.png` | MAE/RMSE per model, best model per region |
| 19 | **Dashboard** | `streamlit run app/app.py` then screenshot | KPI row, trend chart, anomaly tab |
| 20 | **Terminal output** | `python main.py --step all` | The pipeline log + HEADLINE NUMBERS block |
| 21 | **GitHub repo** | Browser on your repo page | README rendering with images, green CI badge, commit history |
| 22 | **README preview** | Browser, top of the README | Title, badges, key-results table, screenshots |

---

## 3. Reference them in the README

```markdown
![Temperature trend by region](images/03_temperature_trend.png)
```

Add a caption in italics underneath so a recruiter knows what to look at:

```markdown
![Temperature trend by region](images/03_temperature_trend.png)
*Monthly mean temperature with a 12-month rolling mean - the rolling band rises in
every one of the five regions.*
```

---

## 4. Screen recording (60-90 seconds)

Record this script - it is the single most convincing asset for an interview:

| Time | Show | Say |
| --- | --- | --- |
| 0:00 | Terminal, `python main.py --step all` | "One command runs the whole pipeline" |
| 0:10 | The log scrolling, stage timings | "Cleaning, features, EDA, trends, anomalies, forecast" |
| 0:25 | The HEADLINE NUMBERS block | "2,700 records, 5 regions, 337 anomalies, RMSE 0.9" |
| 0:35 | Open `outputs/figures/02_temperature_trend.png` | "All five regions are warming" |
| 0:45 | Open `07_warming_rate_by_region.png` | "London fastest, with 95 % confidence intervals" |
| 0:55 | Open `09_anomaly_detection.png` | "337 anomalies, from four independent detectors" |
| 1:05 | Open `14_forecast.png` | "36-month projection with a 95 % interval" |
| 1:15 | Open the Streamlit dashboard, click a region | "And it is interactive" |

**Tooling:** Windows → `Win + Alt + R` (Xbox Game Bar) · macOS → `Cmd + Shift + 5` ·
Linux → `Ctrl + Alt + Shift + R` (GNOME) or `asciinema` for a terminal cast.

---

## 5. A 30-second GIF

If you upload a GIF to the README header, keep it small:

```bash
# macOS
ffmpeg -i demo.mov -vf "fps=10,scale=800:-1" -loop 0 demo.gif
# or with ImageMagick
convert -delay 10 -loop 0 frames/*.png demo.gif
```

Keep it under 5 MB, or GitHub will refuse it.

---

## 6. Checklist before you publish

- [ ] README renders correctly (no broken image links)
- [ ] The green **CI** badge is visible
- [ ] `outputs/figures/` contains all 17 charts
- [ ] `outputs/tables/` contains all 6 tables
- [ ] The HTML report opens in a browser
- [ ] The dashboard starts with `streamlit run app/app.py`
- [ ] `pytest -v` shows 20 passed
- [ ] The repository description, topics and social preview image are set
- [ ] The terminal screenshot and the GitHub screenshot are in `images/`
- [ ] The commit history is meaningful (not "update", "fix", "changes")
- [ ] The last commit message follows `type(scope): description`
