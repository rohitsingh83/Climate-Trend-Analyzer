"""
Climate Trend Analyzer - source package
========================================
Modules
-------
config              : paths, thresholds, simulation parameters
data_generator      : virtual simulation of the climate collection system
data_loader         : dataset access layer
preprocessing       : cleaning & quality control
features            : feature engineering
eda                 : exploratory data analysis
trend_analysis      : OLS + Mann-Kendall trend statistics
anomaly_detection   : z-score / STL / IQR / Isolation Forest anomalies
forecasting         : baseline, ML and ARIMA forecasting
visualizations      : every figure used in the report
insights            : automatic natural-language insights
report_generator    : Markdown + HTML report builders
pipeline            : end-to-end orchestration
"""

__version__ = "1.0.0"
__all__ = [
    "config",
    "data_generator",
    "data_loader",
    "preprocessing",
    "features",
    "eda",
    "trend_analysis",
    "anomaly_detection",
    "forecasting",
    "visualizations",
    "insights",
    "report_generator",
    "pipeline",
]
