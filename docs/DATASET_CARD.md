# Dataset Card

> Documentation of the dataset used by the Climate Trend Analyzer, following the
> structure of the "Datasheets for Datasets" convention.

---

## 1. Name & version

| Field | Value |
| --- | --- |
| **Name** | Climate Trend Analyzer - Simulated Monthly Climate Record |
| **Version** | 1.0.0 |
| **Generator** | `src/data_generator.py` (`generate_climate_dataset(seed=42)`) |
| **File** | `data/raw/climate_raw.csv` |
| **License** | MIT (same as the repository) |
| **Generated** | Deterministically - the same seed always produces the same file |

---

## 2. Description

A **monthly, multi-region, multi-variable climate record** covering five
cities on four continents from **January 1980 to December 2024** (540 months
per region, 2,700 base records).

The dataset is a *simulation* built to give the project a realistic
train/analysis surface without access to institutional systems. It reproduces
the statistical structure that a real climate dataset has: seasonality,
autocorrelation, long-term trends, interannual variability, extreme events and
realistic data-quality defects.

---

## 3. Files & schema

| File | Rows | Description |
| --- | --- | --- |
| `data/raw/climate_raw.csv` | 2,715 | The "as collected" file - **deliberately imperfect** (2,715 = 2,700 + 15 duplicate rows) |
| `data/processed/climate_clean.csv` | 2,700 | The analysis-ready master table |
| `data/processed/climate_featured.csv` | 2,700 | Master table + 39 engineered features |

### Column dictionary

| Column | Type | Unit | Range (simulated) | Description |
| --- | --- | --- | --- | --- |
| `date` | datetime | - | 1980-01 … 2024-12 | Month start. **Mixed format in the raw file** (`YYYY-MM-DD` and `MM/DD/YYYY`). |
| `region` | str | - | 5 values | City / station name |
| `country` | str | - | - | Country |
| `latitude` | float | ° | -33.9 … 51.5 | Used for a small latitude effect on CO₂ |
| `longitude` | float | ° | -151.2 … 151.2 | Kept for future geospatial work |
| `temp_mean_c` | float | °C | ~0 … 35 | **Monthly mean air temperature** (with `-999`/`900` outliers injected) |
| `temp_min_c` | float | °C | -5 … 28 | Monthly mean of daily minima |
| `temp_max_c` | float | °C | 5 … 42 | Monthly mean of daily maxima |
| `rainfall_mm` | float | mm | 0 … 600 | Monthly precipitation total (gamma-distributed) |
| `humidity_pct` | float | % | 30 … 95 | Mean relative humidity (inverse relation to temperature) |
| `co2_ppm` | float | ppm | 338 … 430 | Atmospheric CO₂ - a **global** driver with a small regional offset |
| `sea_level_mm` | float | mm | 0 … 160 | Sea level relative to the 1980 baseline (**global** driver) |
| `sim_heatwave` | int | - | 0/1 | **Ground truth**: month is in the top 3 % of temperature |
| `sim_drought` | int | - | 0/1 | **Ground truth**: rainfall below 35 % of the median |
| `year`, `month` | int | - | - | Added by the cleaning stage |
| `data_quality_flag` | str | - | original / repaired | Added by the cleaning stage - audit trail |

---

## 4. Known defects (by design)

| Defect | Count | How it is fixed |
| --- | --- | --- |
| Missing values (1.5 % of 3 climate columns) | ~123 | time interpolation → regional median |
| Duplicate rows | 15 | dropped on (date, region) |
| Impossible values (`-999 °C`, `900 °C`) | 12 | range check → treated as missing → imputed |
| Mixed date formats | 10 % of rows | ISO-first parse with US-format fallback |
| Out-of-order rows | present | sorted by (region, date) |

---

## 5. Regions

| Region | Country | Lat | Climate character |
| --- | --- | --- | --- |
| Hyderabad | India | 17.4 | Tropical monsoon - mild seasonality, heavy summer rain |
| London | United Kingdom | 51.5 | Temperate maritime - strong summer/winter swing |
| New York | USA | 40.7 | Humid continental - the largest seasonal swing |
| Singapore | Singapore | 1.35 | Tropical equatorial - almost no seasonality, high rainfall |
| Sydney | Australia | -33.9 | Southern-hemisphere temperate - **seasonality reversed** |

---

## 6. Collection process (simulated)

```
for each region:
    for each month in 1980-01 … 2024-12:
        seasonal   = -amplitude · cos(2π (month − peak_month) / 12)
        trend      = slope_per_year · (year − 1980)
        enso       = 0.85·sin(2πt/51.6) + 0.35·sin(2πt/25.2)
        noise      = 0.9·AR1(ρ=0.25) + 0.6·N(0,1)
        temp_mean  = base + seasonal + trend + enso + noise
        rainfall   ~ Gamma(shape=1.4, scale = base_rain · wet_factor / 1.4)
        humidity   = base_humidity − 1.15·(temp_mean − base_temp) + N(0,3)
        co2        = 338 + 2.10·Δyear + 0.0165·Δyear² + latitude effect
        sea_level  = 1.6·Δyear + 0.035·Δyear² + N(0,1.2)
then inject: missing values, duplicates, impossible values, mixed date formats
```

---

## 7. Intended use

* Teaching and portfolio demonstration of climate time-series analysis
* Regression testing of trend, anomaly and forecasting pipelines
* A drop-in replacement for a real dataset with the same schema

## 8. Out-of-scope use

* **Not** suitable for any scientific claim about real climate
* **Not** suitable for policy, insurance or investment decisions
* **Not** a substitute for NASA GISTEMP, NOAA, HadCRUT or CMIP6 data

---

## 9. How to use a real dataset instead

1. Download a public dataset (e.g. NASA GISTEMP `GLB.Ts+dSST.csv` or
   `owid-co2-data.csv` from Our World in Data).
2. Reshape it to the schema above (one row per region-month).
3. Drop the file into `data/raw/climate_raw.csv`.
4. Run `python main.py --step all`.

**No downstream code changes are required** - the loader, cleaning, feature,
trend, anomaly and forecast modules all work on the same contract.
