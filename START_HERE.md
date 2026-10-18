# Start here — Climate Trend Analyzer

## What you received

A working Python project with modular code, synthetic multi-city data, a separate real NOAA/Scripps CO₂ snapshot, executed tutorial notebooks, tests, charts, reports and a Streamlit dashboard.

**Main learning guide:** [docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md) — all requested sections A–P, including installation, simulation, GitHub, résumé/LinkedIn/interview kit and troubleshooting.

**Complete source listing:** [docs/FULL_CODE.md](docs/FULL_CODE.md) — full code by file, plus explanations and the README. The actual source files are already runnable; no manual copying is needed.

**Recruiter landing page:** [README.md](README.md).

## Fastest local run

Use Python 3.11 or 3.12 if possible. Extract the ZIP and enter the project folder.

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --step all
python -m pytest -q
python -m streamlit run app/app.py
```

Open `outputs/reports/climate_trend_report.html` for the standalone report. Regular runs use cached public data; initial package installation needs internet.

## Learn in this order

1. Read sections A–F of the guide.
2. Run notebook 01 and inspect raw/clean data.
3. Run notebooks 02–04 for EDA, season-adjusted trends and anomalies.
4. Run notebook 05 and explain why validation is chronological and centered EDA features are not predictors.
5. Interact with the dashboard and inspect the public-data companion.
6. Read guide J–N; personalize author details, publish a real repository and record your own demo.

## Important boundaries

- Synthetic city results are **not real observed climate findings**.
- Public NOAA CO₂ is analyzed separately; no synthetic cities are disguised as measurements.
- The forecast origin is December 2024; projected dates are 2025–2027 regardless of today's execution date.
- The final 60 months are a **model-selection validation block**, not an untouched final test.
- Prediction bands are approximate/uncalibrated, not official climate scenario intervals.
- Local Git checkpoints are real same-session build commits, not an eight-day history. Do not backdate commits or imply you authored work you cannot explain.
- Actual GitHub publication and your own narrated recording require your account and participation. No remote repository or deployed permanent public demo is claimed.
