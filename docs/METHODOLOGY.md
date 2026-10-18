# Methodology

> The statistical thinking behind every number in this project.

---

## 1. Why the data is simulated

The project must be reproducible on any laptop, with no access to institutional
data systems and no API keys. Instead of pretending the data is real, the
project **simulates a climate system** whose statistical structure is
deliberately realistic, and then runs a genuine analysis on it.

What the simulator reproduces:

| Real climate property | How it is simulated |
| --- | --- |
| Seasonal cycle | Cosine wave, hemisphere-aware peak month (Sydney peaks in January, London in July) |
| Long-term warming trend | Region-specific linear slope of 0.020 - 0.028 °C / year |
| Interannual variability (ENSO) | Two superimposed multi-year sine waves (4.3-year and 2.1-year periods) |
| Serial correlation | AR(1) noise with ρ = 0.25 (weather is not white noise) |
| Extreme events | Heat waves (top 3 % of months) and droughts (rain < 35 % of median) |
| Global drivers | CO₂ with an accelerating curve; sea level rising ~3.2 mm / year |
| Data-quality defects | Missing values, duplicates, impossible values (`-999 °C`), mixed date formats |

**The simulation is the *input*, never the output.** Every result the project
reports is computed from the data by a real statistical method - the numbers
are not hard-coded.

---

## 2. Cleaning methodology

The cleaning stage follows the ISO 8000-style data-quality dimensions and is
fully auditable.

| Step | Action | Rationale |
| --- | --- | --- |
| 1 | Lower-case / strip column names | Consistent schema across sources |
| 2 | Parse dates with an ISO-first, US-format-fallback strategy | The raw file mixes `YYYY-MM-DD` and `MM/DD/YYYY` |
| 3 | Drop rows with unparseable dates | They cannot be placed on a time axis |
| 4 | Drop duplicate (date, region) pairs | Retried uploads |
| 5 | Coerce numerics with `errors="coerce"` | Non-numeric strings become NaN and are counted |
| 6 | Range check against physical bounds | `-999 °C` is a sensor placeholder, not a measurement |
| 7 | Impute: time interpolation → regional median | Preserves continuity; the median fallback handles the edges |
| 8 | Flag repaired rows in `data_quality_flag` | Lets a reviewer audit what was touched |

**Outcome on the shipped dataset:** 2,715 raw rows → 2,700 clean rows,
15 duplicates removed, 12 impossible values repaired, ~123 values imputed,
**100 % completeness**.

---

## 3. Feature engineering

| Feature group | Features | Why |
| --- | --- | --- |
| Calendar | `year, month, quarter, season, decade, t` | lets the model learn seasonality and measure the trend |
| Smoothing | 12-month rolling mean & std (centred) | removes short-term noise; a centred window keeps the series aligned |
| Climatology | `temp_clim, temp_std_clim, rain_normal, rain_std_clim` | the *normal* for that calendar month |
| Anomalies | `temp_anomaly, temp_anomaly_z, temp_anomaly_pct, rain_anomaly_pct, rain_anomaly_z, rain_pct_of_normal` | expresses "unusual for this place and month" |
| Persistence | `lag1, lag2, lag3, lag12` | what a forecaster may legitimately look back at |
| Events | `heatwave_month/event, drought_month/event, extreme_event` | business-defined (not statistical) extreme events |
| Drivers | `co2_ppm, enso_proxy, co2_change_rate, sea_level_change_rate` | the physical context of the series |
| Cyclical | `month_sin, month_cos` | lets tree/linear models learn a smooth annual cycle |

**Leakage control:** every lag and rolling feature uses only *past* values
(`.shift()` and backward-looking windows), and the scaler inside the
forecasting pipeline is fitted on the training fold only.

---

## 4. Trend estimation

### 4.1 The problem with a naive regression

A monthly temperature series swings ±12 °C between summer and winter. If we
regress it on time directly, the seasonal cycle contaminates the trend
estimate (R² collapses to ~0.01 and the estimate becomes unstable).

### 4.2 The fix - two independent methods

**(a) OLS with monthly fixed effects**

