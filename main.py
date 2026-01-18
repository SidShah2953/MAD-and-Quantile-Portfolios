import os
import pandas as pd
import numpy as np
import argparse

from dotenv import load_dotenv

from alive_progress import alive_bar

from scripts.analysis.helpers import get_report
from scripts.finance.Portfolios import BuyAndHold
from scripts.finance.Portfolios import StdDevPortfolio, MADPortfolio, IQRPortfolio

initial_value = 100
transaction_cost = 0  # 1% transaction cost

# Load environment variables from .env for repeatable runs.
load_dotenv()

_max_alloc = os.getenv('MAX_ALLOC')
if _max_alloc is None or _max_alloc.strip() == "":
    raise RuntimeError("MAX_ALLOC is not set. Define it in .env (e.g., MAX_ALLOC=0.25).")
MAX_ALLOC = float(_max_alloc)

freqs = [
    '1mo',
    '3mo',
    '6mo',
    '1y'
]
portfolios = {
    'S&P BnH': BuyAndHold,
    'Volatility': StdDevPortfolio,
    'MAD': MADPortfolio,
    'IQR': IQRPortfolio,
    '95%': lambda **kwargs: IQRPortfolio(trim=0.05, **kwargs),
}
def generate_reports(max_risk, transaction_cost=transaction_cost, generate_figures: bool = False):
    output_dir = f'./Output/{transaction_cost * 10000:.0f} bps Transaction Cost'
    os.makedirs(output_dir, exist_ok=True)
    output_dir = f'{output_dir}/{max_risk:.2%}'
    os.makedirs(output_dir, exist_ok=True)

    plt = None
    if generate_figures:
        import matplotlib.pyplot as plt  # type: ignore

    progress_bar = alive_bar(
        len(freqs) * len(portfolios),
        title=f'Generating Reports for Max Risk: {max_risk:.2%}',
        force_tty=True
        )
    reports = {}
    
    with progress_bar as bar:
        for freq in freqs:
            os.makedirs(f'{output_dir}/{freq}', exist_ok=True)
            os.makedirs(f'{output_dir}/{freq}/Metrics', exist_ok=True)
            os.makedirs(f'{output_dir}/{freq}/Weights', exist_ok=True)
            all_stats = {}
            all_stats_raw = {}
            all_weights = {}

            # Collect all portfolios
            for name, portfolio in portfolios.items():
                weights, stats, stats_raw = get_report(
                    portfolio, parameters={
                        'freq': freq,
                        'max_risk': max_risk,
                        'max_alloc': MAX_ALLOC
                        }
                    )
                if name == 'S&P BnH' or name == 'Equal':
                    pass
                else:
                    all_weights[name] = weights
                weights.to_excel(f'{output_dir}/{freq}/Weights/{name}.xlsx', index=True)
                all_weights[name] = weights
                all_stats[name] = stats
                # Preserve unrounded/raw stats for any calculations that require exact compounding.
                all_stats_raw[name] = stats_raw
                stats_used = list(stats.columns)
                bar()

            # Collect all metrics & Plot them
            metric_labels = {
                'Return': 'Return (%)',
                'Volatility': 'Volatility (%)',
                'MAD': 'Mean Absolute Deviation (%)',
                'IQR': 'Interquartile Range (%)',
                'Sharpe': 'Sharpe Ratio (Vol)',
                'Sharpe_MAD': 'Sharpe Ratio (MAD)',
                'Sharpe_IQR': 'Sharpe Ratio (IQR)',
                'RAR_Vol': 'Risk-Adjusted Return (Vol)',
                'RAR_MAD': 'Risk-Adjusted Return (MAD)',
                'RAR_IQR': 'Risk-Adjusted Return (IQR)',
                'MDD': 'Maximum Drawdown (%)',
                'PV': 'Portfolio Value ($)'
            }
            
            for stat in stats_used:
                stat_graph_df = pd.concat([
                                    all_stats[name][[stat]].rename(columns={stat: name})
                                    for name in portfolios.keys()
                                ], axis=1)
                stat_graph_df.to_excel(f'{output_dir}/{freq}/Metrics/{stat}.xlsx', index=True)
                
                if generate_figures:
                    ylabel = metric_labels.get(stat, stat)

                    if stat == 'PV':
                        stat_graph_df.plot(kind='line', figsize=(18, 8))
                        plt.ylabel(ylabel)
                        plt.xlabel('Period')
                    else:
                        stat_graph_df.plot(kind='bar', figsize=(18, 8))
                        plt.ylabel(ylabel)
                        plt.xlabel('Period')
                    plt.xticks(rotation=45, ha='right')
                    plt.title(f"{metric_labels.get(stat, stat)} Comparison (Rebalanced {freq})")
                    plt.legend(loc='best')
                    plt.grid(True, alpha=0.3)
                    plt.savefig(f'{output_dir}/{freq}/Metrics/{stat}.png', bbox_inches='tight', dpi=150)
                    plt.close()

            # Analysis on period change of weights
            # NOTE: weights_df includes two synthetic anchor rows (all zeros) for plotting convenience.
            # We must drop them before computing turnover / transaction costs, otherwise we create
            # artificial 100% turnover at the anchor boundaries (notably contaminating S&P BnH).
            anchor_dt = pd.to_datetime(os.getenv('INVEST_START_DATE', '2000-01-01'))
            anchor_label = anchor_dt.strftime('%Y-%m-%d')
            if anchor_label in all_weights[list(all_weights.keys())[0]].index:
                # Match get_report() behavior where we shift the anchor by one day if it collides.
                anchor_label = (anchor_dt - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            end_anchor_label = f"{int(os.getenv('END_YEAR')) + 1}-01-01"

            weights_for_cost = {
                name: w.drop(index=[i for i in [anchor_label, end_anchor_label] if i in w.index])
                for name, w in all_weights.items()
            }

            weight_comp = {
                'period': weights_for_cost[list(weights_for_cost.keys())[0]].index[1:]
            }
            for name in weights_for_cost.keys():
                # Turnover proxy used for transaction costs.
                # We charge transaction_cost per trade (one-way) on non-cash assets.
                # If a cash sleeve exists (CSH), the cash leg is not charged, so
                # moving into/out of cash is one-way, while asset-to-asset reallocations
                # still incur both a sell and a buy.
                weights_df = weights_for_cost[name] / 100
                non_cash_cols = [c for c in weights_df.columns if c != 'CSH']
                turnover = weights_df[non_cash_cols].diff().abs().sum(axis=1).iloc[1:]
                weight_comp[name] = turnover.to_numpy()

            weight_comp = pd.DataFrame.from_dict(weight_comp).set_index('period')
            weight_comp.to_excel(f'{output_dir}/{freq}/Weights/Comparison.xlsx')
            if generate_figures:
                weight_comp.drop('S&P BnH', axis=1).plot(kind='bar', figsize=(18, 8))
                plt.title('Sum of Absolute Weight Changes by Period')
                plt.ylabel('Total Weight Change (fraction)')
                plt.xlabel('Period')
                plt.xticks(rotation=45, ha='right')
                plt.legend(loc='best')
                plt.grid(True, alpha=0.3)
                plt.savefig(f'{output_dir}/{freq}/Weights/Comparison.png', bbox_inches='tight', dpi=150)
                plt.close()

            # Transaction Cost Analysis
            collector = []
            for portfolio in weight_comp.columns:
                pv = initial_value
                df = {
                    'period': [],
                    (portfolio, 'Invested'): [],
                    (portfolio, 'Transaction Cost'): [],
                    (portfolio, 'Net Invested'): [],
                }

                # Use raw (decimal) holding-period returns to avoid rounding drift.
                returns = all_stats_raw[portfolio]['Return']
                periods = list(returns.index)
                weight_change = weight_comp[portfolio]

                for i in range(len(periods)):
                    df['period'].append(periods[i])
                    
                    # Transaction cost incurred at the start of period (when rebalancing)
                    if periods[i] in weight_change.index:
                        # By construction, the buy-and-hold benchmark does not rebalance, so turnover is zero.
                        # Guard against any residual numerical noise.
                        if portfolio == 'S&P BnH':
                            cost = 0
                        else:
                            cost = weight_change[periods[i]] * pv * transaction_cost
                        df[(portfolio, 'Transaction Cost')].append(cost)
                        pv -= cost
                    else:
                        # No rebalancing at first period
                        df[(portfolio, 'Transaction Cost')].append(0)
                    
                    df[(portfolio, 'Invested')].append(pv)
                    
                    # Apply return from this period (after transaction costs)
                    pv *= (1 + returns[periods[i]])
                    
                    df[(portfolio, 'Net Invested')].append(pv)
                
                df = pd.DataFrame.from_dict(df).set_index('period')
                collector.append(df)

            collector = pd.concat(collector, axis=1)
            collector.columns = pd.MultiIndex.from_tuples(collector.columns)
            collector.to_excel(f'{output_dir}/{freq}/Transaction Cost.xlsx')

            temp = collector[[(portfolio, 'Net Invested') for portfolio in weight_comp.columns]]
            temp.columns = [portfolio for portfolio in weight_comp.columns]
            # Always export the total PV chart.
            if plt is None:
                import matplotlib.pyplot as plt  # type: ignore

            temp.plot(kind='line', figsize=(18, 8), linewidth=2)
            plt.title('Portfolio Value After Transaction Costs')
            plt.ylabel('Portfolio Value ($)')
            plt.xlabel('Period')
            plt.legend(loc='best')
            plt.grid(True, alpha=0.3)
            plt.savefig(
                f'{output_dir}/{freq}/Portfolio Value with Transaction Costs.png',
                bbox_inches='tight',
                dpi=150
            )
            plt.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run portfolio backtests and export output files.')
    parser.add_argument(
        '--generate-figures',
        action='store_true',
        help='Also export PNG figures alongside the raw XLSX output files (default: off).'
    )
    args = parser.parse_args()

    transaction_costs = [0, 0.01 / 100, 0.02 / 100]  # Different transaction costs to analyze
    risks = [0.05, 0.10, 0.15]
    for transaction_cost in transaction_costs:
        print(f'Assuming transaction cost: {transaction_cost:.2%}')
        for max_risk in risks:
            generate_reports(max_risk=max_risk, transaction_cost=transaction_cost, generate_figures=args.generate_figures)
        print()