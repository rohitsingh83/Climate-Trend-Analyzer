# Key Findings - Climate Trend Analyzer

## Key Findings

*Generated automatically on 2026-10-18 09:34 from 2,700 cleaned monthly records (1980-01 to 2024-12) across 5 regions.*

### 1. Warming trend

- **Synthetic warming signal.** 5 of 5 simulated regions show a statistically significant positive temperature trend (19 of 25 region x indicator combinations are significant at p < 0.05).
- **Fastest synthetic warming:** London at **0.398 °C per decade** (OLS slope 0.0398 °C/yr, full model R² (including seasonal effects) = 0.932, p = 3.00e-06).
- **Slowest warming:** Singapore at 0.228 °C per decade.
- **Mann-Kendall (non-parametric) test** confirms the trend for 5/5 regions (all ['increasing']).
- Regional spread in warming rate is **0.169 °C/decade**, i.e. the same climate driver produces very different local impacts - which is exactly why regionalisation matters for policy.

### 2. Seasonal structure

- **Every region has its own seasonal peak:** Hyderabad (April), London (July), New York (July), Singapore (March), Sydney (January). The ~6-month phase shift between the northern and southern hemispheres (London peaks in July, Sydney in January) is exactly what a climate-aware model has to capture.
- The seasonal swing differs sharply by climate: **New York** swings 23.5 °C between its warmest and coolest month, while **Singapore** swings only 3.4 °C - a 6x difference in seasonal amplitude.
- 4 distinct peak months appear across the 5 regions, confirming the simulator reproduces hemisphere-aware seasonality.
- Seasonality is the main source of variance, so every model in this project uses a 12-month baseline (climatology) or a seasonal-naive benchmark, and every trend statistic is computed on a **deseasonalised** series.

### 3. Anomalies and extreme events

- **362 detector records** were detected by the four-method ensemble (z-score, STL residual, IQR, Isolation Forest).
- Detector-record direction split (methods can flag the same month): **177 hot**, **91 cold**, **0 dry**, **75 wet** months.
- Most extreme event: **Unexpected 36.9°C month: residual +7.2°C (+6.1σ)** in Singapore on 01 Jan 2020 (score 6.076).
- Heat-wave + drought months occur at **0.1 per year** in the 1980s and **1.2 per year** in the 2020s - a rising rate (728.6 % more). (The 2020s are a partial decade, so the rate is used instead of the raw count.)
- The mean warming rate is 0.298 °C/decade; extremes and the mean therefore move **in the same direction**, but these planted simulation episodes are not evidence that real-world extreme frequency increased.

### 4. Drivers

- Atmospheric CO₂ and mean temperature have a monthly, unweighted five-city correlation of **r = 0.178** (Pearson, monthly unweighted five-city means).
- CO₂ is rising at about **28.29 ppm per decade** (R² = 0.995) (concentration, not emissions).
- Shared time trends can create spurious correlation; these simulated associations do not establish causal attribution. This five-city mean is NOT a global climate index.

### 5. Forecasting

- The best model per region was selected by **60-month chronological validation**: Hyderabad -> Ridge (calendar + trend), London -> Ridge (calendar + trend), New York -> Ridge (calendar + trend), Singapore -> Ridge (calendar + trend), Sydney -> Ridge (calendar + trend).
- Lowest validation RMSE among candidates: **1.315 °C** on a monthly average temperature series.
- **Singapore**: projected mean temperature in December 2027 = **29.04 °C**.
- **London**: projected mean temperature in December 2027 = **6.50 °C**.
- **Hyderabad**: projected mean temperature in December 2027 = **26.03 °C**.
- **New York**: projected mean temperature in December 2027 = **4.24 °C**.
- **Sydney**: projected mean temperature in December 2027 = **24.91 °C**.
- Production note: the 36-month projection is a *trend continuation* scenario, not a physical climate model. For policy-grade numbers, this pipeline would be pointed at CMIP6/IPCC scenarios instead of a statistical extrapolation.

### 6. Data quality

- The raw file contained **2,715 rows**; after removing 15 unusable records (bad dates / duplicates) the analysis table holds **2,700 rows**.
- **132 values** were imputed and **12 rows** contained physically impossible readings (e.g. -999 °C sensor dropouts) that were flagged and repaired.
- Final completeness: **100.00 %**.

### 7. Business & policy implications

- **Energy & utilities:** a reliable regional warming signal supports peak-demand and cooling-load planning; no cost savings are measured by this project.
- **Agriculture:** seasonal rainfall anomalies identify drought and flood risk windows for crop planning and irrigation scheduling.
- **Insurance & finance:** anomaly frequency and trend severity are the inputs for parametric weather-risk pricing and climate exposure disclosure.
- **Urban planning & public health:** heat-wave month counts translate directly into cooling-centre, heat-health-alert and infrastructure design criteria.
- **Sustainability reporting:** the pipeline produces reproducible, auditable tables and charts that can be embedded in ESG / TCFD disclosures.

### 8. Limitations and next steps

- The dataset is a **simulation**: it reproduces realistic statistical structure (seasonality, autocorrelation, trends, extremes) but it is not an observational record.
- The statistical models extrapolate; they do not model physical climate feedbacks.
- Next: replace the simulator with a public dataset (NASA GISTEMP, NOAA, Our World in Data), add CMIP6 scenarios, and validate the forecasts against published indices.
