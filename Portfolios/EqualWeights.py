import numpy as np
import pandas as pd

from Portfolios.helpers import get_trading_days, add_period_column, max_drawdown

import os
from dotenv import load_dotenv
load_dotenv()


class EqWeightPortfolio:
    def __init__(self, freq, max_alloc=None, use_index_etf=False):
        """
        Initialize optimizer with ETF price files
        """
        if use_index_etf:
            self.etfs = [os.getenv('INDEX_ETF')]
        else:
            self.etfs = os.getenv('ETF_LIST').split(',')
            use_cash = os.getenv('USE_CASH')
            if use_cash:
                self.etfs += ['CSH']

        self.data = pd.read_csv(os.getenv('COMBINED_DATA_FILE'))
        self.data = add_period_column(self.data, freq=freq)
        self.data = self.data[['period'] + self.etfs]
        self.grouped_data = self.data.groupby('period').apply(lambda period_data:
                    (period_data.iloc[:, 1:] + 1).prod() - 1
                )
        self.data = self.data.set_index('period')
        self.weights = pd.DataFrame(index=self.data.columns)
        self.periods = list(sorted(self.data.index.unique()))
        self.period_length = get_trading_days(freq)

        self.max_alloc = os.getenv('MAX_ALLOC') if max_alloc is None else max_alloc
        self.weights = pd.DataFrame(columns=self.data.columns)

        self.performance = {
            'Return': {},
            'Volatility': {},
            'Sharpe': {},
            'MDD': {},
        }


    def _load_returns(self, period):
        """
        Load ETF returns from CSV files
        :return: DataFrame of ETF returns
        """
        return self.data[self.data.index == period].copy()
    

    def _calculate_weights(self, based_on, max_risk):
        """
        Optimize portfolio weights with dynamic risk adjustment
        """
        invest_in = len(self.etfs)
        weights = [[1 / invest_in]] * invest_in
        weights = pd.DataFrame(dict(zip(
                            self.etfs,
                            weights
                        )))
        return weights


    def calculate_performance(self, max_risk):
        """
        Calculate portfolio weights and returns for each period

        :param max_risk: Maximum acceptable risk for portfolio optimization
        :return: DataFrame of portfolio weights and returns
        """
        self.performance['Return'][self.periods[0]] = 0
        self.performance['Volatility'][self.periods[0]] = 0
        self.performance['Sharpe'][self.periods[0]] = np.nan
        self.performance['MDD'][self.periods[0]] = np.nan

        for i in range(1, len(self.periods)):
            current_period = self.periods[i]
            previous_period = self.periods[i - 1]

            # Calculate weights based on previous period's data
            weights = self._calculate_weights(based_on=previous_period, max_risk=max_risk) \
                            .values[0]
            self.weights.loc[current_period, :] = weights
            current_returns = self._load_returns(current_period).values
            portfolio_return = current_returns @ weights

            self.performance['Return'][current_period] = np.prod(portfolio_return + 1) - 1
            self.performance['Volatility'][current_period] = np.std(portfolio_return) * np.sqrt(self.period_length)
            self.performance['Sharpe'][current_period] = self.performance['Return'][current_period] / self.performance['Volatility'][current_period]
            self.performance['MDD'][current_period] = max_drawdown(portfolio_return)

        temp = []
        for metric in self.performance.keys():
            temp.append(pd.DataFrame({
                'period': self.performance[metric].keys(),
                metric: self.performance[metric].values(),
            }).set_index('period'))

        self.performance = pd.concat(temp, axis=1)
        self.performance['PV'] = np.cumprod(self.performance['Return'] + 1) * 100

        return self.performance
