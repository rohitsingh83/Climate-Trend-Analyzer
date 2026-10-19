"""
Script to extract pipeline outputs and generate docs/index.html for GitHub Pages.
"""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

def build_data():
    tables_dir = ROOT / "outputs" / "tables"
    proc_dir = ROOT / "data" / "processed"
    
    # Load tables
    trends = pd.read_csv(tables_dir / "trend_summary.csv").to_dict(orient="records")
    metrics = pd.read_csv(tables_dir / "model_metrics.csv").to_dict(orient="records")
    forecasts = pd.read_csv(tables_dir / "forecast_next_36m.csv").to_dict(orient="records")
    noaa_co2 = pd.read_csv(tables_dir / "noaa_co2_annual.csv").to_dict(orient="records")
    anomalies = pd.read_csv(tables_dir / "anomalies.csv").to_dict(orient="records")
    yearly = pd.read_csv(tables_dir / "yearly_summary.csv").to_dict(orient="records")
    
    # Load cleaning audit
    audit_file = ROOT / "outputs" / "cleaning_audit.json"
    audit = json.loads(audit_file.read_text()) if audit_file.exists() else {}
    
    # Load monthly data sample for smooth trends (downsampled or complete monthly for all 5 cities)
    clean_csv = proc_dir / "climate_clean.csv"
    monthly_data = {}
    if clean_csv.exists():
        df_clean = pd.read_csv(clean_csv)
        for region in df_clean["region"].unique():
            rdf = df_clean[df_clean["region"] == region].sort_values("date")
            monthly_data[region] = {
                "dates": rdf["date"].tolist(),
                "temp_mean": rdf["temp_mean_c"].round(2).tolist(),
                "rainfall": rdf["rainfall_mm"].round(1).tolist(),
                "humidity": rdf["humidity_pct"].round(1).tolist(),
                "co2": rdf["co2_ppm"].round(1).tolist(),
                "sea_level": rdf["sea_level_mm"].round(1).tolist()
            }
            
    payload = {
        "trends": trends,
        "metrics": metrics,
        "forecasts": forecasts,
        "noaa_co2": noaa_co2,
        "anomalies": anomalies,
        "yearly": yearly,
        "audit": audit,
        "monthly": monthly_data,
        "regions": ["Hyderabad", "London", "New York", "Singapore", "Sydney"]
    }
    return payload

if __name__ == "__main__":
    data = build_data()
    out = ROOT / "docs" / "data.json"
    out.write_text(json.dumps(data, indent=2))
    print(f"Data bundle written: {out} ({len(json.dumps(data))/1024:.1f} KB)")