```
value_t  =  b0  +  b1 · t  +  Σ_k β_k · MonthDummy_k  +  ε_t
```

The month dummies absorb the seasonal cycle, so `b1` is a clean estimate of
the long-term trend. Standard errors come from the OLS covariance matrix
`σ²(XᵀX)⁻¹`, and the confidence interval uses a *t* distribution with
`n − k` degrees of freedom. Reported as °C per year and °C per decade.

**(b) Mann-Kendall test (implemented from scratch, no extra dependency)**

1. Deseasonalise: subtract the mean of each calendar month.
2. `S = Σ_{i<j} sign(x_j − x_i)` - the trend statistic.
3. `Var(S) = [n(n−1)(2n+5) − Σ_t(t−1)(2t+5)] / 18` (tie correction).
4. `z = (S−1)/√Var(S)` → two-sided p-value (normal approximation).
5. **Theil-Sen slope** = median of all pairwise slopes - a robust trend size
   that a single extreme month cannot distort.

**Why run both?** OLS assumes a linear trend and independent errors; Mann-Kendall
assumes only monotonicity. When they agree (as they do here for all 5 regions),
the finding is credible. This agreement is a *result* of the project, not a
coincidence.

### 4.3 Seasonal decomposition

`statsmodels` STL (robust, period = 12) splits the series into **trend +
seasonal + residual**. The residual is the noise floor that the anomaly
detector works against.

---

## 5. Anomaly detection

| Method | Statistic | Threshold | Catches |
| --- | --- | --- | --- |
| Climatology z-score | `(x − normal_month) / σ_month` | \|z\| ≥ 2.5 | months far from their own seasonal normal |
| STL residual | `resid / σ(resid)` | \|z\| ≥ 2.0 | deviations from trend + seasonality |
| IQR (Tukey fences) | `Q1 − 1.5·IQR`, `Q3 + 1.5·IQR` | outside fences | gross outliers |
| Isolation Forest | unsupervised, 300 trees | contamination = 2 % | unusual *combinations* of variables |

All four emit the **same schema** (`date, region, variable, method, value,
expected, deviation, score, severity, direction, description`) and are merged
into one **anomaly register** with a unique `anomaly_id`.

*Severity* is `high` when the score exceeds the threshold by one more sigma;
*direction* is `hot / cold / drought / wet / high / low`.

**Validation:** the simulator knows exactly where it injected heat waves, so
the notebook measures recall against that ground truth.

---

## 6. Forecasting

### 6.1 Protocol

1. Reserve the **last 60 months** as a hold-out window.
2. Fit every candidate on the remaining history.
3. Score them all on the same window with MAE, RMSE, MAPE and R².
4. Pick the winner per region.
5. Refit the winner on the **full** history and project 36 months.
6. For ARIMA, add a 95 % prediction interval from the model's own covariance.

### 6.2 Candidates

| Model | Rationale |
| --- | --- |
| Naive | the benchmark every serious model must beat |
| Seasonal naive | "the same month last year" - captures the annual cycle for free |
| Drift | "the historical slope continues" - the simplest trend extrapolation |
| Ridge + engineered features | the machine-learning route: lags, rolling means, cyclical month, CO₂, ENSO proxy |
| ARIMA(p,d,q) | small grid search (p ≤ 2, d ≤ 1, q ≤ 2), selected by hold-out RMSE |

### 6.3 Honest limitations

* These are **statistical extrapolations**, not physical climate-model output.
  A policy-grade projection would need CMIP6 scenarios.
* Monthly-mean temperature is a smooth target; the RMSE of ~1 °C reflects the
  irreducible monthly noise, not a modelling failure.
* The forecast assumes the historical regime continues - it does not model
  tipping points, policy changes or feedback effects.

---

## 7. Reproducibility

* `RANDOM_SEED = 42` controls the simulator, the Isolation Forest and the
  train/test splits.
* `pytest` verifies the pipeline end-to-end (20 tests).
* GitHub Actions runs the same checks on every push (Python 3.10 / 3.11 / 3.12).
* Every artefact (tables, figures, reports) is regenerated from scratch by
  `python main.py --step all` - nothing is hand-edited.
