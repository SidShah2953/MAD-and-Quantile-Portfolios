"""
Generate transaction-cost drag figure.

Shows how terminal portfolio value changes as transaction cost rate increases
from 0 to 2 bps, testing robustness of frictionless results.

Output: figures/cost_drag_curves.png
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))

from figure_helpers import (
    load_transaction_cost_data,
    save_figure,
    STRATEGY_ORDER,
    STRATEGY_COLORS,
    STRATEGY_LABELS,
    FREQ_ORDER,
    RISK_ORDER,
    TC_ORDER,
)


def collect_terminal_net_pv() -> pd.DataFrame:
    """
    Collect terminal net PV across all transaction cost scenarios.
    
    Returns:
        DataFrame with columns: TC, Frequency, Risk, Strategy, Terminal_Net_PV
    """
    records = []
    
    representative_risk = "10.00%"  # Focus on one risk budget for clarity
    
    for tc_label in TC_ORDER:
        # Extract TC rate in bps for plotting (e.g. "1 bps Transaction Cost" -> 1)
        tc_rate = tc_label.split()[0]
        
        for freq in FREQ_ORDER:
            try:
                tc_df = load_transaction_cost_data(tc_label, representative_risk, freq)
                
                # Get terminal (last row) net invested value
                terminal = tc_df.dropna().tail(1).iloc[0]
                
                for strategy in STRATEGY_ORDER:
                    if (strategy, 'Net Invested') in tc_df.columns:
                        net_pv = float(terminal[(strategy, 'Net Invested')])
                        
                        records.append({
                            'TC_Rate_BPS': int(tc_rate),
                            'Frequency': freq,
                            'Strategy': strategy,
                            'Terminal_Net_PV': net_pv,
                        })
            except FileNotFoundError:
                continue
    
    return pd.DataFrame(records)


def plot_cost_drag_curves(risk_label: str = "10.00%") -> plt.Figure:
    """
    Plot terminal net PV vs transaction cost rate.
    
    Creates small multiples: one panel per rebalancing frequency.
    Within each panel, overlay strategies as separate lines.
    """
    df = collect_terminal_net_pv()
    
    if len(df) == 0:
        print("Warning: No transaction cost data found")
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, 'No transaction cost data available', 
               ha='center', va='center', transform=ax.transAxes)
        return fig
    
    # Figure 11: put all panels in one row and share y-scale.
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.2), sharey=True)

    # Common y-limits across panels for visual comparability.
    y_min = float(df['Terminal_Net_PV'].min())
    y_max = float(df['Terminal_Net_PV'].max())
    y_pad = 0.03 * (y_max - y_min) if y_max > y_min else 1.0
    y_lim = (y_min - y_pad, y_max + y_pad)
    
    for idx, freq in enumerate(FREQ_ORDER):
        ax = axes[idx]
        
        freq_data = df[df['Frequency'] == freq]
        
        if len(freq_data) == 0:
            ax.text(0.5, 0.5, f'No data for {freq}', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'Rebalance: {freq}', fontweight='bold')
            continue
        
        for strategy in STRATEGY_ORDER:
            strat_data = freq_data[freq_data['Strategy'] == strategy].sort_values('TC_Rate_BPS')

            if len(strat_data) == 0:
                continue

            label = STRATEGY_LABELS.get(strategy, strategy)
            color = STRATEGY_COLORS.get(strategy, 'black')

            ax.plot(
                strat_data['TC_Rate_BPS'],
                strat_data['Terminal_Net_PV'],
                marker='o',
                label=label,
                color=color,
                linewidth=2,
                markersize=6,
                alpha=0.9,
            )
        
        ax.set_title(f'Rebalance: {freq}', fontweight='bold')
        ax.set_xlabel('Transaction Cost (bps)')
        ax.set_ylabel('Terminal Net Portfolio Value ($)')
        ax.grid(alpha=0.3, linestyle=':')
        ax.set_xticks([0, 1, 2])
        ax.set_ylim(*y_lim)
        
        if idx == 0:
            ax.legend(loc='best', framealpha=0.9, fontsize=9)
    
    fig.suptitle(f'Transaction Cost Drag (Risk Budget = {risk_label})', 
                fontweight='bold', fontsize=13)
    fig.tight_layout()
    
    return fig


def main() -> None:
    """Generate the transaction cost drag figure."""
    print("Collecting transaction cost data...")
    fig = plot_cost_drag_curves()
    save_figure(fig, 'cost_drag_curves.png')


if __name__ == '__main__':
    main()
