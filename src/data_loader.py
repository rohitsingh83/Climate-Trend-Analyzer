"""
data_loader.py
==============
Loads the climate dataset from disk (CSV) and provides small helpers.

Why a separate loader?
----------------------
In a real project the data source changes (a government portal, a sensor
gateway, an API).  If the rest of the code calls `pd.read_csv` everywhere,
that change becomes painful.  A single loader module isolates that concern -
this is the *separation of concerns* principle.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import config as cfg


def load_raw(path: Path | str | None = None) -> pd.DataFrame:
    """
    Load the RAW (messy) climate dataset.

    If the file does not exist yet it is created with the simulator, so the
    project is runnable on a fresh clone.
    """
    path = Path(path) if path else cfg.RAW_CSV
    if not path.exists():
        from .data_generator import write_raw_dataset
        write_raw_dataset(path)
    df = pd.read_csv(path)
    print(f"[data_loader] Loaded raw dataset: {path} -> shape {df.shape}")
    return df


def load_clean(path: Path | str | None = None) -> pd.DataFrame:
    """Load the cleaned dataset (produced by `preprocessing.clean_dataset`)."""
    path = Path(path) if path else cfg.CLEAN_CSV
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python main.py --step clean` first."
        )
    df = pd.read_csv(path, parse_dates=["date"])
    print(f"[data_loader] Loaded clean dataset: {path} -> shape {df.shape}")
    return df


def load_featured(path: Path | str | None = None) -> pd.DataFrame:
    """Load the feature-engineered dataset."""
    path = Path(path) if path else cfg.FEATURED_CSV
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python main.py --step features` first."
        )
    df = pd.read_csv(path, parse_dates=["date"])
    print(f"[data_loader] Loaded featured dataset: {path} -> shape {df.shape}")
    return df


def save_table(df: pd.DataFrame, path: Path | str) -> Path:
    """Persist any analysis table into `outputs/tables/` (or a given path)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"[data_loader] Saved table -> {path} ({len(df)} rows)")
    return path


def save_json(obj: dict, path: Path | str) -> Path:
    """Persist a JSON summary (used for the run manifest)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)
    print(f"[data_loader] Saved json  -> {path}")
    return path


def dataset_info(df: pd.DataFrame) -> str:
    """A printable profile of any dataframe."""
    lines = [
        "=" * 62,
        f"DATASET PROFILE  shape={df.shape}",
        "=" * 62,
        df.dtypes.to_string(),
        "-" * 62,
        f"Missing values:\n{df.isna().sum().to_string()}",
        "-" * 62,
        f"Duplicate rows: {int(df.duplicated().sum())}",
    ]
    return "\n".join(lines)
