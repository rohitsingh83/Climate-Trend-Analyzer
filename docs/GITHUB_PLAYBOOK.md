# GitHub publishing playbook

The complete copy-paste guide is in [PROJECT_GUIDE.md, sections J–M](PROJECT_GUIDE.md#j-github-upload-steps).

## Before pushing

- Personalize name, contact and profile links; remove unneeded placeholders.
- Run `python main.py`, `python -m pytest -v` and all five notebooks.
- Inspect the report and dashboard yourself.
- Keep synthetic/public data labels and source attribution visible.
- Do not claim that a generated commit history proves eight days of work.
- Never commit tokens, passwords, `.venv` or package caches.

## Create an empty public remote

Suggested name: **climate-trend-analyzer**.

Description: `Reproducible climate analytics portfolio: synthetic multi-city trends, anomaly detection, leakage-safe forecasting, NOAA CO2 companion and Streamlit dashboard.`

Topics: `python`, `data-science`, `climate-data`, `time-series`, `pandas`, `streamlit`, `anomaly-detection`, `forecasting`, `portfolio-project`, `noaa`.

```bash
# If extracted ZIP has no .git directory:
git init -b main
git config user.name "Your Name"
git config user.email "YOUR_VERIFIED_OR_NOREPLY_EMAIL"
git add .
git commit -m "feat: publish reproducible climate portfolio"
# Replace the username in this URL:
git remote add origin https://github.com/YOUR_USERNAME/climate-trend-analyzer.git
git push -u origin main
```

If a local repository already exists, keep its genuine same-session build checkpoints, set your identity for future commits and add the remote without reinitializing. Authenticate using a credential manager/browser, SSH or a scoped token; never embed secrets in commands.

After pushing, inspect **Actions** and real workflow logs before adding a passing CI claim. Pin the repository to your profile, set topics, create a release and link an actual demo if you deploy one. Add genuine repository/README screenshots only after the remote exists.

## Eight-day proof plan

1. Environment/config → import check → `chore: set up environment`.
2. Data/provenance/cleaning → quality audit → `feat(data): add auditable ingestion`.
3. EDA/features → seasonal and annual charts → `feat(eda): add exploration`.
4. Trends → HAC CI chart → `feat(trends): adjust for seasonality`.
5. Detectors → register/recall → `feat(anomalies): evaluate planted episodes`.
6. Forecasts → baseline errors/leakage tests → `feat(forecast): add fair temporal validation`.
7. Dashboard/report → real interaction recording → `feat(app): add evidence dashboard`.
8. Documentation/tests/CI → actual Actions screenshot → `docs: complete reproducibility guide`.

This is a **learning schedule**, not a claim that the delivered code was developed on those dates. Make genuine improvements, keep notes on mistakes, and be prepared to explain limitations.
