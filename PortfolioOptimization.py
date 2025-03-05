import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def get_yearly_report(portfolio, max_risk):
    # Load ETFs and input path from environment variables
    etfs = os.getenv('ETF_LIST').split(',')
    use_cash = os.getenv('USE_CASH')
    if use_cash:
        etfs += ['CSH']
    
    input_path = os.getenv('YEARLY_DATA_DIRECTORY')

    start_year = int(os.getenv('START_YEAR')) + 1
    end_year = int(os.getenv("END_YEAR"))

    weights_collector = []
    stats_collector = []
    for year in range(start_year, end_year + 1):
        po = portfolio(etfs, target_year=year, input_path=input_path)
        weights = po.calculate_portfolio(max_risk)
        weights_df = weights.copy()
        weights_df['Year'] = [year]
        weights_collector.append(weights_df)

        stats = po.calculate_statistics()
        stats_df = stats.copy()
        stats_df['Year'] = [year]
        stats_collector.append(stats_df)
        
    weights_df = pd.concat(weights_collector)
    weights_df = weights_df[['Year'] + list(weights_df.columns)[:-1]]
    for col in weights_df.columns:
        if col == 'Year':
            continue
        weights_df[col] = (weights_df[col] * 100).round(2)
    weights_df = weights_df.reset_index().drop('index', axis=1)

    stats_df = pd.concat(stats_collector)
    stats_df = stats_df[['Year'] + list(stats_df.columns)[:-1]]
    for col in stats_df.columns:
        if col == 'Year':
            continue
        elif col == 'Sharpe Ratio':
            stats_df[col] = stats_df[col].round(4)
        else:
            stats_df[col] = (stats_df[col] * 100).round(2)
    stats_df = stats_df.reset_index().drop('index', axis=1)

    return weights_df, stats_df
