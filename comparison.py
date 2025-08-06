import os
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from scripts.analysis.helpers import get_report
from scripts.finance.Portfolios import BuyAndHold
from scripts.finance.Portfolios import StdDevPortfolio, MADPortfolio, IQRPortfolio

max_risk = 0.10
initial_value = 100
transaction_cost = 0.15 / 100

output_dir = './Output'
os.makedirs(output_dir, exist_ok=True)
output_dir = f'{output_dir}/{max_risk:.2%}'
os.makedirs(output_dir, exist_ok=True)

freqs = [
    # '1d',
    # '1wk',
    # '1mo',
    # '3mo',
    '6mo',
    '1y'
]
portfolios = {
    'S&P BnH': BuyAndHold,
    'Volatility': StdDevPortfolio,
    'MAD': MADPortfolio,
    'IQR': IQRPortfolio,
}


if __name__ == '__main__':
    reports = {}

    for freq in freqs:
        os.makedirs(f'{output_dir}/{freq}', exist_ok=True)
        os.makedirs(f'{output_dir}/{freq}/Metrics', exist_ok=True)
        os.makedirs(f'{output_dir}/{freq}/Weights', exist_ok=True)
        all_stats = {}
        all_weights = {}

        # Collect all portfolios
        for name, portfolio in portfolios.items():
            weights, stats = get_report(portfolio, freq=freq, max_risk=max_risk)
            if name == 'S&P BnH' or name == 'Equal':
                pass
            else:
                all_weights[name] = weights
            weights.to_excel(f'{output_dir}/{freq}/Weights/{name}.xlsx', index=True)

            all_weights[name] = weights

            all_stats[name] = stats
            stats_used = list(stats.columns)

        # Collect all metrics & Plot them
        for stat in stats_used:
            stat_graph_df = pd.concat([
                                all_stats[name][[stat]].rename(columns={stat: name})
                                for name in portfolios.keys()
                            ], axis=1)
            stat_graph_df.to_excel(f'{output_dir}/{freq}/Metrics/{stat}.xlsx', index=True)
            if stat == 'PV':
                stat_graph_df.plot(kind='line', figsize=(18, 8))
            else:
                stat_graph_df.plot(kind='bar', figsize=(18, 8))
            plt.xticks(rotation=90)
            plt.title(f"{stat} Comparison for all Portfolios (Rebalanced {freq})")
            plt.savefig(f'{output_dir}/{freq}/Metrics/{stat}.png', bbox_inches='tight')
            plt.close()

        # Analysis on yearly change of weights
        weight_comp = {
            'period': all_weights[list(all_weights.keys())[0]].index[1:]
        }
        for name in all_weights.keys():
            weights = list(all_weights[name].values / 100)        
            yearly_var = []
            for i in range(1, len(weights)):
                if name == 'S&P BnH' or name == 'Equal':
                    yearly_var.append(np.mean(np.abs(weights[i] - weights[i - 1])))
                else:
                    yearly_var.append(np.mean(np.abs(weights[i] - weights[i - 1])[:-1]))
            
            weight_comp[name] = np.array(yearly_var)

        weight_comp = pd.DataFrame.from_dict(weight_comp).set_index('period')
        weight_comp.to_excel(f'{output_dir}/{freq}/Weights/Comparison.xlsx')
        weight_comp.drop('S&P BnH', axis=1).plot(kind='bar', figsize=(18, 8))
        plt.title('Mean Weight Allocation Change')
        plt.savefig(f'{output_dir}/{freq}/Weights/Comparison.png', bbox_inches='tight')
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
            periods = list(returns.index) + [f"{int(os.getenv('END_YEAR')) + 1}-01-01"]
            if portfolio == 'S&P BnH' or portfolio == 'Equal':
                weight_change = weight_comp[portfolio] * 1
            else:
                weight_change = weight_comp[portfolio] * 9

            for i in range(1, len(periods)):
                pv *= (1 + returns[periods[i - 1]])
                df['period'].append(periods[i])
                df[(portfolio, 'Invested')].append(pv)
                
                cost = weight_change[periods[i]] * pv * transaction_cost
                df[(portfolio, 'Transaction Cost')].append(cost)
                pv -= cost
                df[(portfolio, 'Net Invested')].append(pv)
            
            df = pd.DataFrame.from_dict(df).set_index('period')
            collector.append(df)

        collector = pd.concat(collector, axis=1)
        collector.columns = pd.MultiIndex.from_tuples(collector.columns)
        collector.to_excel(f'{output_dir}/{freq}/Transaction Cost.xlsx')

        temp = collector[[(portfolio, 'Net Invested') for portfolio in weight_comp.columns]]
        temp.columns = [portfolio for portfolio in weight_comp.columns]
        temp.plot(kind='line', figsize=(18, 8))
        plt.title('Net Invested Amount Over Time')
        plt.grid(True)
        plt.savefig(f'{output_dir}/{freq}/Portfolio Value with Transaction Costs.png',
                    bbox_inches='tight')
        plt.close()