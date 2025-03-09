import numpy as np
import pandas as pd

import os
from dotenv import load_dotenv
load_dotenv()

class BuyAndHold:
    def __init__(self, etfs, target_year, input_path, max_alloc=None):
        """
        Initialize optimizer with ETF price files
        :param etfs: List of ETF symbols
        :param target_year: Target year for optimization
        :param input_path: Path to data directory
        """
        self.etfs = ['^GSPC']
        self.year = target_year
        self.input_path = input_path
        self.past_returns = self._load_returns(past=True)


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
        invest_in = len(self.etfs) 
        weights = [[1 / invest_in]] * invest_in
            
        self.weights = pd.DataFrame(dict(zip(
                            self.past_returns.columns, 
                            weights)
                        ))
        return self.weights  # Optimized portfolio weights
    

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
