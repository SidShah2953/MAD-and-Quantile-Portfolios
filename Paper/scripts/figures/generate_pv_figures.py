"""
Generate PV-related figures: time-series curves and heatmaps.

Produces:
- figures/pv_curves_zero_cost.png: Portfolio value over time
- figures/heatmap_terminal_pv_zero_cost.png: Terminal PV heatmap
- figures/heatmap_mdd_zero_cost.png: Maximum drawdown heatmap
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))

from figure_helpers import (
    load_metric,
    save_figure,
    STRATEGY_ORDER,
    STRATEGY_COLORS,
    STRATEGY_LABELS,
    FREQ_ORDER,
    RISK_ORDER,
)


def plot_pv_curves(tc_label: str = "0 bps Transaction Cost") -> plt.Figure:
    """
    Plot portfolio value curves for representative risk budgets.
    
    Creates small multiples: one panel per rebalancing frequency.
    Within each panel, overlay strategies at a representative risk budget (10%).
    """
    representative_risk = "10.00%"
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, sharey=True)
    axes = axes.flatten()
    
    for idx, freq in enumerate(FREQ_ORDER):
        ax = axes[idx]
        
        try:
            pv_df = load_metric(tc_label, representative_risk, freq, "PV")
            
            for strategy in STRATEGY_ORDER:
                if strategy not in pv_df.columns:
                    continue
                    
                label = STRATEGY_LABELS.get(strategy, strategy)
                color = STRATEGY_COLORS.get(strategy, 'black')
                
                ax.plot(pv_df.index, pv_df[strategy], 
                       label=label, color=color, linewidth=1.5, alpha=0.9)
            
            ax.set_title(f'Rebalance: {freq}', fontweight='bold')
            ax.grid(alpha=0.3, linestyle=':')
            ax.set_ylabel('Portfolio Value ($)')
            
            if idx == 0:
                ax.legend(loc='upper left', framealpha=0.9, fontsize=8)
                
        except FileNotFoundError:
            ax.text(0.5, 0.5, f'No data for {freq}', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'Rebalance: {freq}', fontweight='bold')
    
    fig.suptitle(f'Portfolio Value Over Time ({tc_label}, Risk Budget = {representative_risk})', 
                fontweight='bold', fontsize=12)
    fig.tight_layout()
    
    return fig


def plot_terminal_pv_heatmap(tc_label: str = "0 bps Transaction Cost") -> plt.Figure:
    """
    Create heatmap of terminal portfolio values.
    
    Separate panel for each strategy; axes = (risk budget, rebalance frequency).
    """
    # Collect terminal PV values
    data = {strategy: [] for strategy in STRATEGY_ORDER}
    
    for freq in FREQ_ORDER:
        for risk in RISK_ORDER:
            try:
                pv_df = load_metric(tc_label, risk, freq, "PV")
                terminal = pv_df.dropna().tail(1).iloc[0]
                
                for strategy in STRATEGY_ORDER:
                    if strategy in terminal.index:
                        data[strategy].append({
                            'Frequency': freq,
                            'Risk': risk,
                            'Terminal_PV': float(terminal[strategy])
                        })
            except FileNotFoundError:
                continue
    
    # Create subplots
    n_strategies = len([s for s in STRATEGY_ORDER if len(data[s]) > 0])
    fig, axes = plt.subplots(1, n_strategies, figsize=(3.5 * n_strategies, 4), 
                            sharey=True)
    
    if n_strategies == 1:
        axes = [axes]
    
    strategy_idx = 0
    for strategy in STRATEGY_ORDER:
        if len(data[strategy]) == 0:
            continue
            
        ax = axes[strategy_idx]
        df = pd.DataFrame(data[strategy])
        
        # Pivot for heatmap
        pivot = df.pivot(index='Risk', columns='Frequency', values='Terminal_PV')
        pivot = pivot.reindex(index=RISK_ORDER, columns=FREQ_ORDER)
        
        # Plot heatmap
        im = ax.imshow(pivot.values, cmap='RdYlGn', aspect='auto', 
                      vmin=pivot.values.min(), vmax=pivot.values.max())
        
        # Add text annotations
        for i in range(len(RISK_ORDER)):
            for j in range(len(FREQ_ORDER)):
                val = pivot.iloc[i, j]
                if not np.isnan(val):
                    text = ax.text(j, i, f'{val:.0f}',
                                 ha='center', va='center', fontsize=8,
                                 color='white' if val < pivot.values.mean() else 'black')
        
        ax.set_xticks(range(len(FREQ_ORDER)))
        ax.set_xticklabels(FREQ_ORDER)
        ax.set_xlabel('Rebalance Frequency')
        
        if strategy_idx == 0:
            ax.set_yticks(range(len(RISK_ORDER)))
            ax.set_yticklabels(RISK_ORDER)
            ax.set_ylabel('Risk Budget')
        
        label = STRATEGY_LABELS.get(strategy, strategy)
        ax.set_title(label, fontweight='bold')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Terminal PV ($)', rotation=270, labelpad=15)
        
        strategy_idx += 1
    
    fig.suptitle(f'Terminal Portfolio Value Heatmap ({tc_label})', 
                fontweight='bold', fontsize=12)
    fig.tight_layout()
    
    return fig


def plot_mdd_heatmap(tc_label: str = "0 bps Transaction Cost") -> plt.Figure:
    """
    Create heatmap of maximum drawdown values.
    
    Same layout as terminal PV heatmap for direct comparison.
    """
    # Collect MDD values (reported as negative percentages)
    data = {strategy: [] for strategy in STRATEGY_ORDER}
    
    for freq in FREQ_ORDER:
        for risk in RISK_ORDER:
            try:
                mdd_df = load_metric(tc_label, risk, freq, "MDD")
                worst_mdd = mdd_df.min().to_dict()  # Most negative value
                
                for strategy in STRATEGY_ORDER:
                    if strategy in worst_mdd:
                        data[strategy].append({
                            'Frequency': freq,
                            'Risk': risk,
                            'MDD': float(worst_mdd[strategy])
                        })
            except FileNotFoundError:
                continue
    
    # Create subplots
    n_strategies = len([s for s in STRATEGY_ORDER if len(data[s]) > 0])
    fig, axes = plt.subplots(1, n_strategies, figsize=(3.5 * n_strategies, 4), 
                            sharey=True)
    
    if n_strategies == 1:
        axes = [axes]
    
    strategy_idx = 0
    for strategy in STRATEGY_ORDER:
        if len(data[strategy]) == 0:
            continue
            
        ax = axes[strategy_idx]
        df = pd.DataFrame(data[strategy])
        
        # Pivot for heatmap
        pivot = df.pivot(index='Risk', columns='Frequency', values='MDD')
        pivot = pivot.reindex(index=RISK_ORDER, columns=FREQ_ORDER)
        
        # Plot heatmap (reversed colormap: more negative = worse = red)
        im = ax.imshow(pivot.values, cmap='RdYlGn_r', aspect='auto')
        
        # Add text annotations
        for i in range(len(RISK_ORDER)):
            for j in range(len(FREQ_ORDER)):
                val = pivot.iloc[i, j]
                if not np.isnan(val):
                    text = ax.text(j, i, f'{val:.1f}',
                                 ha='center', va='center', fontsize=8,
                                 color='white' if val < -30 else 'black')
        
        ax.set_xticks(range(len(FREQ_ORDER)))
        ax.set_xticklabels(FREQ_ORDER)
        ax.set_xlabel('Rebalance Frequency')
        
        if strategy_idx == 0:
            ax.set_yticks(range(len(RISK_ORDER)))
            ax.set_yticklabels(RISK_ORDER)
            ax.set_ylabel('Risk Budget')
        
        label = STRATEGY_LABELS.get(strategy, strategy)
        ax.set_title(label, fontweight='bold')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Max Drawdown (%)', rotation=270, labelpad=15)
        
        strategy_idx += 1
    
    fig.suptitle(f'Maximum Drawdown Heatmap ({tc_label})', 
                fontweight='bold', fontsize=12)
    fig.tight_layout()
    
    return fig


def main() -> None:
    """Generate all PV-related figures."""
    print("Generating PV curves...")
    fig_pv = plot_pv_curves()
    save_figure(fig_pv, 'pv_curves_zero_cost.png')
    
    print("Generating terminal PV heatmap...")
    fig_hm_pv = plot_terminal_pv_heatmap()
    save_figure(fig_hm_pv, 'heatmap_terminal_pv_zero_cost.png')
    
    print("Generating MDD heatmap...")
    fig_hm_mdd = plot_mdd_heatmap()
    save_figure(fig_hm_mdd, 'heatmap_mdd_zero_cost.png')


if __name__ == '__main__':
    main()
