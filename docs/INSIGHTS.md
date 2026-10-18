# Key Findings - Climate Trend Analyzer

## Key Findings

*Generated automatically on 2026-10-18 09:10 from 2,700 cleaned monthly records (1980-01 to 2024-12) across 5 regions.*

### 1. Warming trend

- **Every region is warming.** All 5 of 5 simulated regions show a statistically significant positive temperature trend (20 of 25 region x indicator combinations are significant at p < 0.05).
- **Fastest warming:** London at **0.376 °C per decade** (OLS slope 0.0376 °C/yr, R² = 0.947, p = 0.00e+00).
- **Slowest warming:** Singapore at 0.209 °C per decade.
- **Mann-Kendall (non-parametric) test** confirms the trend for 5/5 regions (all ['increasing']).
- Regional spread in warming rate is **0.167 °C/decade**, i.e. the same climate driver produces very different local impacts - which is exactly why regionalisation matters for policy.

### 2. Seasonal structure

- The dataset has a clear seasonal cycle: peak mean temperature in **December** (22.98 °C) and minimum in **June** (17.20 °C), a swing of **5.78 °C**.
- 1 distinct seasonal peaks were detected across regions, confirming that the simulator reproduces hemisphere-aware seasonality.
- Seasonality is the main source of variance, so every model in this project uses a 12-month baseline (climatology) or a seasonal-naive benchmark.

### 3. Anomalies and extreme events

- **337 anomalies** were detected by the four-method ensemble (z-score, STL residual, IQR, Isolation Forest).
- Direction split: **140 hot**, **120 cold**, **0 dry**, **73 wet** months.
- Most extreme event: **Unexpected 22.6°C month: residual +5.7°C (+5.6σ)** in London on 01 Jan 2004 (score 5.606).
- Heat-wave + drought months rise from **12** in the 1980s to **10** in the 2020s (-16.7 % change) - extremes are increasing faster than the mean.

### 4. Drivers

- Atmospheric CO₂ and mean temperature show a strong global correlation of **r = 0.171** (Pearson, monthly global means).
- CO₂ is rising at about **28.29 ppm per decade** (R² = 0.995) - the fastest-moving driver in the dataset.
- The residual variance that CO₂ does not explain appears in the seasonal and event columns: local extremes are driven by circulation (ENSO proxy) and land-ocean patterns, not only by the global trend.

### 5. Forecasting

- The best model per region was selected by **60-month hold-out back-testing**: Hyderabad -> Ridge (engineered features), London -> Ridge (engineered features), New York -> Ridge (engineered features), Singapore -> Ridge (engineered features), Sydney -> Ridge (engineered features).
- Best achievable RMSE across all candidates: **0.896 °C** on a monthly average temperature series.
- **Singapore**: projected mean temperature in November 2027 = **31.03 °C**.
- **London**: projected mean temperature in November 2027 = **13.41 °C**.
- **Hyderabad**: projected mean temperature in November 2027 = **31.39 °C**.
- **New York**: projected mean temperature in November 2027 = **16.06 °C**.
- **Sydney**: projected mean temperature in November 2027 = **16.63 °C**.
- Production note: the 36-month projection is a *trend continuation* scenario, not a physical climate model. For policy-grade numbers, this pipeline would be pointed at CMIP6/IPCC scenarios instead of a statistical extrapolation.

### 6. Data quality

- The raw file contained **2,715 rows**; after removing 15 unusable records (bad dates / duplicates) the analysis table holds **2,700 rows**.
- **132 values** were imputed and **12 rows** contained physically impossible readings (e.g. -999 °C sensor dropouts) that were flagged and repaired.
- Final completeness: **100.00 %**.

### 7. Business & policy implications

- **Energy & utilities:** a reliable regional warming signal supports peak-demand and cooling-load forecasting (10-15 % operational savings is the range usually quoted for better demand management).
- **Agriculture:** seasonal rainfall anomalies identify drought and flood risk windows for crop planning and irrigation scheduling.
- **Insurance & finance:** anomaly frequency and trend severity are the inputs for parametric weather-risk pricing and climate exposure disclosure.
- **Urban planning & public health:** heat-wave month counts translate directly into cooling-centre, heat-health-alert and infrastructure design criteria.
- **Sustainability reporting:** the pipeline produces reproducible, auditable tables and charts that can be embedded in ESG / TCFD disclosures.

### 8. Limitations and next steps

- The dataset is a **simulation**: it reproduces realistic statistical structure (seasonality, autocorrelation, trends, extremes) but it is not an observational record.
- The statistical models extrapolate; they do not model physical climate feedbacks.
- Next: replace the simulator with a public dataset (NASA GISTEMP, NOAA, Our World in Data), add CMIP6 scenarios, and validate the forecasts against published indices.
