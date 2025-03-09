import numpy as np
import pandas as pd
from scipy.optimize import minimize

import os
from dotenv import load_dotenv
load_dotenv()

class MeanAbsDevPortfolio:
    def __init__(self, etfs, target_year, input_path, max_alloc=None):
        """
        Initialize optimizer with ETF price files
        :param etfs: List of ETF symbols
        :param target_year: Target year for optimization
        :param input_path: Path to data directory
        """
        self.etfs = etfs
        self.year = target_year
        self.input_path = input_path
        self.past_returns = self._load_returns(past=True)
        self.max_alloc = os.getenv('MAX_ALLOC') if max_alloc is None else max_alloc


    def _load_returns(self, past=False):
        """
        Load ETF returns from CSV files
        :return: DataFrame of ETF returns
        """
        year = self.year - 1 if past else self.year
        returns_df = pd.read_csv(f'{self.input_path}/{year}.csv')
        
        # Validate ETF presence and convert to returns
        returns_dict = {}
        for etf in self.etfs:
            if etf not in returns_df.columns:
                raise ValueError(f"ETF {etf} not found in returns data")
            # Convert price series to returns
            returns_dict[etf] = returns_df[etf].dropna()
        
        return pd.DataFrame(returns_dict)
    

    def calculate_portfolio(self, max_risk):
        """
        Optimize portfolio weights with dynamic risk adjustment
        """
        max_risk = np.sqrt(2 / np.pi) * max_risk
        _, n_assets = self.past_returns.shape
        R = self.past_returns.to_numpy() 
        mu = np.mean(R, axis=0)
        
        # Compute Annual MAD risk
        def risk(weights):
            risk = np.mean(np.abs(R - mu), axis=0)
            risk = risk @ weights
            return risk * np.sqrt(250)
        
        # Objective function: maximize return (minimize negative return)
        def objective(weights):
            return - mu @ weights
        
        # Constraints
        constraints = ({
                            'type': 'eq',
                            'fun': lambda w: np.sum(w) - 1
                        },  # Weights sum to 1
                        {
                            'type': 'ineq',
                            'fun': lambda w: max_risk - risk(w)
                    })  # MAD risk constraint
        
        # Bounds for weights
        if 'CSH' in self.etfs:
            bounds = [(0, self.max_alloc)] * (n_assets - 1) + [(0, 1)]
        else: 
            bounds = [(0, self.max_alloc)] * (n_assets)
        
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
            self.weights = pd.DataFrame(dict(zip(
                                self.past_returns.columns, 
                                list(map(lambda x: [x], result.x))
                            )))
            return self.weights  # Optimized portfolio weights
        else:
            raise ValueError("Optimization did not converge.")
    

    def calculate_statistics(self):
        def max_drawdown(returns):
            cumulative_returns = (1 + returns).cumprod()
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdown = (cumulative_returns - running_max) / running_max
            return drawdown.min()
        
        returns = self._load_returns().to_numpy()
        portfolio_returns = returns @ self.weights.T
        annual_stats = {}

        if portfolio_returns.empty:
            raise ValueError("No returns")

        annual_stats['Annual Return'] = (1 + portfolio_returns).prod() - 1
        annual_stats['Volatility'] = portfolio_returns.std() * np.sqrt(252)
        annual_stats['Sharpe Ratio'] = annual_stats['Annual Return'] / annual_stats['Volatility'] \
                                        if annual_stats['Volatility'].item() > 0 \
                                        else np.nan
        annual_stats['Max Drawdown'] = max_drawdown(portfolio_returns)

        return pd.DataFrame(annual_stats)
