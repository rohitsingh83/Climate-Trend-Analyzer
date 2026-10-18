# Résumé, LinkedIn and interview kit

The full editable kit is in [PROJECT_GUIDE.md, section N](PROJECT_GUIDE.md#n-résumé-linkedin-and-interview-presentation): three résumé bullets, three LinkedIn posts, ten questions with detailed answers, HR/technical pitches and an honest business-value explanation.

## Three concise résumé bullets

- Built a reproducible Python climate-analytics pipeline for **2,700 synthetic monthly observations across five cities**, with auditable preprocessing, seasonal trend analysis and a Streamlit dashboard.
- Compared calendar Ridge, ARIMA and naive baselines using **60-month chronological validation**, with tests that exclude future-target and exploratory-feature leakage; implemented four complementary anomaly detectors.
- Integrated a separate **NOAA/Scripps public CO₂** companion with source/checksum tracking and generated charts, reports, executed notebooks and automated statistical/data-quality tests.

Use only after personally running and understanding the work. Disclose AI assistance appropriately; do not imply sole authorship, real regional measurements, production deployment or financial savings.

## 30-second explanation

> I built a reproducible analysis tool that shows how a long climate record changes, finds unusual months and presents results in a dashboard. Simulation lets me test the full multi-variable workflow, while a separate public NOAA dataset demonstrates real source handling. The most important engineering choices were auditable cleaning, seasonal controls, past-only forecasting and clear uncertainty labels.

## Interview checklist

Be ready to explain: concentration vs emissions; seasonal controls; full-model vs trend-only R²; HAC uncertainty; serial-dependence caveats in MK; method records vs unique events; planted-event recall; fixed-origin validation vs final testing; why Celsius MAPE is omitted; and why an approximate band is not a guaranteed physical projection.
