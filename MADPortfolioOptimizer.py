import numpy as np
import pandas as pd
from scipy.optimize import minimize


class MADPortfolioOptimizer:
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
        self.past_returns = self._load_past_returns()


    def _load_past_returns(self):
        """
        Load ETF returns from CSV files
        :return: DataFrame of ETF returns
        """
        returns_df = pd.read_csv(f'{self.input_path}/{self.year - 1}.csv')
        
        # Validate ETF presence and convert to returns
        returns_dict = {}
        for etf in self.etfs:
            if etf not in returns_df.columns:
                raise ValueError(f"ETF {etf} not found in returns data")
            # Convert price series to returns
            returns_dict[etf] = returns_df[etf].dropna()
        
        return pd.DataFrame(returns_dict)
    

    def _load_returns(self):
        """
        Load ETF returns from CSV files
        :return: DataFrame of ETF returns
        """
        returns_df = pd.read_csv(f'{self.input_path}/{self.year}.csv')
        
        # Validate ETF presence and convert to returns
        returns_dict = {}
        for etf in self.etfs:
            if etf not in returns_df.columns:
                raise ValueError(f"ETF {etf} not found in returns data")
            # Convert price series to returns
            returns_dict[etf] = returns_df[etf].dropna()
        
        return pd.DataFrame(returns_dict)
    

    def calculate_portfolio(self, max_risk, initial_risk=None):
        """
        Optimize portfolio weights with dynamic risk adjustment
        """
        mean_returns = self.past_returns.mean()
        n_assets = len(mean_returns)
        
        def objective(weights):
            portfolio_returns = self.past_returns.dot(weights)
            portfolio_volatility = portfolio_returns.std() * np.sqrt(252)
            portfolio_return = np.dot(mean_returns, weights)
            # Penalize risk above max_risk
            risk_penalty = max(0, portfolio_volatility - max_risk) * 100
            return -portfolio_return + risk_penalty
        
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # weights sum to 1
        ]
        
        bounds = tuple((0, 1) for _ in range(n_assets))
        
        # Try multiple initial points if first optimization fails
        initial_points = [
            np.array([1/n_assets] * n_assets),  # Equal weights
            np.random.dirichlet(np.ones(n_assets)),  # Random weights
            np.zeros(n_assets)]
        
        initial_points[-1][0] = 1  # Single asset
        
        best_result = None
        min_objective = float('inf')
        
        for initial_weights in initial_points:
            result = minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000}
            )
            
            if result.fun < min_objective:
                min_objective = result.fun
                best_result = result
        
        if best_result is None:
            raise ValueError("Optimization failed with all initial points")
            
        weights_df =  pd.DataFrame(
            best_result.x,
            index=self.past_returns.columns,
            columns=['Portfolio Weight']
        )
        self.weights = weights_df.to_dict()['Portfolio Weight']

        return weights_df
    
    def calculate_returns(self):
        returns = self._load_returns()
        total_return = 0
        for etf in self.etfs:
            etf_return = np.prod(returns[etf].values + 1)
            total_return += self.weights[etf] * etf_return
        
        return float(total_return) - 1