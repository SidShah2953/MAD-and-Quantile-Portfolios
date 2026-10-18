"""
Rebuild `heatmap_mdd_fullsample_zero_cost.png`.

The published manuscript includes this figure, but no generator for it exists in
Paper/scripts/: the figure pipeline only emits `heatmap_mdd_zero_cost.png`, the
*within-period* drawdown that the review replaced. The full-sample numbers live
only in build_fullsample_mdd.py, which writes a LaTeX table and no figure.

This module closes that gap. It takes the drawdowns from build_fullsample_mdd's
own reconstruction, so the values are the paper's, and lays them out to match the
published figure (four strategy panels, no benchmark, 'P95' label, shared scale).

`EXPECTED` holds the numbers read off the published PNG; build_grid() is checked
against them so a silent change in the data would fail loudly rather than quietly
ship a different figure in the video.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from Paper.scripts.build_fullsample_mdd import (
    TC_LABEL,
    _daily_returns,
    max_drawdown_pct,
    portfolio_daily_returns,
)
from Paper.scripts.utils.constants import FREQ_ORDER, RISK_ORDER

PANELS = ["Volatility", "MAD", "IQR", "95%"]
PANEL_LABELS = {"95%": "P95"}

# Transcribed from the published figure, Paper/LaTeX/figures/heatmap_mdd_fullsample_zero_cost.png
EXPECTED = {
    "Volatility": [[13.9, 19.3, 17.8, 16.9], [27.2, 34.4, 33.8, 32.4], [34.9, 36.7, 33.5, 43.3]],
    "MAD":        [[14.1, 18.1, 21.9, 20.7], [30.7, 36.7, 33.5, 36.3], [35.9, 36.9, 33.5, 45.0]],
    "IQR":        [[22.0, 38.6, 31.7, 22.5], [34.8, 36.7, 33.5, 39.5], [35.8, 39.5, 35.6, 45.4]],
    "95%":        [[15.3, 21.7, 17.3, 18.3], [26.9, 33.2, 29.7, 31.8], [36.8, 36.7, 33.5, 41.7]],
}


def build_grid() -> dict[str, np.ndarray]:
    rets = _daily_returns()
    grids: dict[str, np.ndarray] = {}
    for strategy in PANELS:
        g = np.full((len(RISK_ORDER), len(FREQ_ORDER)), np.nan)
        for i, risk in enumerate(RISK_ORDER):
            for j, freq in enumerate(FREQ_ORDER):
                try:
                    series = portfolio_daily_returns(rets, risk, freq, strategy)
                except FileNotFoundError:
                    continue
                if series.empty:
                    continue
                raw = max_drawdown_pct(series)
                g[i, j] = -raw if raw <= 0 else raw
        grids[strategy] = g
    return grids


# The published figure prints one decimal, and its generator is not in the repo,
# so the last digit cannot be bit-reproduced. Measured agreement across all 48
# cells is within 0.06pp, with differences in both directions -- numerical noise
# in the reconstruction, not a difference in the data. TOL is set to the figure's
# own display granularity; anything larger is a real divergence and must fail.
TOL = 0.1


def check(grids: dict[str, np.ndarray], tol: float = TOL) -> list[str]:
    """Compare against the published figure; return a list of real divergences."""
    problems = []
    for strategy, grid in grids.items():
        want = np.array(EXPECTED[strategy])
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                got, exp = grid[i, j], want[i, j]
                if np.isnan(got) or abs(got - exp) > tol:
                    problems.append(
                        f"{strategy} {RISK_ORDER[i]} {FREQ_ORDER[j]}: got {got:.3f}, published {exp:.1f}"
                    )
    return problems


def max_deviation(grids: dict[str, np.ndarray]) -> float:
    return max(
        abs(grids[s][i, j] - EXPECTED[s][i][j])
        for s in grids
        for i in range(3)
        for j in range(4)
    )


def plot(grids: dict[str, np.ndarray]) -> plt.Figure:
    values = np.concatenate([g[~np.isnan(g)].ravel() for g in grids.values()])
    vmin, vmax = float(values.min()), float(values.max())
    mid = 0.5 * (vmin + vmax)

    fig, axes = plt.subplots(1, len(PANELS), figsize=(3.5 * len(PANELS), 4), sharey=True,
                             constrained_layout=True)
    im = None
    for k, strategy in enumerate(PANELS):
        ax = axes[k]
        grid = grids[strategy]
        im = ax.imshow(grid, cmap="RdYlGn_r", aspect="auto", vmin=vmin, vmax=vmax)
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                val = grid[i, j]
                if np.isnan(val):
                    continue
                ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=8,
                        color="white" if val >= mid else "black")
        ax.set_xticks(range(len(FREQ_ORDER)))
        ax.set_xticklabels(FREQ_ORDER)
        ax.set_xlabel("Rebalance Frequency")
        if k == 0:
            ax.set_yticks(range(len(RISK_ORDER)))
            ax.set_yticklabels(RISK_ORDER)
            ax.set_ylabel("Risk Budget")
        ax.set_title(PANEL_LABELS.get(strategy, strategy), fontweight="bold")

    cbar = fig.colorbar(im, ax=axes, fraction=0.02, pad=0.01)
    cbar.set_label("Full-Sample Max Drawdown Magnitude (%)")
    fig.suptitle(f"Full-Sample Maximum Drawdown Heatmap ({TC_LABEL.replace(' Transaction Cost', '')} Transaction Cost)",
                 fontweight="bold")
    return fig
