import os
import pandas as pd
from dotenv import load_dotenv
load_dotenv()


def get_report(portfolio, parameters):
    po = portfolio(freq=parameters['freq'], max_alloc=parameters['max_alloc'])
    stats_raw = po.calculate_performance(parameters['max_risk'])

    # Format a copy for export (percent units + rounding), but keep raw decimals
    # for any downstream calculations (e.g., transaction-cost compounding).
    stats_df = stats_raw.copy()

    for col in stats_df.columns:
        if col in ['Sharpe', 'Sharpe_MAD', 'Sharpe_IQR', 'RAR_Vol', 'RAR_MAD', 'RAR_IQR']:
            stats_df[col] = stats_df[col].round(4)
        elif col == 'PV':
            stats_df[col] = stats_df[col].round(2)
        else:
            stats_df[col] = (stats_df[col] * 100).round(2)

    weights_df = po.weights
    for col in weights_df.columns:
        weights_df[col] = weights_df[col] * 100

    # Add an anchor row at the common investment start date for plotting/export convenience.
    # Ensure we don't overwrite an existing period label (period labels are trading-day starts).
    anchor_dt = pd.to_datetime(os.getenv('INVEST_START_DATE', '2000-01-01'))
    anchor_label = anchor_dt.strftime('%Y-%m-%d')
    if anchor_label in weights_df.index:
        anchor_label = (anchor_dt - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    weights_df.loc[anchor_label] = len(weights_df.columns) * [0]

    weights_df.loc[f"{int(os.getenv('END_YEAR')) + 1}-01-01"] = len(weights_df.columns) * [0]
    weights_df = weights_df.sort_index()

    return weights_df, stats_df, stats_raw