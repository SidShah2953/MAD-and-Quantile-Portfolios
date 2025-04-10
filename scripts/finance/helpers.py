import os
import pandas as pd
import numpy as np

from dotenv import load_dotenv
load_dotenv()


def get_trading_days(frequency):
    """
    Returns the number of trading days for different frequency periods

    :param frequency: Period frequency
    :return: Number of trading days in the period
    """
    trading_days_map = {
        '1d': 1,      # Daily
        '1wk': 5,     # Weekly (assuming 5 trading days per week)
        '1mo': 21,    # Monthly (assuming 21 trading days per month)
        '3mo': 63,    # Quarterly (21 * 3)
        '6mo': 125,   # Semi-annually (21 * 6)
        '1y': 250     # Yearly (assuming 250 trading days per year)
    }

    return trading_days_map.get(frequency, 0)


def calculate_portfolio_value(returns, initial=100):
    returns['PV'] = (np.cumprod(returns['returns'] + 1) - 1) * initial
    return returns


def max_drawdown(returns):
    cumulative_returns = (1 + returns).cumprod()
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdown = (cumulative_returns - running_max) / running_max
    return drawdown.min()


