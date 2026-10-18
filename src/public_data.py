"""Real public-data companion: NOAA/Scripps Mauna Loa monthly CO2.

This track is NEVER merged with simulated city measurements. It preserves
source comments, source URL, SHA256 and retrieval time. Offline analysis uses
the bundled snapshot; --refresh downloads a new snapshot explicitly.
Run: python -m src.public_data [--refresh]
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen
import numpy as np
import pandas as pd
from . import config as cfg

URL = 'https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv'
PATH = cfg.RAW_DIR / 'noaa_co2_mm_mlo.csv'
CITATION = 'Xin Lan, NOAA/GML, and Ralph Keeling, Scripps Institution of Oceanography; https://gml.noaa.gov/ccgg/trends/data.html'


def download():
    """Download with a timeout; fail clearly rather than fabricate real data."""
    req = Request(URL, headers={'User-Agent':'ClimateTrendAnalyzer educational project'})
    with urlopen(req, timeout=45) as res:
        content = res.read()
    if b'year,month' not in content.replace(b' ',b''):
        raise ValueError('Unexpected NOAA response; expected a monthly CO2 CSV')
    PATH.write_bytes(content)
    meta = dict(source_url=URL, retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                sha256=hashlib.sha256(content).hexdigest(),citation=CITATION,
                license_note='NOAA public data: preserve source attribution and file usage notes; not relicensed under project MIT')
    (cfg.RAW_DIR/'noaa_provenance.json').write_text(json.dumps(meta,indent=2))


def analyze(refresh=False):
    if refresh or not PATH.exists():
        download()
    raw = pd.read_csv(PATH,comment='#',skipinitialspace=True)
    raw.columns = raw.columns.str.strip()
    raw['date'] = pd.to_datetime(dict(year=raw.year,month=raw.month,day=1))
    raw['average'] = pd.to_numeric(raw['average'],errors='coerce').mask(lambda s:s<0)
    # Complete, common analysis window. Do not silently compare incomplete years.
    d = raw[(raw.date>='1980-01-01') & (raw.date<='2024-12-01')].copy()
    d = d[['date','average']].rename(columns={'average':'co2_ppm'}).dropna()
    d['year']=d.date.dt.year
    annual = d.groupby('year',as_index=False).co2_ppm.agg(['mean','count']).reset_index()
    annual = annual[annual['count']==12].copy()
    from scipy.stats import linregress
    fit = linregress(annual.year,annual['mean'])
    summary = dict(dataset='NOAA/Scripps Mauna Loa monthly atmospheric CO2',
                   data_type='PUBLIC OBSERVATIONS, separate from synthetic city data',
                   n_months=len(d),start=str(d.date.min().date()),end=str(d.date.max().date()),
                   n_complete_years=len(annual),linear_slope_ppm_per_year=float(fit.slope),
                   first_complete_year_mean_ppm=float(annual['mean'].iloc[0]),
                   last_complete_year_mean_ppm=float(annual['mean'].iloc[-1]),
                   source=URL,citation=CITATION,
                   caveats='Station CO2 concentration in ppm, not emissions; linear summary of accelerating series. Source notes include measurement-site interruptions and interpolation.')
    d.to_csv(cfg.PROCESSED_DIR/'noaa_co2_monthly.csv',index=False)
    annual.to_csv(cfg.TABLES_DIR/'noaa_co2_annual.csv',index=False)
    (cfg.OUTPUTS_DIR/'noaa_summary.json').write_text(json.dumps(summary,indent=2))
    cfg.use_headless_backend()
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11,5))
    ax.plot(d.date,d.co2_ppm,color='#167d9a',lw=1,label='Public monthly observations')
    ax.plot(pd.to_datetime(annual.year.astype(str)+'-07-01'),annual['mean'],color='#c65d37',lw=2,label='Complete-year mean')
    ax.set(title='NOAA/Scripps Mauna Loa atmospheric CO2 — PUBLIC DATA, 1980–2024',xlabel='Date',ylabel='CO2 concentration (ppm)')
    ax.legend(); fig.tight_layout();fig.savefig(cfg.FIGURES_DIR/'16_public_noaa_co2.png',dpi=150);plt.close(fig)
    print(json.dumps(summary,indent=2))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh',action='store_true')
    args=parser.parse_args()
    analyze(args.refresh)
