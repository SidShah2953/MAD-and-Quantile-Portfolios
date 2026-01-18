"""
Generate no-look-ahead timeline schematic figure.

Shows the information timeline for the backtest: estimation window,
rebalance boundary, and holding window.

Output: figures/no_lookahead_timeline.png
"""
from __future__ import annotations

if __package__ is None or __package__ == "":
       import sys
       from pathlib import Path

       sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from Paper.scripts.utils.figure_helpers import save_figure


def plot_timeline() -> plt.Figure:
    """
    Create a schematic timeline showing the no-look-ahead design.
    """
    fig, ax = plt.subplots(figsize=(12, 4))
    
    # Define timeline positions
    y_center = 0.5
    
    # Period k-1 (estimation window)
    period_k1_start = 0
    period_k1_end = 3
    
    # Rebalance point
    rebalance = period_k1_end
    
    # Period k (holding window)
    period_k_start = period_k1_end
    period_k_end = 6
    
    # Draw boxes for periods
    # Period k-1
    box_k1 = FancyBboxPatch(
        (period_k1_start, y_center - 0.15),
        period_k1_end - period_k1_start,
        0.3,
        boxstyle="round,pad=0.02",
        edgecolor='#2ca02c',
        facecolor='#d4f1d4',
        linewidth=2
    )
    ax.add_patch(box_k1)
    
    # Period k
    box_k = FancyBboxPatch(
        (period_k_start, y_center - 0.15),
        period_k_end - period_k_start,
        0.3,
        boxstyle="round,pad=0.02",
        edgecolor='#1f77b4',
        facecolor='#d4e6f1',
        linewidth=2
    )
    ax.add_patch(box_k)
    
    # Labels for periods
    ax.text(period_k1_start + (period_k1_end - period_k1_start) / 2, y_center,
            'Period $k-1$\n(Estimation Window)',
            ha='center', va='center', fontsize=11, weight='bold')
    
    ax.text(period_k_start + (period_k_end - period_k_start) / 2, y_center,
            'Period $k$\n(Holding Window)',
            ha='center', va='center', fontsize=11, weight='bold')
    
    # Rebalance marker
    ax.plot([rebalance, rebalance], [y_center - 0.25, y_center + 0.25],
           'r--', linewidth=2, label='Rebalance')
    ax.text(rebalance, y_center + 0.35, 'Rebalance\n& Optimize',
           ha='center', va='bottom', fontsize=10, color='red', weight='bold')
    
    # Information flow annotations
    # Returns from k-1 used for estimation
    ax.annotate('', xy=(rebalance - 0.1, y_center - 0.4),
               xytext=(period_k1_start + 0.5, y_center - 0.4),
               arrowprops=dict(arrowstyle='->', lw=1.5, color='#2ca02c'))
    ax.text((period_k1_start + rebalance) / 2, y_center - 0.5,
           'Estimate $\\hat{\\mu}$, $\\hat{\\Sigma}$',
           ha='center', fontsize=9, style='italic', color='#2ca02c')
    
    # Weights applied to period k
    ax.annotate('', xy=(period_k_end - 0.5, y_center + 0.4),
               xytext=(rebalance + 0.1, y_center + 0.4),
               arrowprops=dict(arrowstyle='->', lw=1.5, color='#1f77b4'))
    ax.text((rebalance + period_k_end) / 2, y_center + 0.5,
           'Apply weights $w_k$',
           ha='center', fontsize=9, style='italic', color='#1f77b4')
    
    # Timeline arrow
    ax.annotate('', xy=(period_k_end + 0.3, y_center - 0.6),
               xytext=(period_k1_start - 0.3, y_center - 0.6),
               arrowprops=dict(arrowstyle='->', lw=2, color='black'))
    ax.text(period_k1_start - 0.3, y_center - 0.7, 'Time',
           ha='left', fontsize=10)
    
    # Set axis limits and remove axes
    ax.set_xlim(-0.5, period_k_end + 0.5)
    ax.set_ylim(-0.8, 1.0)
    ax.axis('off')
    
    plt.tight_layout()
    return fig


def main() -> None:
    """Generate the no-look-ahead timeline figure."""
    print("Creating no-look-ahead timeline schematic...")
    fig = plot_timeline()
    save_figure(fig, 'no_lookahead_timeline.png')


if __name__ == '__main__':
    main()
