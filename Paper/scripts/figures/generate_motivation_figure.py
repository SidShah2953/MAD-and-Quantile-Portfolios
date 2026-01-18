"""Paper motivation figure: semi-annual outlier inflation in volatility.

Reads Data/combined.csv, pools daily sector-ETF returns within each calendar
half-year (H1 = Jan--Jun, H2 = Jul--Dec), and plots a modified box-and-whisker
showing how standard deviation estimates can be inflated by outliers.

Output: figures/motivation_semiannual_outlier_inflation.png
"""
from __future__ import annotations

if __package__ is None or __package__ == "":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from Paper.scripts.utils.figure_helpers import (
    load_combined_data,
    get_sector_etf_columns,
    save_figure,
)


def compute_semiannual_stats(returns_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pool sector ETF returns by calendar half-year and compute summary statistics.
    
    Args:
        returns_df: DataFrame with daily returns, index=Date, columns=ETFs
        
    Returns:
        DataFrame with one row per half-year containing:
        - halfyear: period label (e.g., '2008H1', '2008H2')
        - mean, q1, median, q3, iqr
        - std_all, std_trimmed (after IQR-based outlier removal)
        - whisker_low, whisker_high (non-outlier extrema)
        - outliers: list of outlier values
    """
    sector_cols = get_sector_etf_columns(returns_df)
    df = returns_df[sector_cols].copy()
    
    # Add half-year period label (H1 = Jan-Jun, H2 = Jul-Dec)
    df['halfyear'] = df.index.year.astype(str) + 'H' + ((df.index.month - 1) // 6 + 1).astype(str)
    
    results = []
    for halfyear, group in df.groupby('halfyear'):
        # Pool all returns across all sector ETFs in this half-year
        pooled = group[sector_cols].values.flatten()
        pooled = pooled[~np.isnan(pooled)]
        
        if len(pooled) == 0:
            continue
            
        # Compute basic statistics
        q1 = np.percentile(pooled, 25)
        median = np.median(pooled)
        q3 = np.percentile(pooled, 75)
        iqr = q3 - q1
        mean = np.mean(pooled)
        
        # Identify outliers using 1.5 × IQR rule
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr
        inliers_mask = (pooled >= lower_fence) & (pooled <= upper_fence)
        inliers = pooled[inliers_mask]
        outliers = pooled[~inliers_mask]
        
        # Compute standard deviations
        std_all = np.std(pooled, ddof=1)
        std_trimmed = np.std(inliers, ddof=1) if len(inliers) > 1 else std_all
        
        # Whiskers extend to non-outlier extrema
        whisker_low = pooled[inliers_mask].min() if len(inliers) > 0 else pooled.min()
        whisker_high = pooled[inliers_mask].max() if len(inliers) > 0 else pooled.max()
        
        results.append({
            'halfyear': str(halfyear),
            'mean': mean,
            'q1': q1,
            'median': median,
            'q3': q3,
            'iqr': iqr,
            'std_all': std_all,
            'std_trimmed': std_trimmed,
            'whisker_low': whisker_low,
            'whisker_high': whisker_high,
            'outliers': outliers.tolist(),
            'n_outliers': len(outliers),
        })
    
    return pd.DataFrame(results)


def plot_semiannual_outlier_inflation(stats_df: pd.DataFrame) -> plt.Figure:
    """
    Create a modified box-and-whisker plot showing outlier inflation.
    
    Args:
        stats_df: DataFrame from compute_quarterly_stats
        
    Returns:
        matplotlib Figure
    """
    n_periods = len(stats_df)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Plot each half-year period
    for i, row in stats_df.iterrows():
        x = i
        
        # Draw box (Q1 to Q3)
        box_height = row['q3'] - row['q1']
        box = plt.Rectangle(
            (x - 0.3, row['q1']),
            0.6,
            box_height,
            facecolor='lightblue',
            edgecolor='black',
            linewidth=1,
        )
        ax.add_patch(box)
        
        # Draw median line
        ax.plot([x - 0.3, x + 0.3], [row['median'], row['median']], 
                color='darkblue', linewidth=2)
        
        # Draw whiskers
        ax.plot([x, x], [row['q1'], row['whisker_low']], 
                color='black', linewidth=1)
        ax.plot([x, x], [row['q3'], row['whisker_high']], 
                color='black', linewidth=1)
        ax.plot([x - 0.15, x + 0.15], [row['whisker_low'], row['whisker_low']], 
                color='black', linewidth=1)
        ax.plot([x - 0.15, x + 0.15], [row['whisker_high'], row['whisker_high']], 
                color='black', linewidth=1)
        
        # Plot outliers
        if len(row['outliers']) > 0:
            ax.scatter([x] * len(row['outliers']), row['outliers'], 
                      alpha=0.3, s=10, color='gray', marker='o')
        
        # Plot mean
        ax.scatter([x], [row['mean']], color='red', s=20, marker='o', 
                  zorder=5, label='Mean' if i == 0 else '')
        
        # Overlay ±2σ bands centered on mean
        # Full sample
        ax.plot([x - 0.35, x + 0.35], 
               [row['mean'] + 2 * row['std_all']] * 2,
               color='orange', linewidth=1.5, linestyle='--', alpha=0.8,
               label='±2σ (all data)' if i == 0 else '')
        ax.plot([x - 0.35, x + 0.35], 
               [row['mean'] - 2 * row['std_all']] * 2,
               color='orange', linewidth=1.5, linestyle='--', alpha=0.8)
        
        # Trimmed sample
        ax.plot([x - 0.35, x + 0.35], 
               [row['mean'] + 2 * row['std_trimmed']] * 2,
               color='green', linewidth=1.5, linestyle=':', alpha=0.8,
               label='±2σ (trimmed)' if i == 0 else '')
        ax.plot([x - 0.35, x + 0.35], 
               [row['mean'] - 2 * row['std_trimmed']] * 2,
               color='green', linewidth=1.5, linestyle=':', alpha=0.8)
    
    # Configure axes
    ax.set_xticks(range(n_periods))
    ax.set_xticklabels(stats_df['halfyear'], rotation=45, ha='right')
    ax.set_xlabel('Half-Year Period')
    ax.set_ylabel('Daily Simple Return')
    ax.set_title('Six-Month Distributions of Sector ETF Returns: Outlier Inflation in Volatility Estimates')
    ax.grid(axis='y', alpha=0.3, linestyle=':')
    ax.legend(loc='upper left', framealpha=0.9)
    ax.axhline(0, color='black', linewidth=0.8, alpha=0.5)
    
    plt.tight_layout()
    return fig


def main() -> None:
    """Generate the motivation figure."""
    print("Loading data...")
    returns = load_combined_data()
    
    print("Computing half-year period statistics...")
    stats = compute_semiannual_stats(returns)
    
    print(f"Found {len(stats)} 6-month periods with data")
    print(f"Average outlier inflation: {(stats['std_all'] / stats['std_trimmed']).mean():.3f}x")
    
    print("Creating plot...")
    fig = plot_semiannual_outlier_inflation(stats)
    
    save_figure(fig, 'motivation_semiannual_outlier_inflation.png')


if __name__ == '__main__':
    main()
