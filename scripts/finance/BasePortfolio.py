import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from scipy.optimize import minimize

from scripts.finance.helpers import get_trading_days, max_drawdown
from scripts.data.processing import add_period_column

import os
from dotenv import load_dotenv
load_dotenv()


class BasePortfolio(ABC):
    def __init__(self, freq, max_alloc=None, use_index_etf=False):
        """
        Initialize base portfolio class
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
        self.data = self.data.set_index('period')

        self.weights = pd.DataFrame(index=self.data.columns)
        self.periods = list(sorted(self.data.index.unique()))
        self.period_length = get_trading_days(freq)

        self.max_alloc = os.getenv('MAX_ALLOC') if max_alloc is None else max_alloc
        self.weights = pd.DataFrame(columns=self.data.columns)

        self.performance = {
            'Return': {},
            'Volatility': {},
            'MAD': {},
            'IQR': {},
            'Sharpe': {},
            'Sharpe_MAD': {},
            'Sharpe_IQR': {},
            'RAR_Vol': {},
            'RAR_MAD': {},
            'RAR_IQR': {},
            'MDD': {},
        }

    def _load_returns(self, period):
        """
        Load ETF returns from CSV files
        """
        return self.data[self.data.index == period].copy()


    def _get_optimization_params(self, based_on):
        """
        Get common optimization parameters used by child classes
        """
        R = self._load_returns(based_on).to_numpy()
        mu = np.mean(R, axis=0)
        n_assets = len(self.etfs)
        
        if 'CSH' in self.etfs:
            bounds = [(0, self.max_alloc)] * (n_assets - 1) + [(0, 1)]
        else:
            bounds = [(0, self.max_alloc)] * n_assets
            
        initial_weights = np.zeros(n_assets)
        
        return R, mu, n_assets, bounds, initial_weights


    def _optimize_weights(self, based_on, max_risk, risk_fn, objective_fn=None):
        """
        Template method for portfolio optimization
        """
        _, mu, _, bounds, initial_weights = self._get_optimization_params(based_on)
        
        if objective_fn is None:
            objective_fn = lambda w: -np.dot(w, mu)
            
        constraints = ({
            'type': 'eq',
            'fun': lambda w: np.sum(w) - 1
        },
        {
            'type': 'ineq',
            'fun': lambda w: max_risk - risk_fn(w)
        })
        
        result = minimize(objective_fn,
                        initial_weights,
                        method='SLSQP',
                        bounds=bounds,
                        constraints=constraints)
        
        if result.success:
            weights = pd.DataFrame(dict(zip(
                                self.etfs,
                                list(map(lambda x: [x], result.x))
                            )))
            return weights
        else:
            raise ValueError("Optimization did not converge.")


    @abstractmethod
    def _calculate_weights(self, based_on, max_risk):
        """
        Abstract method to be implemented by child classes
        """
        pass


    def calculate_performance(self, max_risk):
        """
        Calculate portfolio weights and returns for each period
        """
        self.performance['Return'][self.periods[0]] = 0
        self.performance['Volatility'][self.periods[0]] = 0
        self.performance['MAD'][self.periods[0]] = 0
        self.performance['IQR'][self.periods[0]] = 0
        self.performance['Sharpe'][self.periods[0]] = np.nan
        self.performance['Sharpe_MAD'][self.periods[0]] = np.nan
        self.performance['Sharpe_IQR'][self.periods[0]] = np.nan
        self.performance['RAR_Vol'][self.periods[0]] = np.nan
        self.performance['RAR_MAD'][self.periods[0]] = np.nan
        self.performance['RAR_IQR'][self.periods[0]] = np.nan
        self.performance['MDD'][self.periods[0]] = np.nan

        for i in range(1, len(self.periods)):
            current_period = self.periods[i]
            previous_period = self.periods[i - 1]

            weights = self._calculate_weights(based_on=previous_period, max_risk=max_risk).values[0]
            self.weights.loc[current_period, :] = weights
            current_returns = self._load_returns(current_period).values
            portfolio_return = current_returns @ weights

            # Calculate period return
            self.performance['Return'][current_period] = np.prod(portfolio_return + 1) - 1
            
            # Calculate annualized volatility from daily returns in the period
            self.performance['Volatility'][current_period] = np.std(portfolio_return) * np.sqrt(get_trading_days('1y'))
            
            # Calculate annualized MAD
            mu = np.mean(portfolio_return)
            self.performance['MAD'][current_period] = np.mean(np.abs(portfolio_return - mu)) * np.sqrt(get_trading_days('1y'))
            
            # Calculate annualized IQR
            q75, q25 = np.percentile(portfolio_return, [75, 25])
            self.performance['IQR'][current_period] = (q75 - q25) * np.sqrt(get_trading_days('1y'))
            
            # Calculate annualized return for Sharpe ratios
            annualized_return = (1 + self.performance['Return'][current_period]) ** (get_trading_days('1y') / self.period_length) - 1
            
            # Calculate Sharpe ratio with volatility
            self.performance['Sharpe'][current_period] = annualized_return / self.performance['Volatility'][current_period] if self.performance['Volatility'][current_period] != 0 else np.nan
            
            # Calculate Sharpe ratio with MAD
            self.performance['Sharpe_MAD'][current_period] = annualized_return / self.performance['MAD'][current_period] if self.performance['MAD'][current_period] != 0 else np.nan
            
            # Calculate Sharpe ratio with IQR
            self.performance['Sharpe_IQR'][current_period] = annualized_return / self.performance['IQR'][current_period] if self.performance['IQR'][current_period] != 0 else np.nan
            
            # Calculate period-level risk-adjusted returns (no annualization)
            period_return = self.performance['Return'][current_period]
            period_volatility = np.std(portfolio_return)
            period_mad = np.mean(np.abs(portfolio_return - mu))
            period_iqr = (q75 - q25)
            
            self.performance['RAR_Vol'][current_period] = period_return / period_volatility if period_volatility != 0 else np.nan
            self.performance['RAR_MAD'][current_period] = period_return / period_mad if period_mad != 0 else np.nan
            self.performance['RAR_IQR'][current_period] = period_return / period_iqr if period_iqr != 0 else np.nan
            
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