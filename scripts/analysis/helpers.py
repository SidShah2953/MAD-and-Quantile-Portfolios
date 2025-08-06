import os
from dotenv import load_dotenv
load_dotenv()


def get_report(portfolio, parameters):
    po = portfolio(freq=parameters['freq'], max_alloc=parameters['max_alloc'])
    stats_df = po.calculate_performance(parameters['max_risk'])

    for col in stats_df.columns:
        if col == 'Sharpe':
            stats_df[col] = stats_df[col].round(4)
        if col == 'PV':
            stats_df[col] = stats_df[col].round(2)
        else:
            stats_df[col] = (stats_df[col] * 100).round(2)

    weights_df = po.weights
    for col in weights_df.columns:
        weights_df[col] = (weights_df[col] * 100).round(2)
    weights_df.loc[f"{os.getenv('START_YEAR')}-01-01"] = len(weights_df.columns) * [0]
    weights_df.loc[f"{int(os.getenv('END_YEAR')) + 1}-01-01"] = len(weights_df.columns) * [0]
    weights_df = weights_df.sort_index()

    return weights_df, stats_df