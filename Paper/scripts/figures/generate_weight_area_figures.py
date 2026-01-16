"""Generate stacked area charts of portfolio weights at the 15% risk budget.

Grouping is by rebalance tenure (frequency): one figure per tenure.
Within each figure, we show one panel per optimized strategy. Each panel is a
stacked area chart of individual ETF weights (including cash if present) that
sum to 100%.

Output files (in Paper/LaTeX/figures):
- weights_area_tenure_1mo_risk15.png
- weights_area_tenure_3mo_risk15.png
- weights_area_tenure_6mo_risk15.png
- weights_area_tenure_1y_risk15.png

Assumes backtest outputs exist under Output/<tc>/<risk>/<freq>/Weights/<strategy>.xlsx.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))

from figure_helpers import (
    load_weights,
    save_figure,
    FREQ_ORDER,
)


RISK_LABEL = "15.00%"
TC_LABEL = "0 bps Transaction Cost"

# Keep this ordering stable across figures.
SECTOR_ORDER = [
    "XLY",
    "XLP",
    "XLE",
    "XLF",
    "XLV",
    "XLI",
    "XLB",
    "XLK",
    "XLU",
]

# We generate only optimized strategies here (they all include CSH when USE_CASH=True).
STRATEGIES = ["Volatility", "MAD", "IQR", "95%"]


def _slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _ordered_weight_columns(df: pd.DataFrame) -> list[str]:
    cols = list(df.columns)
    ordered = [c for c in SECTOR_ORDER if c in cols]
    if "CSH" in cols:
        ordered.append("CSH")

    # Include any unexpected columns at the end to avoid silently dropping.
    remaining = [c for c in cols if c not in ordered]
    return ordered + remaining


def _clean_weights(df: pd.DataFrame) -> pd.DataFrame:
    # Drop any completely-empty/zero rows (the pipeline writes 0 rows for boundaries).
    df = df.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    df = df.loc[df.sum(axis=1) > 0].copy()

    # Normalize to 100% for display (guards against minor numerical drift).
    row_sum = df.sum(axis=1).replace(0, np.nan)
    df = df.div(row_sum, axis=0) * 100.0

    return df


def _get_color_map(columns: list[str]) -> dict[str, str]:
    # tab20 has enough distinct colors for 10-ish series.
    cmap = plt.get_cmap("tab20")
    colors = [cmap(i) for i in range(len(columns))]

    # Make cash visually distinct if present.
    if "CSH" in columns:
        cash_idx = columns.index("CSH")
        colors[cash_idx] = (0.6, 0.6, 0.6, 1.0)  # gray

    return dict(zip(columns, colors))


def plot_tenure_weight_areas(freq: str) -> plt.Figure:
    """One figure per tenure (freq), one panel per strategy."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex=False, sharey=True)
    axes = axes.flatten()

    # Determine a common column set and color mapping so panels are comparable.
    columns_for_colors: list[str] | None = None

    # First pass: find the first available strategy weights to define columns.
    for strategy in STRATEGIES:
        try:
            w0 = load_weights(TC_LABEL, RISK_LABEL, freq, strategy)
        except FileNotFoundError:
            continue
        w0 = w0[_ordered_weight_columns(w0)]
        w0 = _clean_weights(w0)
        if len(w0) == 0:
            continue
        columns_for_colors = list(w0.columns)
        break

    if columns_for_colors is None:
        # Nothing to plot for this tenure.
        for ax in axes:
            ax.axis("off")
        fig.suptitle(f"No weights available (Rebalance: {freq}, Risk = {RISK_LABEL})", fontweight="bold")
        return fig

    color_map = _get_color_map(columns_for_colors)

    for idx, strategy in enumerate(STRATEGIES):
        ax = axes[idx]
        try:
            w = load_weights(TC_LABEL, RISK_LABEL, freq, strategy)
        except FileNotFoundError:
            ax.text(0.5, 0.5, f"No weights", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(strategy, fontweight="bold")
            ax.set_ylim(0, 100)
            continue

        w = w[_ordered_weight_columns(w)]
        w = _clean_weights(w)

        if len(w) == 0:
            ax.text(0.5, 0.5, f"Empty weights", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(strategy, fontweight="bold")
            ax.set_ylim(0, 100)
            continue

        # Align columns across panels (fill missing with 0 so areas still stack correctly).
        for c in columns_for_colors:
            if c not in w.columns:
                w[c] = 0.0
        w = w[columns_for_colors]

        x = w.index
        ys = [w[c].to_numpy() for c in w.columns]
        ax.stackplot(
            x,
            ys,
            labels=list(w.columns),
            colors=[color_map[c] for c in w.columns],
            alpha=0.95,
        )

        ax.set_title(strategy, fontweight="bold")
        ax.set_ylim(0, 100)
        ax.set_ylabel("Weight (%)")
        ax.grid(alpha=0.3, linestyle=":")

        for label in ax.get_xticklabels():
            label.set_rotation(30)
            label.set_horizontalalignment("right")

    # Hide any unused axes (in case STRATEGIES changes)
    for j in range(len(STRATEGIES), len(axes)):
        axes[j].axis("off")

    # Single legend for entire figure
    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="lower center", ncol=6, frameon=False, bbox_to_anchor=(0.5, -0.02))

    fig.suptitle(
        f"Portfolio Weights by Strategy (Rebalance: {freq}, Risk = {RISK_LABEL}, {TC_LABEL})",
        fontweight="bold",
        fontsize=13,
    )

    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    return fig


def main() -> None:
    for freq in FREQ_ORDER:
        fig = plot_tenure_weight_areas(freq)
        save_figure(fig, f"weights_area_tenure_{_slug(freq)}_risk15.png")


if __name__ == "__main__":
    main()
