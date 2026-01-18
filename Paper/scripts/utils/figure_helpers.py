"""
Shared utilities for paper figure generation.

Provides common imports, paths, plotting configuration, and data loading
functions used across all figure-generation scripts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

def apply_finance_theme() -> None:
    """Apply a clean, print-friendly plotting theme suitable for finance figures."""
    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except Exception:
        # Fall back silently if style not available.
        pass

    plt.rcParams.update({
        # Typography
        'font.family': 'DejaVu Sans',
        'font.size': 10,
        'axes.labelsize': 10,
        'axes.titlesize': 11,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 9,
        'figure.titlesize': 11,
        'text.usetex': False,

        # Figure export
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.05,

        # Axes / grid styling
        'axes.facecolor': 'white',
        'figure.facecolor': 'white',
        'axes.edgecolor': '#2f2f2f',
        'axes.linewidth': 0.8,
        'axes.grid': True,
        'grid.color': '#d9d9d9',
        'grid.linestyle': '-',
        'grid.linewidth': 0.6,
        'axes.spines.top': False,
        'axes.spines.right': False,

        # Lines
        'lines.linewidth': 1.6,
    })


def set_year_ticks_include_ends(ax: plt.Axes, dates: pd.Index | pd.Series) -> None:
    """Set x-axis ticks to show years and always include start/end year labels."""
    idx = pd.to_datetime(pd.Index(dates), errors="coerce").dropna()
    if len(idx) == 0:
        return

    start = idx.min()
    end = idx.max()
    start_year = int(start.year)
    end_year = int(end.year)
    span = end_year - start_year

    if span <= 12:
        step = 1
    elif span <= 35:
        step = 5
    else:
        step = 10

    # Candidate year ticks (Jan 1), restricted to visible range.
    year_ticks = [datetime(y, 1, 1) for y in range(start_year, end_year + 1, step)]
    year_ticks = [t for t in year_ticks if start.to_pydatetime() <= t <= end.to_pydatetime()]

    # Always include exact endpoints so the first/last year are present.
    ticks = [start.to_pydatetime(), *year_ticks, end.to_pydatetime()]

    # De-duplicate while preserving order.
    seen = set()
    unique_ticks: list[datetime] = []
    for t in ticks:
        key = mdates.date2num(t)
        if key in seen:
            continue
        seen.add(key)
        unique_ticks.append(t)

    ax.set_xticks(unique_ticks)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))


# Apply theme once on import
apply_finance_theme()

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_ROOT = PROJECT_ROOT / "Output"
DATA_ROOT = PROJECT_ROOT / "Data"
FIGURES_ROOT = PROJECT_ROOT / "Paper" / "LaTeX" / "figures"

# Ensure figures directory exists
FIGURES_ROOT.mkdir(parents=True, exist_ok=True)

# Standard ordering
STRATEGY_ORDER = ["S&P BnH", "Volatility", "MAD", "IQR", "95%"]
FREQ_ORDER = ["1mo", "3mo", "6mo", "1y"]
RISK_ORDER = ["5.00%", "10.00%", "15.00%"]
TC_ORDER = ["0 bps Transaction Cost", "1 bps Transaction Cost", "2 bps Transaction Cost"]

# Strategy display names and colors
STRATEGY_LABELS = {
    "S&P BnH": "S&P 500 BnH",
    "Volatility": "Volatility",
    "MAD": "MAD",
    "IQR": "IQR",
    "95%": "Trimmed (95%)",
}

STRATEGY_COLORS = {
    "S&P BnH": "#1f77b4",  # blue
    "Volatility": "#ff7f0e",  # orange
    "MAD": "#2ca02c",  # green
    "IQR": "#d62728",  # red
    "95%": "#9467bd",  # purple
}


def load_combined_data() -> pd.DataFrame:
    """Load Data/combined.csv with Date as datetime index."""
    df = pd.read_csv(DATA_ROOT / "combined.csv", index_col=0, parse_dates=True)
    return df


def load_metric(
    tc_label: str,
    risk_label: str,
    freq_label: str,
    metric_name: str,
) -> pd.DataFrame:
    """Load a metric Excel file from Output structure."""
    path = OUTPUT_ROOT / tc_label / risk_label / freq_label / "Metrics" / f"{metric_name}.xlsx"
    if not path.exists():
        raise FileNotFoundError(f"Metric file not found: {path}")
    df = pd.read_excel(path, index_col=0)
    df.index = pd.to_datetime(df.index, errors="coerce")
    return df


def load_weights(
    tc_label: str,
    risk_label: str,
    freq_label: str,
    strategy: str,
) -> pd.DataFrame:
    """Load portfolio weights for a specific strategy."""
    path = OUTPUT_ROOT / tc_label / risk_label / freq_label / "Weights" / f"{strategy}.xlsx"
    if not path.exists():
        raise FileNotFoundError(f"Weights file not found: {path}")
    df = pd.read_excel(path, index_col=0)
    df.index = pd.to_datetime(df.index, errors="coerce")
    return df


def load_turnover(
    tc_label: str,
    risk_label: str,
    freq_label: str,
) -> pd.DataFrame:
    """Load turnover comparison data."""
    path = OUTPUT_ROOT / tc_label / risk_label / freq_label / "Weights" / "Comparison.xlsx"
    if not path.exists():
        raise FileNotFoundError(f"Comparison file not found: {path}")
    df = pd.read_excel(path, index_col=0)
    df.index = pd.to_datetime(df.index, errors="coerce")
    return df


def load_transaction_cost_data(
    tc_label: str,
    risk_label: str,
    freq_label: str,
) -> pd.DataFrame:
    """Load Transaction Cost.xlsx with MultiIndex columns."""
    path = OUTPUT_ROOT / tc_label / risk_label / freq_label / "Transaction Cost.xlsx"
    if not path.exists():
        raise FileNotFoundError(f"Transaction Cost file not found: {path}")
    df = pd.read_excel(path, header=[0, 1], index_col=0)
    df.index = pd.to_datetime(df.index, errors="coerce")
    return df


def save_figure(fig: plt.Figure, filename: str, *, pad_inches: float | None = None) -> None:
    """Save a matplotlib figure to the figures directory as high DPI PNG."""
    output_path = FIGURES_ROOT / filename
    save_kwargs = dict(format='png', dpi=300, bbox_inches='tight')
    if pad_inches is not None:
        save_kwargs['pad_inches'] = pad_inches
    fig.savefig(output_path, **save_kwargs)
    print(f"✓ Saved: {output_path}")
    plt.close(fig)


def get_sector_etf_columns(df: pd.DataFrame) -> list[str]:
    """
    Return columns for sector ETFs only (exclude ^GSPC and CSH).
    
    Args:
        df: DataFrame with ETF columns
        
    Returns:
        List of sector ETF column names
    """
    exclude = {'^GSPC', 'CSH'}
    return [col for col in df.columns if col not in exclude]
