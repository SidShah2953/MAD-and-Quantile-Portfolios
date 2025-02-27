import numpy as np
import pandas as pd
from scipy.optimize import minimize
import math


class MeanAbsDevPortfolio:
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
        """
        Optimize portfolio weights with dynamic risk adjustment
        """
        max_mad_risk = math.sqrt(2 / math.pi) * max_risk
        _, n_assets = self.past_returns.shape
        R = self.past_returns.to_numpy() 
        mu = np.mean(R, axis=0)
        
        # Compute MAD risk
        def risk(weights):
            risk = np.mean(np.abs(R - mu), axis=0)
            risk = risk @ weights
            return risk
        
        # Objective function: maximize return (minimize negative return)
        def objective(weights):
            pred_return = np.dot(weights, mu)
            return -pred_return
        
        # Constraints
        constraints = ({
                            'type': 'eq',
                            'fun': lambda w: np.sum(w) - 1
                        },  # Weights sum to 1
                        {
                            'type': 'ineq',
                            'fun': lambda w: max_mad_risk - risk(w)
                    })  # MAD risk constraint
        
        # Bounds for weights (each asset must be between 0 and 25%)
        bounds = [(0, 0.25) for _ in range(n_assets)]
        
        # Initial guess
        initial_weights = np.ones(n_assets)
        
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
    

    def calculate_returns(self):
        returns = self._load_returns()
        total_return = 0
        for etf in self.etfs:
            etf_return = np.prod(returns[etf].values + 1) - 1
            total_return += self.weights[etf] * etf_return
        
        return total_return[0]