import os
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize
from dotenv import load_dotenv

class PortfolioOptimizer:
    def __init__(self, etfs, target_year, input_path):
        """
        Initialize optimizer with ETF price files
        :param etfs: List of ETF symbols
        :param target_year: Target year for optimization
        :param input_path: Path to data directory
        """
        self.etfs = etfs
        self.year = target_year
        self.input_path = input_path
        self.returns = self._load_returns()


    def _load_returns(self):
        """
        Load ETF returns from CSV files
        :return: DataFrame of ETF returns
        """
        returns_df = pd.read_csv(f'{self.input_path}/{self.year - 1}.csv')
        
        # Validate ETF presence and convert to returns
        returns = {}
        for etf in self.etfs:
            if etf not in returns_df.columns:
                raise ValueError(f"ETF {etf} not found in returns data")
            
            # Convert price series to returns
            returns[etf] = returns_df[etf].pct_change().dropna()
        
        return pd.DataFrame(returns)
    

    def calculate_portfolio(self, max_risk):
        """
        Optimize portfolio weights with a risk constraint
        
        Parameters:
        - returns: DataFrame of daily returns
        - max_risk: Maximum allowed portfolio risk (annualized volatility)
        
        Returns:
        - Optimized portfolio weights
        """
        # Mean returns
        mean_returns = self.returns.mean()
        
        # Number of assets
        n_assets = len(mean_returns)
        
        # Objective function (maximize return)
        def objective(weights):
            return -np.dot(mean_returns, weights)
        
        # Risk constraint function (annualized volatility)
        def risk_constraint(weights):
            portfolio_returns = self.returns.dot(weights)
            portfolio_volatility = portfolio_returns.std() * np.sqrt(252)
            return max_risk - portfolio_volatility
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},  # weights sum to 1
            {'type': 'ineq', 'fun': risk_constraint}  # risk constraint
        ]
        
        # Bounds (no short selling)
        bounds = tuple((0, 1) for _ in range(n_assets))
        
        # Initial guess (equal weights)
        initial_weights = np.array([1/n_assets] * n_assets)
        
        # Optimize
        result = minimize(
            objective, 
            initial_weights, 
            method='SLSQP', 
            bounds=bounds, 
            constraints=constraints
        )
        
        # Create weight DataFrame
        weights_df = pd.DataFrame(
            result.x, 
            index=self.returns.columns, 
            columns=['Portfolio Weight']
        )
        
        return weights_df


def main():
    load_dotenv()
    
    # Load ETFs and input path from environment variables
    etfs = os.getenv('ETF_LIST')
    if not etfs:
        raise ValueError("ETF_LIST environment variable not found")
    etfs = etfs.split(',')
    
    input_path = os.getenv('YEARLY_DATA_DIRECTORY')
    if not input_path:
        raise ValueError("YEARLY_DATA_DIRECTORY environment variable not found")
    
    po = PortfolioOptimizer(etfs, target_year=2000, input_path=input_path)
    
    # Set maximum risk (e.g., 15% annualized volatility)
    max_risk = 0.15
    
    # Optimize portfolio
    portfolio_weights = po.calculate_portfolio(max_risk)
    
    print("Optimized Portfolio Weights:")
    print(portfolio_weights)


if __name__ == '__main__':
    main()