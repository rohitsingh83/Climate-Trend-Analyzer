# Glossary

> Every term you might be asked about in an interview, defined in one line.

---

## Climate science

**Climate normal (climatology)** - The average value of a variable for a given calendar month
(or day) over a reference period, usually 30 years. E.g. "the July normal for London is 19 °C".

**Anomaly** - The difference between an observation and its climatological normal.
*Anomalies are comparable across places and seasons; absolute values are not.*
`30 °C in London in July` is normal; `30 °C in London in January` is a +7 °C anomaly.

**Seasonal cycle** - The regular within-year variation (spring → summer → autumn → winter).
It is *not* climate change - removing it is essential before measuring a trend.

**Interannual variability** - Year-to-year fluctuation (e.g. El Niño / La Niña), typically
2-5 year periods. Adds noise to a trend estimate and is the reason we need many decades.

**El Niño Southern Oscillation (ENSO)** - A periodic warming/cooling of the tropical Pacific
that shifts rainfall and temperature patterns worldwide. In this project it is proxied by a
smoothed global mean temperature anomaly.

**Heat wave** - A sustained period of unusually hot days. Here: **3 or more consecutive months**
with a temperature anomaly above +1.5 σ.

**Drought** - A prolonged dry period. Here: rainfall below **40 % of the calendar-month normal**.

**Radiative forcing** - The change in Earth's energy balance (W/m²) caused by e.g. CO₂.
The *physical* driver behind the warming trend we measure statistically.

**Climate projection vs. forecast** - A *projection* is a conditional scenario from a physical
model (CMIP6); a *forecast* is a statistical extrapolation of the observed record.
This project produces **projections of the statistical kind** and says so explicitly.

**Variability vs. trend** - Variability is the noise around the trend; the trend is the
direction the noise is drifting in. Confusing the two is the most common analytical error.

---

## Data science & statistics

**Long format (tidy data)** - One row per observation, one column per variable.
`region | date | temp_mean_c | rainfall_mm` is tidy; a wide matrix is not.

**Missing value (NaN)** - A gap in the record. In climate data it usually means a sensor
dropout or a failed request, not a zero.

**Imputation** - Filling a missing value with an estimate (here: linear interpolation in time,
falling back to the regional median).

**Outlier** - A value far from the bulk of the data. Careful: an outlier may be an *error*
(`-999 °C`) **or a real extreme event** (a heat wave). The project treats impossible values as
errors and genuine extremes as anomalies - two different things.

**Rolling window / moving average** - The mean of the last *k* observations. A 12-month rolling
mean on monthly data smooths the seasonal cycle and reveals the underlying trend.

**Centred rolling window** - A window that looks equally forward and backward. Used for
*analysis* (not for forecasting - that would be leakage).

**Climatological z-score** - `(value − normal) / σ_normal`. The unit-free way to say "how
unusual is this month for this place".

**STL decomposition** - Seasonal-Trend decomposition using LOESS; it separates seasonal, trend and residual
components. The residual is the "noise + extremes" layer.

**OLS (Ordinary Least Squares)** - Linear regression that minimises the sum of squared
residuals. With monthly fixed effects it estimates the long-term trend of a seasonal series.

**Fixed effects (month dummies)** - Extra regressors (one per calendar month) that absorb the
seasonal cycle so the time coefficient estimates only the trend.

**R²** - The share of variance explained by the model. 0 = no better than the mean, 1 = perfect.
Note that R² on a *seasonal* series is naturally small; the fixed-effects model raises it to
0.91-0.98 here.

**p-value** - The probability of seeing data this extreme if the null hypothesis (no trend)
were true. `p < 0.05` = "significant at the 5 % level". *A p-value is not the probability that
the trend is real.*

**Confidence interval (CI)** - The plausible range for the true slope. A confidence interval communicates slope uncertainty; compare the bounds and units in the actual trend table.

**Mann-Kendall test** - A non-parametric trend test that only assumes the trend is monotonic.
Robust to outliers and to non-normal errors; the standard tool in climate-trend work.

**Theil-Sen slope** - The median of all pairwise slopes. A robust alternative to the OLS slope
that a single extreme month cannot distort.

**Mann-Kendall S statistic** - The sum of the signs of all pairwise differences. Its sign
gives the direction of the trend, its distance from 0 gives the strength.

**Deseasonalisation** - Removing the seasonal cycle (here: subtracting each calendar month's
mean) before a trend test. Skipping this step is the classic pitfall of climate analysis.

**Leakage** - Accidentally letting the model see information from the future (e.g. a centred
rolling mean used as a *predictor*, or fitting a scaler on the full dataset before splitting).

**Back-testing / hold-out** - Evaluating a model on a period it never saw. This is the only
honest way to compare models.

**MAE / RMSE / R²** - Forecast error metrics. MAE = average absolute error,
RMSE = penalises large errors more, R² = variance explained.

**ARIMA(p,d,q)** - AutoRegressive Integrated Moving Average: *p* auto-regressive lags, *d*
differencing order, *q* moving-average lags. `d=1` removes a linear trend.

**Seasonal naive forecast** - "The value of the same month last year." A shockingly strong
baseline that any real model must beat.

**Ridge regression** - Linear regression with an L2 penalty on the coefficients. Shrinks
unstable coefficients; with lagged features it is a solid time-series regressor.

**Isolation Forest** - An unsupervised algorithm that isolates points that are easy to separate
from the rest. Points isolated quickly are the anomalies.

**Contamination (parameter)** - The *expected fraction* of anomalies in the data. Setting it is
a modelling decision, not a fact.

---

## Software engineering

**Data contract** - The agreed schema between two modules. Here: "one row per (region, month)"
with a fixed column list - which is why a real dataset can replace the simulated one.

**Separation of concerns** - One job per module. `preprocessing.py` does not draw charts;
`visualizations.py` does not compute statistics.

**DRY** - Don't Repeat Yourself. Every threshold lives in `config.py`; every chart function in
`visualizations.py`.

**Idempotent pipeline** - Running it twice produces the same result (thanks to the seed).
This is what makes it trustworthy.

**CI (Continuous Integration)** - Automated checks on every push. Here: import check → tests →
full pipeline run.

**Seaborn `heatmap`** - A 2-D matrix rendered as a colour grid - the standard way to show
month × year climate patterns.

---

## Business & domain

**Climate risk / climate exposure** - How much a business, asset or portfolio is affected by
climate hazards. Trend severity × anomaly frequency × asset exposure.

**TCFD / ISSB** - Disclosure frameworks requiring companies to report climate-related risks
and metrics - the main reason corporates are hiring climate data roles.

**Parametric insurance** - Insurance that pays out automatically when an index (e.g. rainfall
or temperature) crosses a threshold. Needs exactly the kind of anomaly statistics this project
produces.

**Peak demand** - The maximum electricity load of a period. Shifting by ~0.3 °C/decade changes
cooling demand and therefore the capacity a utility must build.

**Crop-loss risk** - The probability that weather during the growing season destroys yield.
Drought months identified here are the early-warning signal.
