import pandas as pd
import numpy as np
from scipy.optimize import minimize
# from empyrical import max_drawdown

class MarkowitzPortfolioOptimizer:
    def __init__(self, etfs, risk_tolerance, input_path):
        """
        Initialize optimizer with ETF return files.
        :param etfs: List of ETF symbols
        :param risk_tolerance: Maximum acceptable volatility (e.g., 0.15 for 15%)
        :param input_path: Path to ETF returns data directory
        """
        self.etfs = etfs
        self.risk_tolerance = risk_tolerance
        self.input_path = input_path
        self.returns_df = self._load_returns()
        self.weights = None

    def _load_returns(self):
        """
        Load ETF return data from CSV files.
        :return: DataFrame of ETF returns
        """
        data = {}
        for etf in self.etfs:
            df = pd.read_csv(f'{self.input_path}/{etf}_weekly_return_detailed.csv', parse_dates=['Date'])
            df.set_index('Date', inplace=True)
            df.rename(columns={'Return': etf}, inplace=True)
            data[etf] = df[etf] / 100  # Convert percentage returns to decimal
        return pd.DataFrame(data).dropna()


    def optimize_portfolio(self):
        def objective_function(self, weights):
            """
            Objective function for optimization: maximize return with a risk constraint.
            :param weights: Portfolio weights
            :return: Negative portfolio return (since we maximize return)
            """
            portfolio_return, portfolio_volatility = self._portfolio_statistics(weights)
            return -portfolio_return  # Negative because we use `minimize()`
        
        def portfolio_statistics(self, weights):
            cov_matrix = self.returns_df.cov()
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(252)  # Annualized volatility
            return portfolio_volatility
        
        num_assets = len(self.etfs)
        initial_weights = np.ones(num_assets) / num_assets  # Equal weight start
        bounds = tuple((0, 0.25) for _ in range(num_assets))  # No shorting, no leverage
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
            {'type': 'ineq', 'fun': lambda x: self.risk_tolerance - portfolio_statistics(x)[1]}
        ]

        result = minimize(
            objective_function,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        if not result.success:
            raise ValueError("Optimization failed!")

        self.weights = pd.DataFrame({'ETF': self.etfs, 'Weight': result.x})
        return self.weights
