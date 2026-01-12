import os
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from alive_progress import alive_bar

from scripts.analysis.helpers import get_report
from scripts.finance.Portfolios import BuyAndHold
from scripts.finance.Portfolios import StdDevPortfolio, MADPortfolio, IQRPortfolio

initial_value = 100
transaction_cost = 1e-2  # 1% transaction cost
MAX_ALLOC = float(os.getenv('MAX_ALLOC'))

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


def generate_reports(max_risk, transaction_cost=transaction_cost):
    output_dir = f'./Output/{transaction_cost:.0%} Transaction Cost'
    os.makedirs(output_dir, exist_ok=True)
    output_dir = f'{output_dir}/{max_risk:.2%}'
    os.makedirs(output_dir, exist_ok=True)

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
            all_weights = {}

            # Collect all portfolios
            for name, portfolio in portfolios.items():
                weights, stats = get_report(
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
            weight_comp = {
                'period': all_weights[list(all_weights.keys())[0]].index[1:]
            }
            for name in all_weights.keys():
                weights = list(all_weights[name].values / 100)        
                period_var = []
                for i in range(1, len(weights)):
                    # Calculate sum of absolute weight changes
                    weight_change = np.sum(np.abs(weights[i] - weights[i - 1]))
                    period_var.append(weight_change)
                
                weight_comp[name] = np.array(period_var)

            weight_comp = pd.DataFrame.from_dict(weight_comp).set_index('period')
            weight_comp.to_excel(f'{output_dir}/{freq}/Weights/Comparison.xlsx')
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

                returns = all_stats[portfolio]['Return'] / 100
                periods = list(returns.index)
                weight_change = weight_comp[portfolio]

                for i in range(len(periods)):
                    df['period'].append(periods[i])
                    
                    # Transaction cost incurred at the start of period (when rebalancing)
                    if periods[i] in weight_change.index:
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
            temp.plot(kind='line', figsize=(18, 8), linewidth=2)
            plt.title('Portfolio Value After Transaction Costs')
            plt.ylabel('Portfolio Value ($)')
            plt.xlabel('Period')
            plt.legend(loc='best')
            plt.grid(True, alpha=0.3)
            plt.savefig(f'{output_dir}/{freq}/Portfolio Value with Transaction Costs.png',
                        bbox_inches='tight', dpi=150)
            plt.close()

if __name__ == '__main__':
    transaction_costs = [0, 0.01, 0.02]  # Different transaction costs to analyze
    risks = [0.05, 0.10, 0.15, 0.20]
    for transaction_cost in transaction_costs:
        print(f'Assuming transaction cost: {transaction_cost:.2%}')
        for max_risk in risks:
            generate_reports(max_risk=max_risk, transaction_cost=transaction_cost)
        print()