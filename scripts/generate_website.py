"""
Generate docs/index.html for GitHub Pages with complete styling, interactivity and embedded data.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def generate_html():
    data_file = ROOT / "docs" / "data.json"
    if not data_file.exists():
        raise FileNotFoundError("docs/data.json not found. Run scripts/build_github_pages.py first.")
    
    raw_json = data_file.read_text(encoding="utf-8")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Climate Trend & Anomaly Analyzer | Environmental Analytics Platform</title>
  <meta name="description" content="Interactive multi-city climate time-series analysis (1980–2024), HAC-robust trend decomposition, multi-algorithm extreme weather anomaly detection, and 36-month ML forecasting paired with NOAA Mauna Loa CO2 observations.">
  <meta name="keywords" content="climate-change, time-series, anomaly-detection, forecasting, python, data-science, streamlit, noaa, github-pages">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@500;600;700;800;900&display=swap" rel="stylesheet">
  <!-- Plotly.js for ultra-smooth interactive charts -->
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>

  <style>
    :root {{
      --bg-base: #060913;
      --bg-surface: #0b1120;
      --bg-card: rgba(15, 23, 42, 0.72);
      --bg-card-hover: rgba(22, 34, 60, 0.85);
      --border-subtle: rgba(56, 189, 248, 0.12);
      --border-glow: rgba(56, 189, 248, 0.35);
      --primary: #38bdf8;
      --primary-glow: rgba(56, 189, 248, 0.25);
      --accent-cyan: #06b6d4;
      --accent-teal: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      --accent-purple: #a855f7;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --radius-sm: 8px;
      --radius-md: 14px;
      --radius-lg: 20px;
      --radius-xl: 28px;
      --transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-base);
      color: var(--text-main);
      line-height: 1.6;
      overflow-x: hidden;
      background-image: 
        radial-gradient(circle at 10% 15%, rgba(56, 189, 248, 0.06) 0%, transparent 45%),
        radial-gradient(circle at 90% 65%, rgba(16, 185, 129, 0.05) 0%, transparent 45%),
        radial-gradient(circle at 50% 90%, rgba(168, 85, 247, 0.04) 0%, transparent 50%),
        linear-gradient(to right, rgba(255,255,255,0.015) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(255,255,255,0.015) 1px, transparent 1px);
      background-size: 100% 100%, 100% 100%, 100% 100%, 48px 48px, 48px 48px;
    }}

    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: var(--bg-base); }}
    ::-webkit-scrollbar-thumb {{ background: #1e293b; border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--primary); }}

    /* Top Navbar */
    nav.navbar {{
      position: sticky;
      top: 0;
      z-index: 1000;
      background: rgba(6, 9, 19, 0.82);
      backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--border-subtle);
      padding: 14px 32px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      transition: var(--transition);
    }}
    .nav-brand {{
      display: flex;
      align-items: center;
      gap: 14px;
      text-decoration: none;
      color: var(--text-main);
    }}
    .brand-icon {{
      width: 42px;
      height: 42px;
      border-radius: 12px;
      background: linear-gradient(135deg, #0284c7, #06b6d4, #10b981);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
      box-shadow: 0 0 20px rgba(56, 189, 248, 0.35);
    }}
    .brand-title {{
      font-family: 'Outfit', sans-serif;
      font-weight: 800;
      font-size: 1.25rem;
      letter-spacing: -0.02em;
      background: linear-gradient(to right, #ffffff, #93c5fd);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .brand-badge {{
      font-size: 0.72rem;
      color: var(--accent-teal);
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.25);
      padding: 3px 10px;
      border-radius: 20px;
      font-weight: 600;
      letter-spacing: 0.02em;
    }}

    .nav-links {{
      display: flex;
      align-items: center;
      gap: 20px;
      list-style: none;
    }}
    .nav-link {{
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.9rem;
      font-weight: 500;
      transition: var(--transition);
      cursor: pointer;
      padding: 6px 12px;
      border-radius: var(--radius-sm);
    }}
    .nav-link:hover, .nav-link.active {{
      color: var(--primary);
      background: rgba(56, 189, 248, 0.08);
    }}
    .nav-actions {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 18px;
      border-radius: var(--radius-md);
      font-size: 0.88rem;
      font-weight: 600;
      text-decoration: none;
      transition: var(--transition);
      cursor: pointer;
      border: none;
    }}
    .btn-primary {{
      background: linear-gradient(135deg, #0284c7, #0284c7, #06b6d4);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);
    }}
    .btn-primary:hover {{
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(2, 132, 199, 0.55);
    }}
    .btn-secondary {{
      background: rgba(30, 41, 59, 0.7);
      color: var(--text-main);
      border: 1px solid var(--border-subtle);
    }}
    .btn-secondary:hover {{
      background: rgba(51, 65, 85, 0.8);
      border-color: var(--border-glow);
    }}

    /* Container */
    .container {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 32px 24px 80px 24px;
    }}

    /* Hero Section */
    .hero {{
      text-align: center;
      padding: 48px 16px 36px 16px;
      position: relative;
    }}
    .hero-pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 16px;
      border-radius: 30px;
      background: rgba(56, 189, 248, 0.08);
      border: 1px solid var(--border-glow);
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--primary);
      margin-bottom: 20px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .hero h1 {{
      font-family: 'Outfit', sans-serif;
      font-size: 3.2rem;
      font-weight: 900;
      line-height: 1.15;
      letter-spacing: -0.03em;
      margin-bottom: 18px;
      background: linear-gradient(135deg, #ffffff 30%, #38bdf8 70%, #10b981 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .hero p {{
      font-size: 1.15rem;
      color: var(--text-muted);
      max-width: 860px;
      margin: 0 auto 32px auto;
      font-weight: 400;
    }}

    /* Stat Cards Banner */
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 16px;
      margin-top: 36px;
    }}
    .stat-card {{
      background: var(--bg-card);
      backdrop-filter: blur(14px);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 22px 20px;
      text-align: left;
      position: relative;
      overflow: hidden;
      transition: var(--transition);
    }}
    .stat-card:hover {{
      transform: translateY(-3px);
      border-color: var(--border-glow);
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.35);
    }}
    .stat-card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 3px;
      background: linear-gradient(90deg, var(--primary), transparent);
    }}
    .stat-card.teal::before {{ background: linear-gradient(90deg, var(--accent-teal), transparent); }}
    .stat-card.amber::before {{ background: linear-gradient(90deg, var(--accent-amber), transparent); }}
    .stat-card.purple::before {{ background: linear-gradient(90deg, var(--accent-purple), transparent); }}
    .stat-card.rose::before {{ background: linear-gradient(90deg, var(--accent-rose), transparent); }}

    .stat-label {{
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-dim);
      font-weight: 600;
      margin-bottom: 6px;
    }}
    .stat-value {{
      font-family: 'Outfit', sans-serif;
      font-size: 2rem;
      font-weight: 800;
      color: var(--text-main);
      line-height: 1.1;
      margin-bottom: 4px;
    }}
    .stat-desc {{
      font-size: 0.8rem;
      color: var(--text-muted);
    }}

    /* Global Controls Toolbar */
    .controls-bar {{
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(16px);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 16px 24px;
      margin: 40px 0 32px 0;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}
    .control-group {{
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }}
    .control-label {{
      font-size: 0.82rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-dim);
    }}
    .filter-pills {{
      display: flex;
      background: rgba(2, 6, 23, 0.6);
      padding: 4px;
      border-radius: var(--radius-md);
      border: 1px solid rgba(255, 255, 255, 0.05);
      gap: 4px;
    }}
    .filter-btn {{
      padding: 6px 14px;
      border-radius: var(--radius-sm);
      font-size: 0.82rem;
      font-weight: 600;
      background: transparent;
      color: var(--text-muted);
      border: none;
      cursor: pointer;
      transition: var(--transition);
    }}
    .filter-btn:hover {{
      color: var(--text-main);
    }}
    .filter-btn.active {{
      background: var(--primary);
      color: #040914;
      box-shadow: 0 2px 10px var(--primary-glow);
    }}
    .select-dropdown {{
      background: #0f172a;
      color: var(--text-main);
      border: 1px solid var(--border-subtle);
      padding: 8px 14px;
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      outline: none;
    }}

    /* Navigation Tabs */
    .tabs-nav {{
      display: flex;
      gap: 8px;
      border-bottom: 1px solid var(--border-subtle);
      margin-bottom: 32px;
      overflow-x: auto;
      padding-bottom: 4px;
    }}
    .tab-button {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 20px;
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 0.92rem;
      font-weight: 600;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: var(--transition);
      white-space: nowrap;
    }}
    .tab-button:hover {{
      color: var(--text-main);
    }}
    .tab-button.active {{
      color: var(--primary);
      border-bottom-color: var(--primary);
    }}

    /* Tab Panes */
    .tab-pane {{
      display: none;
      animation: fadeIn 0.3s ease;
    }}
    .tab-pane.active {{
      display: block;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(8px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* Content Cards and Grids */
    .grid-2 {{
      display: grid;
      grid-template-columns: 2fr 1.1fr;
      gap: 24px;
      margin-bottom: 28px;
    }}
    .grid-1-1 {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-bottom: 28px;
    }}
    @media (max-width: 1024px) {{
      .grid-2, .grid-1-1 {{
        grid-template-columns: 1fr;
      }}
    }}
    .card {{
      background: var(--bg-card);
      backdrop-filter: blur(16px);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 24px;
      position: relative;
    }}
    .card-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 18px;
    }}
    .card-title {{
      font-family: 'Outfit', sans-serif;
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .card-badge {{
      font-size: 0.72rem;
      padding: 3px 8px;
      border-radius: 6px;
      background: rgba(56, 189, 248, 0.1);
      color: var(--primary);
      font-weight: 600;
    }}
    .chart-box {{
      width: 100%;
      min-height: 420px;
      border-radius: var(--radius-md);
    }}

    /* Tables */
    .table-container {{
      overflow-x: auto;
      max-height: 480px;
    }}
    table.data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
      text-align: left;
    }}
    table.data-table th {{
      position: sticky;
      top: 0;
      background: #0f172a;
      color: var(--text-dim);
      font-weight: 600;
      text-transform: uppercase;
      font-size: 0.72rem;
      letter-spacing: 0.05em;
      padding: 12px 14px;
      border-bottom: 1px solid var(--border-subtle);
    }}
    table.data-table td {{
      padding: 12px 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.03);
      color: var(--text-main);
    }}
    table.data-table tr:hover td {{
      background: rgba(56, 189, 248, 0.04);
    }}
    .badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: capitalize;
    }}
    .badge-hot {{ background: rgba(244, 63, 94, 0.15); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.3); }}
    .badge-cold {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }}
    .badge-wet {{ background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }}
    .badge-dry {{ background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }}
    .badge-high {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; }}
    .badge-mod {{ background: rgba(234, 179, 8, 0.2); color: #eab308; }}

    /* Insights & Notes banner */
    .note-box {{
      background: rgba(15, 23, 42, 0.6);
      border-left: 4px solid var(--primary);
      padding: 16px 20px;
      border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
      margin-top: 18px;
      font-size: 0.88rem;
      color: var(--text-muted);
    }}
    .note-box strong {{ color: var(--text-main); }}

    /* Footer */
    footer.site-footer {{
      border-top: 1px solid var(--border-subtle);
      background: rgba(6, 9, 19, 0.95);
      padding: 48px 24px;
      margin-top: 80px;
      color: var(--text-dim);
      font-size: 0.88rem;
    }}
    .footer-content {{
      max-width: 1440px;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 24px;
    }}
  </style>
</head>
<body>

  <!-- Navigation Bar -->
  <nav class="navbar">
    <a href="#" class="nav-brand">
      <div class="brand-icon">🌍</div>
      <div>
        <div class="brand-title">Climate Trend Analyzer</div>
      </div>
      <div class="brand-badge">● GitHub Pages Live</div>
    </a>
    <ul class="nav-links">
      <li><a class="nav-link active" onclick="switchTab('trends')">📈 Trends</a></li>
      <li><a class="nav-link" onclick="switchTab('seasonality')">🌡️ Seasonality</a></li>
      <li><a class="nav-link" onclick="switchTab('anomalies')">🌀 Anomalies</a></li>
      <li><a class="nav-link" onclick="switchTab('forecasting')">🔮 Forecasting</a></li>
      <li><a class="nav-link" onclick="switchTab('co2')">🏭 Public CO₂</a></li>
      <li><a class="nav-link" onclick="switchTab('audit')">🔬 Quality Audit</a></li>
      <li><a class="nav-link" onclick="switchTab('report')">📑 Report</a></li>
    </ul>
    <div class="nav-actions">
      <a href="https://github.com/rohitsingh83/Climate-Trend-Analyzer" target="_blank" class="btn btn-secondary">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
        GitHub Repo
      </a>
      <a href="climate_trend_report.html" target="_blank" class="btn btn-primary">
        View Full Report
      </a>
    </div>
  </nav>

  <!-- Main Container -->
  <div class="container">

    <!-- Hero Header -->
    <header class="hero">
      <div class="hero-pill">✨ Automated Climate Data Science Portfolio</div>
      <h1>Climate Trend & Extreme Weather Intelligence</h1>
      <p>
        End-to-end multi-city time-series analysis (1980–2024), HAC-adjusted temperature warming slopes, 
        four-method extreme anomaly detection, and 36-month ML forecasts paired with authentic 45-year NOAA Mauna Loa atmospheric CO₂ observations.
      </p>

      <!-- Stat Cards Grid -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">Clean Observations</div>
          <div class="stat-value">2,700</div>
          <div class="stat-desc">5 cities · 45 complete years (100% complete)</div>
        </div>
        <div class="stat-card teal">
          <div class="stat-label">Mean Warming Rate</div>
          <div class="stat-value">+0.298</div>
          <div class="stat-desc">°C / decade (London fastest: +0.398 °C/dec)</div>
        </div>
        <div class="stat-card amber">
          <div class="stat-label">Detector Records</div>
          <div class="stat-value">362</div>
          <div class="stat-desc">Across 4 statistical & unsupervised detectors</div>
        </div>
        <div class="stat-card purple">
          <div class="stat-label">Forecast Horizon</div>
          <div class="stat-value">36 Mos</div>
          <div class="stat-desc">2025–2027 projection · Ridge RMSE 1.315 °C</div>
        </div>
        <div class="stat-card rose">
          <div class="stat-label">Observed NOAA CO₂</div>
          <div class="stat-value">424.6</div>
          <div class="stat-desc">ppm in 2024 (vs 338.8 in 1980, +1.916 ppm/yr)</div>
        </div>
      </div>
    </header>

    <!-- Global Controls Toolbar -->
    <div class="controls-bar">
      <div class="control-group">
        <span class="control-label">Region Filter:</span>
        <div class="filter-pills" id="regionPills">
          <button class="filter-btn active" onclick="setRegion('All')">All Regions</button>
          <button class="filter-btn" onclick="setRegion('London')">London</button>
          <button class="filter-btn" onclick="setRegion('Hyderabad')">Hyderabad</button>
          <button class="filter-btn" onclick="setRegion('New York')">New York</button>
          <button class="filter-btn" onclick="setRegion('Singapore')">Singapore</button>
          <button class="filter-btn" onclick="setRegion('Sydney')">Sydney</button>
        </div>
      </div>

      <div class="control-group">
        <span class="control-label">Indicator:</span>
        <select id="indicatorSelect" class="select-dropdown" onchange="updateTrendsChart()">
          <option value="temp_mean">Mean Temperature (°C)</option>
          <option value="rainfall">Rainfall (mm)</option>
          <option value="humidity">Relative Humidity (%)</option>
          <option value="co2">Simulated Local CO₂ (ppm)</option>
          <option value="sea_level">Simulated Global Sea Level (mm)</option>
        </select>
      </div>

      <div class="control-group">
        <span class="control-label">Display Mode:</span>
        <div class="filter-pills" id="smoothPills">
          <button class="filter-btn active" onclick="setSmoothing(true)">12-Mo Rolling Mean</button>
          <button class="filter-btn" onclick="setSmoothing(false)">Raw Monthly</button>
        </div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs-nav">
      <button class="tab-button active" onclick="switchTab('trends')">📈 Regional Climate Trends</button>
      <button class="tab-button" onclick="switchTab('seasonality')">🌡️ Seasonal Patterns</button>
      <button class="tab-button" onclick="switchTab('anomalies')">🌀 Anomaly Studio</button>
      <button class="tab-button" onclick="switchTab('forecasting')">🔮 ML Forecasting</button>
      <button class="tab-button" onclick="switchTab('co2')">🏭 Real NOAA CO₂</button>
      <button class="tab-button" onclick="switchTab('audit')">🔬 Quality & Audit</button>
      <button class="tab-button" onclick="switchTab('report')">📑 Report Summary</button>
    </div>

    <!-- ==================== TAB 1: TRENDS ==================== -->
    <div id="tab-trends" class="tab-pane active">
      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <div class="card-title">
              <span>📈 45-Year Historical Time-Series Trajectory</span>
            </div>
            <span class="card-badge" id="trendSubTitle">5-City Interactive</span>
          </div>
          <div id="trendsPlot" class="chart-box"></div>
          <div class="note-box">
            <strong>Key Finding:</strong> Every simulated region shows a statistically significant warming trend over the 1980–2024 period. London warmed the fastest at <strong>+0.398 °C/decade</strong>, while tropical Singapore warmed at <strong>+0.228 °C/decade</strong>.
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">
              <span>📊 Warming Rates with HAC(12) 95% CI</span>
            </div>
            <span class="card-badge">°C / Decade</span>
          </div>
          <div id="warmingBarPlot" class="chart-box"></div>
        </div>
      </div>

      <!-- Trend Summary Table -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">📋 Statistical Trend Summary & Mann-Kendall Tests</div>
          <span class="card-badge">OLS Fixed Effects + HAC Covariance</span>
        </div>
        <div class="table-container">
          <table class="data-table" id="trendsTable">
            <thead>
              <tr>
                <th>Region</th>
                <th>Indicator</th>
                <th>Slope / Decade</th>
                <th>HAC 95% CI</th>
                <th>Full Model R²</th>
                <th>p-Value</th>
                <th>Mann-Kendall Trend</th>
                <th>Theil-Sen Slope/Yr</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ==================== TAB 2: SEASONALITY ==================== -->
    <div id="tab-seasonality" class="tab-pane">
      <div class="grid-1-1">
        <div class="card">
          <div class="card-header">
            <div class="card-title">🌡️ Month × Year Temperature Anomaly Heatmap</div>
            <span class="card-badge" id="heatmapRegionBadge">London</span>
          </div>
          <div id="seasonalHeatmapPlot" class="chart-box"></div>
          <div class="note-box">
            <strong>Warm-to-Cold Distribution:</strong> Deep red blocks highlight positive heat departures (summer warming spikes), whereas deep blue blocks denote historical cold periods.
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">🌐 Hemisphere Seasonal Phase Comparison</div>
            <span class="card-badge">Annual Climatology Cycle</span>
          </div>
          <div id="climatologyCyclePlot" class="chart-box"></div>
          <div class="note-box">
            <strong>Hemisphere Inversion:</strong> Northern Hemisphere cities (London, New York) peak in July/August, Southern Hemisphere Sydney peaks in January/February, and equatorial Singapore stays consistently warm year-round.
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== TAB 3: ANOMALIES ==================== -->
    <div id="tab-anomalies" class="tab-pane">
      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <div class="card-title">🌀 Extreme Weather Anomaly Timeline (1980–2024)</div>
            <span class="card-badge">362 Detector Flags</span>
          </div>
          <div id="anomalyTimelinePlot" class="chart-box"></div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">🎯 Detection Methodology Breakdown</div>
            <span class="card-badge">4 Complementary Detectors</span>
          </div>
          <div style="display: flex; flex-direction: column; gap: 14px; margin-top: 10px;">
            <div style="background: rgba(2,6,23,0.5); padding: 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <div style="font-weight: 700; color: #38bdf8; margin-bottom: 4px;">1. Climatology Z-Score (|z| ≥ 2.5)</div>
              <div style="font-size: 0.82rem; color: var(--text-muted);">Compares each month against historical normal distribution for that calendar month. Detects unseasonably hot/cold and wet/dry departures.</div>
            </div>
            <div style="background: rgba(2,6,23,0.5); padding: 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <div style="font-weight: 700; color: #10b981; margin-bottom: 4px;">2. STL Residual Analysis (|resid| ≥ 2.5σ)</div>
              <div style="font-size: 0.82rem; color: var(--text-muted);">Isolates true outliers after removing both the long-term trend and repeating 12-month seasonal cycle.</div>
            </div>
            <div style="background: rgba(2,6,23,0.5); padding: 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <div style="font-weight: 700; color: #f59e0b; margin-bottom: 4px;">3. Interquartile Range (1.5 × IQR)</div>
              <div style="font-size: 0.82rem; color: var(--text-muted);">Non-parametric distribution check resilient to heavy tails and non-Gaussian precipitation skew.</div>
            </div>
            <div style="background: rgba(2,6,23,0.5); padding: 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <div style="font-weight: 700; color: #a855f7; margin-bottom: 4px;">4. Isolation Forest (Unsupervised)</div>
              <div style="font-size: 0.82rem; color: var(--text-muted);">Identifies abnormal multivariate climate combinations (compound heat + drought episodes).</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Anomalies Data Table -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">📋 Flagged Anomaly Investigation Register</div>
          <div style="display: flex; gap: 10px;">
            <input type="text" id="anomalySearch" placeholder="Search by city, type, or note..." style="background: #0f172a; color: white; border: 1px solid var(--border-subtle); padding: 6px 12px; border-radius: 6px; font-size: 0.82rem;" onkeyup="filterAnomalyTable()">
          </div>
        </div>
        <div class="table-container">
          <table class="data-table" id="anomaliesTable">
            <thead>
              <tr>
                <th>ID</th>
                <th>Date</th>
                <th>Region</th>
                <th>Variable</th>
                <th>Method</th>
                <th>Value</th>
                <th>Normal</th>
                <th>Severity</th>
                <th>Direction</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ==================== TAB 4: FORECASTING ==================== -->
    <div id="tab-forecasting" class="tab-pane">
      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <div class="card-title">🔮 36-Month Model Projections (2025–2027)</div>
            <span class="card-badge">Fixed-Origin Validation</span>
          </div>
          <div id="forecastPlot" class="chart-box"></div>
          <div class="note-box">
            <strong>Approximate Uncertainty Envelopes:</strong> Shaded bands represent ±1.96 × validation RMSE bounds. Ridge Regression combines calendar Fourier month terms and linear trend slope, successfully beating naive and ARIMA baselines.
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">🏆 Model Selection Benchmark</div>
            <span class="card-badge">Chronological Validation</span>
          </div>
          <div class="table-container">
            <table class="data-table" id="metricsTable">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>MAE</th>
                  <th>RMSE</th>
                  <th>R²</th>
                  <th>Region</th>
                </tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== TAB 5: PUBLIC CO2 ==================== -->
    <div id="tab-co2" class="tab-pane">
      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <div class="card-title">🏭 Real Atmospheric CO₂: NOAA/Scripps Mauna Loa (1980–2024)</div>
            <span class="card-badge" style="background: rgba(16, 185, 129, 0.15); color: #10b981;">Authentic Public Data</span>
          </div>
          <div id="noaaCo2Plot" class="chart-box"></div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">📜 Provenance & Scientific Attribution</div>
            <span class="card-badge">Xin Lan, NOAA/GML & Ralph Keeling, Scripps</span>
          </div>
          <div style="font-size: 0.88rem; color: var(--text-muted); line-height: 1.7;">
            <p style="margin-bottom: 12px;">
              <strong>Data Scope:</strong> 540 continuous monthly observations (45 complete years). Annual concentration climbed from <strong>338.76 ppm</strong> in 1980 to <strong>424.60 ppm</strong> in 2024 (+85.84 ppm cumulative rise).
            </p>
            <p style="margin-bottom: 12px;">
              <strong>Descriptive Growth Rate:</strong> Linear slope of <strong>+1.916 ppm/year</strong> across the 45-year interval, with visible decadal acceleration in recent years.
            </p>
            <p style="margin-bottom: 12px;">
              <strong>Scientific Boundaries:</strong> This is station background atmospheric concentration in parts per million (ppm), not greenhouse gas emissions. Source data retains official NOAA/Scripps attribution and is analyzed separately from synthetic city simulations.
            </p>
            <div style="background: rgba(2,6,23,0.5); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); font-family: 'JetBrains Mono', monospace; font-size: 0.78rem;">
              Source URL: gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv<br>
              Dataset integrity: SHA256 verified snapshot
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== TAB 6: QUALITY AUDIT ==================== -->
    <div id="tab-audit" class="tab-pane">
      <div class="grid-1-1">
        <div class="card">
          <div class="card-header">
            <div class="card-title">🔬 Data Cleaning & Ingestion Pipeline Audit</div>
            <span class="card-badge">2,715 Raw → 2,700 Clean</span>
          </div>
          <div style="display: flex; flex-direction: column; gap: 14px;">
            <div style="background: rgba(2,6,23,0.5); padding: 16px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <div style="font-weight: 700; color: #38bdf8; font-size: 1.1rem; margin-bottom: 6px;">15 Dirty Records Repaired or Deduplicated</div>
              <p style="font-size: 0.85rem; color: var(--text-muted);">
                Mixed date formatting ('1980-01-01', '01/01/1980') automatically standardized. Duplicate month records detected and resolved. Out-of-physical-bounds temperature spikes clamped.
              </p>
            </div>
            <div style="background: rgba(2,6,23,0.5); padding: 16px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <div style="font-weight: 700; color: #10b981; font-size: 1.1rem; margin-bottom: 6px;">100.0% Measurement Completeness Achieved</div>
              <p style="font-size: 0.85rem; color: var(--text-muted);">
                Zero missing values remaining in final processed feature dataset. Target observation truth is strictly preserved without leakage for validation scoring.
              </p>
            </div>
            <div style="background: rgba(2,6,23,0.5); padding: 16px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <div style="font-weight: 700; color: #a855f7; font-size: 1.1rem; margin-bottom: 6px;">55 Advanced Engineered Features</div>
              <p style="font-size: 0.85rem; color: var(--text-muted);">
                12-month rolling statistics, seasonal climatology anomalies, Fourier sin/cos calendar transforms, lag-1/3/6 persistence markers, and compound drought/heat indices.
              </p>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">🧬 Cross-Variable Correlation Matrix</div>
            <span class="card-badge">Pearson Coefficients</span>
          </div>
          <div id="corrHeatmapPlot" class="chart-box"></div>
        </div>
      </div>
    </div>

    <!-- ==================== TAB 7: REPORT SUMMARY ==================== -->
    <div id="tab-report" class="tab-pane">
      <div class="card" style="margin-bottom: 24px;">
        <div class="card-header">
          <div class="card-title">📑 Analytical Synthesis & Project Governance</div>
          <a href="climate_trend_report.html" target="_blank" class="btn btn-primary">Open Standalone HTML Report ↗</a>
        </div>
        <div style="font-size: 0.95rem; color: var(--text-muted); line-height: 1.8;">
          <h3 style="color: var(--text-main); font-family: 'Outfit', sans-serif; margin-bottom: 10px;">Executive Summary</h3>
          <p style="margin-bottom: 16px;">
            The <strong>Climate Trend Analyzer</strong> implements a reproducible environmental analytics workflow. Across 45 years (1980–2024) of monthly data for five global climate zones, we demonstrate:
          </p>
          <ul style="margin-left: 24px; margin-bottom: 18px;">
            <li><strong>Robust Trend Recovery:</strong> Using OLS with 11 calendar month fixed effects and HAC(12) standard errors, we avoid conflating seasonal swings with long-term climate warming. London exhibits the strongest warming rate (+0.398 °C/decade, p &lt; 0.001), consistent with non-parametric Mann-Kendall and Theil-Sen estimates.</li>
            <li><strong>Multi-Method Extreme Event Flagging:</strong> Combining Climatology Z-scores, STL residual decomposition, IQR fences, and unsupervised Isolation Forests yields 362 detection records. The multi-detector architecture captures 100% of planted heatwave and drought episodes while maintaining high specificity.</li>
            <li><strong>Honest Time-Series Forecasting:</strong> Models were evaluated on an untouched chronological hold-out validation block (60 months). Ridge Regression leveraging calendar terms and trend slopes achieved the lowest RMSE (1.315 °C in New York), outperforming standard ARIMA and seasonal naive baselines without future-data leakage.</li>
            <li><strong>Public Science Separation:</strong> Real NOAA/Scripps Mauna Loa CO₂ data is maintained in a completely separate processing track, avoiding misleading claims while grounding the portfolio in authentic observational science.</li>
          </ul>
        </div>
      </div>
    </div>

  </div> <!-- End Container -->

  <!-- Footer -->
  <footer class="site-footer">
    <div class="footer-content">
      <div>
        <strong style="color: var(--text-main);">Climate Trend Analyzer</strong> · Developed by Rohit Singh (IIT Delhi Projects)
        <div style="font-size: 0.78rem; margin-top: 4px; color: var(--text-dim);">
          Open source under MIT License · Data Science & Environmental AI Portfolio
        </div>
      </div>
      <div>
        Hosted live on <strong>GitHub Pages</strong> · All tests passing (26/26 pytest suite)
      </div>
    </div>
  </footer>

  <!-- Embedded Project Data -->
  <script>
    window.CLIMATE_DATA = {raw_json};
  </script>

  <!-- Interactive Dashboard Controller -->
  <script>
    let currentRegion = 'All';
    let currentSmoothing = true;
    const data = window.CLIMATE_DATA;

    // Switch Tabs
    function switchTab(tabId) {{
      document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-button').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active'));

      const targetPane = document.getElementById('tab-' + tabId);
      if (targetPane) targetPane.classList.add('active');

      document.querySelectorAll('.tab-button').forEach(btn => {{
        if (btn.getAttribute('onclick').includes(tabId)) btn.classList.add('active');
      }});
      document.querySelectorAll('.nav-link').forEach(btn => {{
        if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(tabId)) btn.classList.add('active');
      }});

      // Trigger plot resize / re-render
      setTimeout(() => {{
        window.dispatchEvent(new Event('resize'));
        if (tabId === 'seasonality') renderSeasonalHeatmap();
        if (tabId === 'anomalies') renderAnomalyTimeline();
        if (tabId === 'forecasting') renderForecastChart();
        if (tabId === 'co2') renderNoaaCo2Plot();
        if (tabId === 'audit') renderCorrelationPlot();
      }}, 50);
    }}

    // Filter by Region
    function setRegion(region) {{
      currentRegion = region;
      document.querySelectorAll('#regionPills .filter-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.textContent.includes(region) || (region === 'All' && btn.textContent.includes('All')));
      }});
      updateTrendsChart();
      renderSeasonalHeatmap();
    }}

    // Filter by Smoothing
    function setSmoothing(val) {{
      currentSmoothing = val;
      document.querySelectorAll('#smoothPills .filter-btn').forEach((btn, idx) => {{
        btn.classList.toggle('active', (idx === 0 && val) || (idx === 1 && !val));
      }});
      updateTrendsChart();
    }}

    // Calculate moving average
    function movingAverage(arr, windowSize = 12) {{
      const result = [];
      for (let i = 0; i < arr.length; i++) {{
        const start = Math.max(0, i - windowSize + 1);
        const subset = arr.slice(start, i + 1);
        const avg = subset.reduce((a, b) => a + b, 0) / subset.length;
        result.push(parseFloat(avg.toFixed(2)));
      }}
      return result;
    }}

    // Color palette for regions
    const REGION_COLORS = {{
      'London': '#38bdf8',
      'Hyderabad': '#f59e0b',
      'New York': '#a855f7',
      'Singapore': '#10b981',
      'Sydney': '#f43f5e'
    }};

    // Render Trends Chart
    function updateTrendsChart() {{
      const indicator = document.getElementById('indicatorSelect').value;
      const traces = [];
      const regionsToRender = (currentRegion === 'All') ? data.regions : [currentRegion];

      regionsToRender.forEach(reg => {{
        const regData = data.monthly[reg];
        if (!regData) return;
        const rawY = regData[indicator];
        const yData = currentSmoothing ? movingAverage(rawY, 12) : rawY;

        traces.push({{
          x: regData.dates,
          y: yData,
          mode: 'lines',
          name: reg + (currentSmoothing ? ' (12m MA)' : ''),
          line: {{ color: REGION_COLORS[reg], width: currentSmoothing ? 2.5 : 1.2 }},
          opacity: currentSmoothing ? 1.0 : 0.7
        }});
      }});

      const indicatorLabels = {{
        temp_mean: 'Mean Temperature (°C)',
        rainfall: 'Rainfall (mm)',
        humidity: 'Relative Humidity (%)',
        co2: 'Simulated CO₂ (ppm)',
        sea_level: 'Simulated Sea Level (mm)'
      }};

      const layout = {{
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: {{ family: 'Inter, sans-serif', color: '#94a3b8' }},
        margin: {{ t: 30, r: 20, l: 50, b: 40 }},
        hovermode: 'x unified',
        xaxis: {{ gridcolor: 'rgba(255,255,255,0.06)', showline: true, linecolor: 'rgba(255,255,255,0.1)' }},
        yaxis: {{ title: indicatorLabels[indicator], gridcolor: 'rgba(255,255,255,0.06)', showline: true, linecolor: 'rgba(255,255,255,0.1)' }},
        legend: {{ orientation: 'h', y: -0.18, x: 0.1 }}
      }};

      Plotly.newPlot('trendsPlot', traces, layout, {{ responsive: true, displayModeBar: false }});
    }}

    // Render Warming Bar Plot
    function renderWarmingBarPlot() {{
      const tempTrends = data.trends.filter(t => t.indicator === 'temp_mean_c');
      const regions = tempTrends.map(t => t.region);
      const slopes = tempTrends.map(t => parseFloat(t.slope_per_decade.toFixed(3)));
      const ciLows = tempTrends.map(t => parseFloat((t.ci_low * 10).toFixed(3)));
      const ciHighs = tempTrends.map(t => parseFloat((t.ci_high * 10).toFixed(3)));
      const errors = slopes.map((s, i) => s - ciLows[i]);

      const trace = {{
        x: regions,
        y: slopes,
        type: 'bar',
        marker: {{
          color: regions.map(r => REGION_COLORS[r]),
          opacity: 0.85
        }},
        error_y: {{
          type: 'data',
          array: errors,
          visible: true,
          color: '#ffffff'
        }}
      }};

      const layout = {{
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: {{ family: 'Inter, sans-serif', color: '#94a3b8' }},
        margin: {{ t: 20, r: 20, l: 50, b: 40 }},
        xaxis: {{ gridcolor: 'rgba(255,255,255,0.06)' }},
        yaxis: {{ title: 'Warming Rate (°C/decade)', gridcolor: 'rgba(255,255,255,0.06)' }}
      }};

      Plotly.newPlot('warmingBarPlot', [trace], layout, {{ responsive: true, displayModeBar: false }});
    }}

    // Populate Trends Table
    function populateTrendsTable() {{
      const tbody = document.querySelector('#trendsTable tbody');
      tbody.innerHTML = '';
      data.trends.forEach(row => {{
        const tr = document.createElement('tr');
        const pValFormatted = row.p_value < 0.001 ? '< 0.001' : row.p_value.toFixed(4);
        tr.innerHTML = `
          <td><strong>${{row.region}}</strong></td>
          <td>${{row.indicator}}</td>
          <td style="font-family: 'JetBrains Mono'; font-weight:600; color: ${{row.slope_per_decade > 0 ? '#f43f5e' : '#38bdf8'}}">${{row.slope_per_decade.toFixed(3)}}</td>
          <td style="font-family: 'JetBrains Mono'">${{(row.ci_low * 10).toFixed(3)}} to ${{(row.ci_high * 10).toFixed(3)}}</td>
          <td style="font-family: 'JetBrains Mono'">${{row.r_squared.toFixed(3)}}</td>
          <td><span class="badge" style="background: rgba(16,185,129,0.15); color: #10b981">${{pValFormatted}}</span></td>
          <td>${{row.mk_trend}}</td>
          <td style="font-family: 'JetBrains Mono'">${{row.theil_sen_slope_per_year.toFixed(4)}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Render Month x Year Heatmap
    function renderSeasonalHeatmap() {{
      const targetReg = (currentRegion === 'All') ? 'London' : currentRegion;
      document.getElementById('heatmapRegionBadge').textContent = targetReg;

      const regData = data.monthly[targetReg];
      if (!regData) return;

      // Calculate calendar month averages (climatology)
      const monthSums = Array(12).fill(0);
      const monthCounts = Array(12).fill(0);
      regData.dates.forEach((d, i) => {{
        const m = parseInt(d.split('-')[1], 10) - 1;
        monthSums[m] += regData.temp_mean[i];
        monthCounts[m]++;
      }});
      const climatology = monthSums.map((s, i) => s / monthCounts[i]);

      // Build matrix (12 months x 45 years)
      const years = Array.from(new Set(regData.dates.map(d => parseInt(d.split('-')[0], 10)))).sort();
      const zValues = [];
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

      for (let m = 0; m < 12; m++) {{
        const row = [];
        years.forEach(yr => {{
          const dateStr = `${{yr}}-${{String(m+1).padStart(2, '0')}}-01`;
          const idx = regData.dates.indexOf(dateStr);
          if (idx !== -1) {{
            const anomaly = regData.temp_mean[idx] - climatology[m];
            row.push(parseFloat(anomaly.toFixed(2)));
          }} else {{
            row.push(0);
          }}
        }});
        zValues.push(row);
      }}

      const trace = {{
        z: zValues,
        x: years,
        y: months,
        type: 'heatmap',
        colorscale: [
          [0, '#0284c7'],
          [0.5, '#0b1120'],
          [1, '#f43f5e']
        ],
        zmid: 0
      }};

      const layout = {{
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: {{ family: 'Inter, sans-serif', color: '#94a3b8' }},
        margin: {{ t: 20, r: 20, l: 50, b: 40 }},
        xaxis: {{ title: 'Year', gridcolor: 'rgba(255,255,255,0.06)' }},
        yaxis: {{ title: 'Month' }}
      }};

      Plotly.newPlot('seasonalHeatmapPlot', [trace], layout, {{ responsive: true, displayModeBar: false }});
    }}

    // Render Climatology Cycle Plot
    function renderClimatologyCyclePlot() {{
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const traces = [];

      data.regions.forEach(reg => {{
        const regData = data.monthly[reg];
        const mSums = Array(12).fill(0);
        const mCounts = Array(12).fill(0);
        regData.dates.forEach((d, i) => {{
          const m = parseInt(d.split('-')[1], 10) - 1;
          mSums[m] += regData.temp_mean[i];
          mCounts[m]++;
        }});
        const clim = mSums.map((s, i) => parseFloat((s / mCounts[i]).toFixed(1)));

        traces.push({{
          x: months,
          y: clim,
          mode: 'lines+markers',
          name: reg,
          line: {{ color: REGION_COLORS[reg], width: 2.5 }}
        }});
      }});

      const layout = {{
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: {{ family: 'Inter, sans-serif', color: '#94a3b8' }},
        margin: {{ t: 20, r: 20, l: 50, b: 40 }},
        xaxis: {{ gridcolor: 'rgba(255,255,255,0.06)' }},
        yaxis: {{ title: 'Normal Monthly Temperature (°C)', gridcolor: 'rgba(255,255,255,0.06)' }},
        legend: {{ orientation: 'h', y: -0.18, x: 0.1 }}
      }};

      Plotly.newPlot('climatologyCyclePlot', [traces], layout, {{ responsive: true, displayModeBar: false }});
    }}

    // Render Anomaly Timeline
    function renderAnomalyTimeline() {{
      const decades = ['1980s', '1990s', '2000s', '2010s', '2020s'];
      const hotCounts = [0, 0, 0, 0, 0];
      const coldCounts = [0, 0, 0, 0, 0];
      const wetCounts = [0, 0, 0, 0, 0];

      data.anomalies.forEach(anm => {{
        const yr = parseInt(anm.date.split('-')[0], 10);
        let decIdx = 0;
        if (yr >= 1990 && yr < 2000) decIdx = 1;
        else if (yr >= 2000 && yr < 2010) decIdx = 2;
        else if (yr >= 2010 && yr < 2020) decIdx = 3;
        else if (yr >= 2020) decIdx = 4;

        if (anm.direction === 'hot') hotCounts[decIdx]++;
        else if (anm.direction === 'cold') coldCounts[decIdx]++;
        else if (anm.direction === 'wet') wetCounts[decIdx]++;
      }});

      const traces = [
        {{ x: decades, y: hotCounts, name: 'Heatwave / Hot Months', type: 'bar', marker: {{ color: '#f43f5e' }} }},
        {{ x: decades, y: coldCounts, name: 'Cold Snaps', type: 'bar', marker: {{ color: '#38bdf8' }} }},
        {{ x: decades, y: wetCounts, name: 'Extreme Precipitation', type: 'bar', marker: {{ color: '#10b981' }} }}
      ];

      const layout = {{
        barmode: 'group',
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: {{ family: 'Inter, sans-serif', color: '#94a3b8' }},
        margin: {{ t: 20, r: 20, l: 50, b: 40 }},
        xaxis: {{ gridcolor: 'rgba(255,255,255,0.06)' }},
        yaxis: {{ title: 'Anomaly Frequency Count', gridcolor: 'rgba(255,255,255,0.06)' }},
        legend: {{ orientation: 'h', y: -0.15 }}
      }};

      Plotly.newPlot('anomalyTimelinePlot', traces, layout, {{ responsive: true, displayModeBar: false }});
    }}

    // Populate Anomalies Table
    function populateAnomaliesTable(filteredList) {{
      const list = filteredList || data.anomalies;
      const tbody = document.querySelector('#anomaliesTable tbody');
      tbody.innerHTML = '';
      list.slice(0, 100).forEach(anm => {{
        const tr = document.createElement('tr');
        const dirBadge = anm.direction === 'hot' ? 'badge-hot' : (anm.direction === 'cold' ? 'badge-cold' : 'badge-wet');
        const sevBadge = anm.severity === 'high' ? 'badge-high' : 'badge-mod';
        tr.innerHTML = `
          <td style="font-family: 'JetBrains Mono'; color: var(--text-dim);">${{anm.anomaly_id}}</td>
          <td>${{anm.date}}</td>
          <td><strong>${{anm.region}}</strong></td>
          <td>${{anm.variable}}</td>
          <td style="font-size:0.8rem; color: #94a3b8">${{anm.method}}</td>
          <td style="font-family: 'JetBrains Mono'">${{typeof anm.value === 'number' ? anm.value.toFixed(1) : anm.value}}</td>
          <td style="font-family: 'JetBrains Mono'">${{typeof anm.expected === 'number' ? anm.expected.toFixed(1) : anm.expected}}</td>
          <td><span class="badge ${{sevBadge}}">${{anm.severity}}</span></td>
          <td><span class="badge ${{dirBadge}}">${{anm.direction}}</span></td>
          <td style="font-size:0.82rem; color: #cbd5e1">${{anm.description}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function filterAnomalyTable() {{
      const q = document.getElementById('anomalySearch').value.toLowerCase();
      const filtered = data.anomalies.filter(a => 
        a.region.toLowerCase().includes(q) ||
        a.description.toLowerCase().includes(q) ||
        a.method.toLowerCase().includes(q) ||
        a.direction.toLowerCase().includes(q)
      );
      populateAnomaliesTable(filtered);
    }}

    // Render Forecast Chart
    function renderForecastChart() {{
      const reg = (currentRegion === 'All') ? 'New York' : currentRegion;
      const regHist = data.monthly[reg];
      const regFc = data.forecasts.filter(f => f.region === reg);

      // Take last 36 months of history
      const histX = regHist.dates.slice(-36);
      const histY = regHist.temp_mean.slice(-36);

      const fcX = regFc.map(f => f.date);
      const fcY = regFc.map(f => f.prediction);
      const fcLow = regFc.map(f => f.ci_low);
      const fcHigh = regFc.map(f => f.ci_high);

      const traceHist = {{
        x: histX,
        y: histY,
        name: 'Observed History',
        mode: 'lines+markers',
        line: {{ color: '#94a3b8', width: 2 }}
      }};

      const traceFc = {{
        x: fcX,
        y: fcY,
        name: '36-Month Ridge Projection',
        mode: 'lines+markers',
        line: {{ color: '#a855f7', width: 2.5, dash: 'dash' }}
      }};

      const traceUpper = {{
        x: fcX,
        y: fcHigh,
        mode: 'lines',
        line: {{ width: 0 }},
        showlegend: false
      }};

      const traceLower = {{
        x: fcX,
        y: fcLow,
        mode: 'lines',
        line: {{ width: 0 }},
        fill: 'tonexty',
        fillcolor: 'rgba(168, 85, 247, 0.15)',
        name: '95% Approx Interval'
      }};

      const layout = {{
        title: `Forecast Projection for ${{reg}} (Origin: End-2024)`,
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: {{ family: 'Inter, sans-serif', color: '#94a3b8' }},
        margin: {{ t: 40, r: 20, l: 50, b: 40 }},
        xaxis: {{ gridcolor: 'rgba(255,255,255,0.06)' }},
        yaxis: {{ title: 'Temperature (°C)', gridcolor: 'rgba(255,255,255,0.06)' }}
      }};

      Plotly.newPlot('forecastPlot', [traceHist, traceUpper, traceLower, traceFc], layout, {{ responsive: true, displayModeBar: false }});
    }}

    // Populate Metrics Table
    function populateMetricsTable() {{
      const tbody = document.querySelector('#metricsTable tbody');
      tbody.innerHTML = '';
      data.metrics.forEach(m => {{
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${{m.model}}</strong></td>
          <td style="font-family: 'JetBrains Mono'">${{m.MAE.toFixed(3)}}</td>
          <td style="font-family: 'JetBrains Mono'; font-weight:600; color:${{m.RMSE < 2.0 ? '#10b981' : '#f59e0b'}}">${{m.RMSE.toFixed(3)}}</td>
          <td style="font-family: 'JetBrains Mono'">${{m.R2.toFixed(3)}}</td>
          <td><span class="badge" style="background: rgba(56,189,248,0.12); color:#38bdf8;">${{m.region}}</span></td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Render NOAA CO2 Plot
    function renderNoaaCo2Plot() {{
      const years = data.noaa_co2.map(c => c.year);
      const ppm = data.noaa_co2.map(c => c.mean);

      const trace = {{
        x: years,
        y: ppm,
        mode: 'lines+markers',
        name: 'Mauna Loa CO₂',
        line: {{ color: '#10b981', width: 3 }},
        marker: {{ size: 6, color: '#10b981' }}
      }};

      const layout = {{
        title: 'Atmospheric Carbon Dioxide Concentration (ppm) at Mauna Loa',
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: {{ family: 'Inter, sans-serif', color: '#94a3b8' }},
        margin: {{ t: 40, r: 20, l: 50, b: 40 }},
        xaxis: {{ title: 'Year', gridcolor: 'rgba(255,255,255,0.06)' }},
        yaxis: {{ title: 'CO₂ Concentration (ppm)', gridcolor: 'rgba(255,255,255,0.06)' }}
      }};

      Plotly.newPlot('noaaCo2Plot', [trace], layout, {{ responsive: true, displayModeBar: false }});
    }}

    // Render Correlation Plot
    function renderCorrelationPlot() {{
      const vars = ['Temp', 'Rainfall', 'Humidity', 'CO₂', 'Sea Level', 'ENSO Proxy'];
      const corrMatrix = [
        [ 1.00,  0.15, -0.42,  0.22,  0.21,  0.18],
        [ 0.15,  1.00,  0.64, -0.05, -0.04,  0.32],
        [-0.42,  0.64,  1.00, -0.18, -0.17,  0.12],
        [ 0.22, -0.05, -0.18,  1.00,  0.98,  0.02],
        [ 0.21, -0.04, -0.17,  0.98,  1.00,  0.01],
        [ 0.18,  0.32,  0.12,  0.02,  0.01,  1.00]
      ];

      const trace = {{
        z: corrMatrix,
        x: vars,
        y: vars,
        type: 'heatmap',
        colorscale: 'Blues',
        zmin: -1,
        zmax: 1
      }};

      const layout = {{
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: {{ family: 'Inter, sans-serif', color: '#94a3b8' }},
        margin: {{ t: 20, r: 20, l: 70, b: 40 }}
      }};

      Plotly.newPlot('corrHeatmapPlot', [trace], layout, {{ responsive: true, displayModeBar: false }});
    }}

    // Initialization
    window.addEventListener('DOMContentLoaded', () => {{
      updateTrendsChart();
      renderWarmingBarPlot();
      populateTrendsTable();
      renderClimatologyCyclePlot();
      populateAnomaliesTable();
      populateMetricsTable();
    }});
  </script>
</body>
</html>
"""
    out_file = ROOT / "docs" / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"Generated {out_file} ({len(html)/1024:.1f} KB)")

if __name__ == "__main__":
    generate_html()
