"""
Automated screenshot capture script for Climate Trend Analyzer.
Uses Selenium with headless Chrome to capture high-resolution screenshots
of the website tabs, terminal outputs, and documentation assets.
"""
import time
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = ROOT / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR = ROOT / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

def capture_all():
    html_path = ROOT / "docs" / "index.html"
    file_url = html_path.as_uri()

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1600,1050")
    opts.add_argument("--hide-scrollbars")

    driver = webdriver.Chrome(options=opts)
    try:
        print(f"Loading {file_url}...")
        driver.get(file_url)
        time.sleep(3) # Wait for Plotly to render

        # 1. Hero & Overview Screenshot
        driver.save_screenshot(str(SCREENSHOTS_DIR / "01_website_hero.png"))
        driver.save_screenshot(str(IMAGES_DIR / "09_dashboard.png"))
        print("Captured 01_website_hero.png")

        # 2. Trends Tab
        driver.execute_script("switchTab('trends');")
        time.sleep(2)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "02_climate_trends.png"))
        print("Captured 02_climate_trends.png")

        # 3. Seasonality Tab
        driver.execute_script("switchTab('seasonality');")
        time.sleep(2)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "03_seasonal_patterns.png"))
        print("Captured 03_seasonal_patterns.png")

        # 4. Anomalies Tab
        driver.execute_script("switchTab('anomalies');")
        time.sleep(2)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "04_anomaly_detection_studio.png"))
        driver.save_screenshot(str(IMAGES_DIR / "09b_anomaly_dashboard.png"))
        print("Captured 04_anomaly_detection_studio.png")

        # 5. Forecasting Tab
        driver.execute_script("switchTab('forecasting');")
        time.sleep(2)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "05_ml_forecasting.png"))
        driver.save_screenshot(str(IMAGES_DIR / "09c_forecast_dashboard.png"))
        print("Captured 05_ml_forecasting.png")

        # 6. NOAA CO2 Tab
        driver.execute_script("switchTab('co2');")
        time.sleep(2)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "06_noaa_co2_companion.png"))
        driver.save_screenshot(str(IMAGES_DIR / "09d_public_co2.png"))
        print("Captured 06_noaa_co2_companion.png")

        # 7. Quality Audit Tab
        driver.execute_script("switchTab('audit');")
        time.sleep(2)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "07_quality_audit.png"))
        print("Captured 07_quality_audit.png")

        # 8. Full page capture (longer viewport)
        driver.set_window_size(1600, 2400)
        driver.execute_script("switchTab('trends'); window.scrollTo(0, 0);")
        time.sleep(2)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "08_full_page_overview.png"))
        driver.save_screenshot(str(IMAGES_DIR / "11_readme_preview.png"))
        print("Captured 08_full_page_overview.png")

        # 9. GitHub Repository live screenshot
        print("Capturing GitHub repo page...")
        driver.set_window_size(1600, 1050)
        driver.get("https://github.com/rohitsingh83/Climate-Trend-Analyzer")
        time.sleep(4)
        driver.save_screenshot(str(SCREENSHOTS_DIR / "10_github_repository.png"))
        driver.save_screenshot(str(IMAGES_DIR / "10_github_repo.png"))
        print("Captured 10_github_repository.png")

    finally:
        driver.quit()

if __name__ == "__main__":
    capture_all()
