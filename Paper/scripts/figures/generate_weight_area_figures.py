"""Generate stacked area charts of portfolio weights at a focused risk budget.

Grouping is by rebalance tenure (frequency): one figure per tenure.
Within each figure, we show one panel per optimized strategy. Each panel is a
stacked area chart of individual ETF weights (including cash if present) that
sum to 100%.

Output files (in Paper/LaTeX/figures), for the focused risk budget:
- weights_area_<strategy>_risk10.png
- weights_area_tenure_1mo_risk10.png
- weights_area_tenure_3mo_risk10.png
- weights_area_tenure_6mo_risk10.png
- weights_area_tenure_1y_risk10.png

Assumes backtest outputs exist under Output/<tc>/<risk>/<freq>/Weights/<strategy>.xlsx.
"""

from __future__ import annotations

if __package__ is None or __package__ == "":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pathlib import Path
import re
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from Paper.scripts.utils.figure_helpers import load_weights, save_figure, FREQ_ORDER, set_year_ticks_include_ends


RISK_LABEL = "10.00%"
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


STRATEGY_FILE_STEMS = {
    "Volatility": "volatility",
    "MAD": "mad",
    "IQR": "iqr",
    "95%": "95",
}


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


def _set_year_ticks_through_2026(ax: plt.Axes, dates: pd.Index | pd.Series) -> None:
    idx = pd.to_datetime(pd.Index(dates), errors="coerce").dropna()
    if len(idx) == 0:
        return

    start = idx.min()
    end = max(idx.max(), pd.Timestamp("2026-01-01"))

    start_year = int(start.year)
    end_year = int(end.year)
    ticks = [datetime(y, 1, 1) for y in range(start_year, end_year + 1)]

    ax.set_xlim(start.to_pydatetime(), end.to_pydatetime())
    ax.set_xticks(ticks)
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y'))


def plot_tenure_weight_areas(freq: str) -> plt.Figure:
    """One figure per tenure (freq), one panel per strategy."""
    # 4x1 layout makes each panel wider ("longer") vs 2x2.
    fig, axes = plt.subplots(
        4,
        1,
        figsize=(16, 10),
        sharex=True,
        sharey=True,
    )

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

    # Year ticks on bottom axis only (shared x).
    _set_year_ticks_through_2026(axes[-1], x)
    for label in axes[-1].get_xticklabels():
        label.set_rotation(45)
        label.set_horizontalalignment("right")

    # Hide any unused axes (in case STRATEGIES changes)
    for j in range(len(STRATEGIES), len(axes)):
        axes[j].axis("off")

    # Single legend for entire figure
    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        fig.legend(
            handles,
            labels,
            loc="lower center",
            ncol=len(labels),
            frameon=False,
            bbox_to_anchor=(0.5, 0.0),
            fontsize=7,
            columnspacing=0.9,
            handletextpad=0.4,
        )

    fig.suptitle(
        f"Portfolio Weights by Strategy (Rebalance: {freq}, Risk = {RISK_LABEL}, {TC_LABEL})",
        fontweight="bold",
        fontsize=13,
    )

    # Leave room at the bottom for the legend.
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    return fig


def plot_strategy_weight_area(freq: str, strategy: str) -> plt.Figure:
    """One figure per strategy at a given (freq, risk) showing weights through time."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 4.2))

    try:
        w = load_weights(TC_LABEL, RISK_LABEL, freq, strategy)
    except FileNotFoundError:
        ax.axis("off")
        fig.suptitle(f"No weights available ({strategy}, Rebalance: {freq}, Risk = {RISK_LABEL})", fontweight="bold")
        return fig

    w = w[_ordered_weight_columns(w)]
    w = _clean_weights(w)
    if len(w) == 0:
        ax.axis("off")
        fig.suptitle(f"Empty weights ({strategy}, Rebalance: {freq}, Risk = {RISK_LABEL})", fontweight="bold")
        return fig

    columns = list(w.columns)
    color_map = _get_color_map(columns)

    x = w.index
    ys = [w[c].to_numpy() for c in columns]
    ax.stackplot(
        x,
        ys,
        labels=columns,
        colors=[color_map[c] for c in columns],
        alpha=0.95,
    )

    ax.set_ylim(0, 100)
    ax.set_ylabel("Weight (%)")
    ax.grid(alpha=0.3, linestyle=":")
    _set_year_ticks_through_2026(ax, x)

    for label in ax.get_xticklabels():
        label.set_rotation(45)
        label.set_horizontalalignment("right")

    handles, labels = ax.get_legend_handles_labels()
    if handles:
        fig.legend(
            handles,
            labels,
            loc="lower center",
            ncol=len(labels),
            frameon=False,
            bbox_to_anchor=(0.5, 0.0),
            fontsize=7,
            columnspacing=0.9,
            handletextpad=0.4,
        )

    fig.suptitle(
        f"{strategy} Weights Through Time (Rebalance: {freq}, Risk = {RISK_LABEL}, {TC_LABEL})",
        fontweight="bold",
        fontsize=13,
    )

    # Leave room at the bottom for the legend.
    fig.tight_layout(rect=(0, 0.06, 1, 0.92))
    return fig


def plot_strategy_weight_areas(freq: str) -> plt.Figure:
    """One figure per (freq, risk): one panel per strategy (4x1)."""
    fig, axes = plt.subplots(
        4,
        1,
        figsize=(16, 10),
        sharex=True,
        sharey=True,
    )

    # Determine a common column set and color mapping so panels are comparable.
    columns_for_colors: list[str] | None = None
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
            ax.text(0.5, 0.5, "No weights", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(strategy, fontweight="bold")
            ax.set_ylim(0, 100)
            continue

        w = w[_ordered_weight_columns(w)]
        w = _clean_weights(w)
        if len(w) == 0:
            ax.text(0.5, 0.5, "Empty weights", ha="center", va="center", transform=ax.transAxes)
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

    # Pretty x-axis only on the bottom subplot.
    _set_year_ticks_through_2026(axes[-1], x)
    for label in axes[-1].get_xticklabels():
        label.set_rotation(45)
        label.set_horizontalalignment("right")

    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        fig.legend(
            handles,
            labels,
            loc="lower center",
            ncol=len(labels),
            frameon=False,
            bbox_to_anchor=(0.5, 0.0),
            fontsize=7,
            columnspacing=0.9,
            handletextpad=0.4,
        )

    fig.suptitle(
        f"Portfolio Weights by Strategy (Rebalance: {freq}, Risk = {RISK_LABEL}, {TC_LABEL})",
        fontweight="bold",
        fontsize=13,
    )

    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    return fig


def main() -> None:
    # Per-strategy figures at a single (high-signal) rebalance schedule.
    # We use monthly rebalancing so weights evolve smoothly over the sample.
    strategy_freq = "1mo"
    for strategy in STRATEGIES:
        fig = plot_strategy_weight_area(strategy_freq, strategy)
        stem = STRATEGY_FILE_STEMS[strategy]
        save_figure(fig, f"weights_area_{stem}_risk10.png", pad_inches=0.02)

    # Combined strategy figure (matches tenure figures: one panel per strategy).
    fig = plot_strategy_weight_areas(strategy_freq)
    save_figure(fig, "weights_area_strategy_1mo_risk10.png", pad_inches=0.02)

    # Tenure comparison figures (one figure per rebalance tenure).
    for freq in FREQ_ORDER:
        fig = plot_tenure_weight_areas(freq)
        save_figure(fig, f"weights_area_tenure_{_slug(freq)}_risk10.png", pad_inches=0.02)


if __name__ == "__main__":
    main()
