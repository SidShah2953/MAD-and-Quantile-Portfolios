"""
Shared utilities for paper figure generation.

Provides common imports, paths, plotting configuration, and data loading
functions used across all figure-generation scripts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Configure matplotlib for LaTeX-compatible output
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 10,
    'axes.labelsize': 10,
    'axes.titlesize': 11,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.titlesize': 11,
    'text.usetex': False,  # Set to True if you have LaTeX installed for prettier rendering
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
})

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
RISK_ORDER = ["5.00%", "10.00%", "15.00%", "20.00%"]
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


def save_figure(fig: plt.Figure, filename: str) -> None:
    """Save a matplotlib figure to the figures directory as high DPI PNG."""
    output_path = FIGURES_ROOT / filename
    fig.savefig(output_path, format='png', dpi=300, bbox_inches='tight')
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
