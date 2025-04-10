import numpy as np
import pandas as pd
from scipy.optimize import minimize

from Portfolios.helpers import get_trading_days, add_period_column, max_drawdown

import os
from dotenv import load_dotenv
load_dotenv()


class MarkowitzPortfolio:
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
        max_risk = max_risk * np.sqrt(1 / 250)

        R = self._load_returns(based_on).to_numpy()
        mu = np.mean(R, axis=0)
        cov_matrix = np.cov(R, rowvar=False)
        n_assets = len(self.etfs)
        
        # Compute Annualised portfolio risk
        def risk(weights):
            return np.sqrt(weights @ cov_matrix @ weights.T)
        
        # Objective function: maximize return (minimize negative return)
        def objective(weights):
            return -np.dot(weights, mu)
        
        # Constraints
        constraints = ({
                            'type': 'eq',
                            'fun': lambda w: np.sum(w) - 1
                        },  # Weights sum to 1
                        {
                            'type': 'ineq',
                            'fun': lambda w: max_risk - risk(w)
                    })
        
        # Bounds for weights
        if 'CSH' in self.etfs:
            bounds = [(0, self.max_alloc)] * (n_assets - 1) + [(0, 1)]
        else: 
            bounds = [(0, self.max_alloc)] * n_assets
        
        # Initial guess
        initial_weights = np.zeros(n_assets)
        
        # Optimization
        result = minimize(objective,
                          initial_weights,
                          method='SLSQP',
                          bounds=bounds,
                          constraints=constraints
                        )
        
        if result.success:
            weights = pd.DataFrame(dict(zip(
                                self.etfs,
                                list(map(lambda x: [x], result.x))
                            )))
            return weights
        else:
            raise ValueError("Optimization did not converge.")


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

        self.performance.loc[f"{int(os.getenv('END_YEAR')) + 1}-01-01"] = \
                [np.nan] * len(self.performance.columns)
        self.performance = self.performance.sort_index()
        self.performance['PV'] = self.performance['PV'].shift(1)
        self.performance = self.performance.iloc[1:]

        return self.performance
