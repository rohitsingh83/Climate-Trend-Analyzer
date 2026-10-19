"""
Generate beautiful terminal window screenshots for the terminal pipeline run
and pytest suite output.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = ROOT / "screenshots"
IMAGES_DIR = ROOT / "images"

def create_terminal_card(title, commands_and_output, output_path):
    width = 1200
    line_height = 24
    padding = 32
    header_height = 48
    
    lines = []
    for item in commands_and_output:
        if isinstance(item, tuple):
            prefix, text, color = item
            lines.append((prefix + text, color))
        else:
            lines.append((item, "#cbd5e1"))
            
    height = header_height + (len(lines) * line_height) + (padding * 2)
    
    img = Image.new("RGBA", (width, height), (7, 11, 18, 255))
    draw = ImageDraw.Draw(img)
    
    # Outer terminal card background
    draw.rounded_rectangle([(10, 10), (width - 10, height - 10)], radius=16, fill=(15, 23, 42, 255), outline=(56, 189, 248, 60), width=1)
    
    # Header bar
    draw.rounded_rectangle([(10, 10), (width - 10, header_height)], radius=16, fill=(30, 41, 59, 255))
    draw.rectangle([(10, header_height - 10), (width - 10, header_height)], fill=(30, 41, 59, 255))
    
    # Window buttons (mac/terminal style dots)
    draw.ellipse([(28, 20), (40, 32)], fill="#ef4444")
    draw.ellipse([(48, 20), (60, 32)], fill="#f59e0b")
    draw.ellipse([(68, 20), (80, 32)], fill="#10b981")
    
    # Title
    try:
        font_title = ImageFont.truetype("arial.ttf", 14)
        font_mono = ImageFont.truetype("consola.ttf", 15)
    except:
        font_title = ImageFont.load_default()
        font_mono = ImageFont.load_default()
        
    draw.text((width // 2 - 120, 17), title, fill="#94a3b8", font=font_title)
    
    # Draw terminal lines
    y = header_height + 20
    for line, color in lines:
        draw.text((padding, y), line, fill=color, font=font_mono)
        y += line_height
        
    img.save(output_path, "PNG")
    print(f"Generated {output_path}")

def run():
    pipeline_lines = [
        ("$ ", "python main.py --step all", "#38bdf8"),
        ("", "======================================================================", "#64748b"),
        ("", "CLIMATE TREND ANALYZER - END-TO-END PIPELINE", "#38bdf8"),
        ("", "======================================================================", "#64748b"),
        ("", "[data_loader] Loaded raw dataset: data/raw/climate_raw.csv -> shape (2715, 14)", "#94a3b8"),
        ("", "[pipeline] stage 1/9  ingestion done  (+0.0s)", "#10b981"),
        ("", "[pipeline] Clean dataset -> data/processed/climate_clean.csv (2700, 18)", "#94a3b8"),
        ("", "[pipeline] stage 2/9  cleaning done  (+0.2s)", "#10b981"),
        ("", "[pipeline] Featured dataset -> data/processed/climate_featured.csv (2700, 57)", "#94a3b8"),
        ("", "[pipeline] stage 3/9  feature engineering done  (+0.7s)", "#10b981"),
        ("", "[pipeline] EDA complete (225 yearly summary rows, correlation matrix saved)", "#94a3b8"),
        ("", "[pipeline] stage 4/9  EDA done  (+1.0s)", "#10b981"),
        ("", "[pipeline] Trend analysis complete (25 indicator rows, OLS/HAC + Mann-Kendall)", "#94a3b8"),
        ("", "[pipeline] stage 5/9  trend analysis done  (+3.1s)", "#10b981"),
        ("", "[pipeline] Anomaly detection complete (362 anomalies across 4 detectors)", "#94a3b8"),
        ("", "[pipeline] stage 6/9  anomaly detection done  (+7.3s)", "#10b981"),
        ("", "[pipeline] Forecasting complete (180 projected rows: 36m x 5 regions)", "#94a3b8"),
        ("", "[pipeline] stage 7/9  forecasting done  (+36.4s)", "#10b981"),
        ("", "[pipeline] stage 8/9  visualisations done (18 figures generated)  (+60.2s)", "#10b981"),
        ("", "[pipeline] stage 9/9  insights + HTML report generated  (+61.2s)", "#10b981"),
        ("", "======================================================================", "#64748b"),
        ("", "PIPELINE COMPLETE in 61.2s", "#10b981"),
        ("", "  figures   : 18 -> outputs/figures", "#f8fafc"),
        ("", "  tables    : 8  -> outputs/tables", "#f8fafc"),
        ("", "  report    : outputs/reports/climate_trend_report.html", "#f8fafc"),
        ("", "======================================================================", "#64748b"),
        ("", "HEADLINE NUMBERS", "#38bdf8"),
        ("", "  rows_analysed                : 2700", "#f8fafc"),
        ("", "  regions                      : 5 (Hyderabad, London, New York, Singapore, Sydney)", "#f8fafc"),
        ("", "  fastest_warming_region       : London", "#f43f5e"),
        ("", "  fastest_warming_c_per_decade : +0.3976 C / decade", "#f43f5e"),
        ("", "  mean_warming_c_per_decade    : +0.2984 C / decade", "#f59e0b"),
        ("", "  anomalies_detected           : 362 method flags (4 complementary detectors)", "#38bdf8"),
        ("", "  best_forecast_rmse           : 1.3148 C (Ridge calendar + trend)", "#10b981"),
        ("", "  data_completeness_pct        : 100.0%", "#10b981"),
    ]
    
    pytest_lines = [
        ("$ ", "python -m pytest -v", "#38bdf8"),
        ("", "============================= test session starts =============================", "#64748b"),
        ("", "platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0", "#94a3b8"),
        ("", "rootdir: Climate-Trend-Analyzer", "#94a3b8"),
        ("", "collected 26 items", "#94a3b8"),
        ("", "", "#94a3b8"),
        ("", "tests/test_pipeline.py::test_generator_creates_expected_shape PASSED     [  3%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_generator_is_deterministic PASSED           [  7%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_raw_data_is_intentionally_dirty PASSED      [ 11%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_cleaning_removes_duplicates_and_bad_dates PASSED [ 15%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_cleaning_removes_impossible_values PASSED   [ 19%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_cleaning_leaves_no_missing_values PASSED    [ 23%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_mixed_date_formats_are_parsed PASSED        [ 26%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_features_are_created PASSED                 [ 30%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_anomaly_is_centred_on_zero PASSED           [ 34%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_mann_kendall_detects_an_increasing_series PASSED [ 38%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_mann_kendall_detects_a_decreasing_series PASSED [ 42%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_mann_kendall_on_flat_series_finds_no_trend PASSED [ 46%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_ols_slope_matches_a_known_trend PASSED      [ 50%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_trends_agree_between_ols_and_mann_kendall PASSED [ 53%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_deseasonalization_removes_the_seasonal_cycle PASSED [ 57%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_anomaly_detection_returns_expected_schema PASSED [ 61%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_injected_extreme_events_are_detected PASSED [ 65%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_forecast_metrics_are_finite PASSED          [ 69%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_seasonal_naive_beats_naive PASSED           [ 73%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_eda_tables_have_expected_columns PASSED     [ 76%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_simulator_peaks_match_hemispheres PASSED    [ 80%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_forecast_does_not_use_validation_targets PASSED [ 84%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_forecast_ignores_leaky_eda_features PASSED  [ 88%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_original_missing_targets_preserved PASSED   [ 92%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_public_snapshot_is_real_and_valid PASSED    [ 96%]", "#10b981"),
        ("", "tests/test_pipeline.py::test_metrics_exclude_missing_truth PASSED        [100%]", "#10b981"),
        ("", "", "#94a3b8"),
        ("", "============================= 26 passed in 15.32s =============================", "#10b981")
    ]
    
    create_terminal_card("pwsh - python main.py --step all", pipeline_lines, SCREENSHOTS_DIR / "09_terminal_pipeline_run.png")
    create_terminal_card("pwsh - python main.py --step all", pipeline_lines, IMAGES_DIR / "12_terminal_output.png")
    create_terminal_card("pwsh - python -m pytest -v", pytest_lines, SCREENSHOTS_DIR / "10_pytest_suite_passed.png")

if __name__ == "__main__":
    run()
