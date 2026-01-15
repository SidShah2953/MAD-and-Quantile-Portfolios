import numpy as np
import pandas as pd

from scripts.finance.BasePortfolio import BasePortfolio
from scripts.finance.helpers import get_trading_days
from scipy.stats import norm

import os
from dotenv import load_dotenv
load_dotenv()

SCALE = True if 'TRUE' in (os.getenv('SCALE', 'FALSE')).upper() else False


class BuyAndHold(BasePortfolio):
    def __init__(self, freq, max_alloc=None):
        super().__init__(
            freq=freq,
            max_alloc=max_alloc,
            use_index_etf=True
            )
    
    
    def _calculate_weights(self, based_on, max_risk):
        """
        Simple equal weight allocation
        """
        invest_in = len(self.etfs)
        weights = [[1 / invest_in]] * invest_in
        weights = pd.DataFrame(dict(zip(
                            self.etfs,
                            weights
                        )))
        return weights


class StdDevPortfolio(BasePortfolio):
    def __init__(self, freq, max_alloc=None):
        super().__init__(
            freq=freq,
            max_alloc=max_alloc,
            use_index_etf=False
            )
    

    def _calculate_weights(self, based_on, max_risk):
        """
        Calculate Markowitz portfolio weights using mean-variance optimization
        """
        # Convert annualized risk target to DAILY risk target (risk() returns daily std dev)
        max_period_risk = max_risk / np.sqrt(get_trading_days('1y'))
        R = self._load_returns(based_on).to_numpy()
        cov_matrix = np.cov(R, rowvar=False)
        

        def risk(weights):
            # Return daily standard deviation of portfolio
            return np.sqrt(weights @ cov_matrix @ weights.T)
            
        return self._optimize_weights(based_on, max_period_risk, risk)


class MADPortfolio(BasePortfolio):
    def __init__(self, freq, max_alloc=None):
        super().__init__(
            freq=freq, 
            max_alloc=max_alloc,
            use_index_etf=False
            )


    def _calculate_weights(self, based_on, max_risk):
        """
        Calculate Mean Absolute Deviation portfolio weights
        """
        # Convert annualized risk target to DAILY volatility units; risk() returns daily MAD
        max_period_risk = max_risk / np.sqrt(get_trading_days('1y'))
        
        # For log-normal returns (small returns approximation): MAD ≈ σ * sqrt(2/π) ≈ 0.798σ
        if SCALE:
            max_period_risk *= np.sqrt(2 / np.pi)
        
        R = self._load_returns(based_on).to_numpy()
        
        def risk(weights):
            R_weighted = R @ weights
            mu = np.mean(R_weighted)
            mad = np.mean(np.abs(R_weighted - mu))
            return mad
        
        return self._optimize_weights(based_on, max_period_risk, risk)


class IQRPortfolio(BasePortfolio):
    def __init__(self, freq, max_alloc=None, trim=0.5):
        super().__init__(
            freq=freq, 
            max_alloc=max_alloc,
            use_index_etf=False
            )
        self.trim = trim


    def _calculate_weights(self, based_on, max_risk):
        """
        Calculate Interquartile Range portfolio weights
        """
        # Convert annualized risk target to DAILY volatility units; risk() returns daily IQR
        max_period_risk = max_risk / np.sqrt(get_trading_days('1y'))
        
        lower = self.trim / 2
        upper = 1 - self.trim / 2

        # For log-normal returns (small returns approximation): IQR ≈ 2σ * Φ^(-1)(upper)
        # For standard IQR (25th-75th): IQR ≈ 1.349σ
        if SCALE:
            max_period_risk *= 2 * norm.ppf(upper)
        
        R = self._load_returns(based_on).to_numpy()

        def risk(weights):
            R_weighted = R @ weights
            q_upper, q_lower = np.percentile(R_weighted, [upper * 100, lower * 100])
            iqr = q_upper - q_lower
            return iqr
        
        return self._optimize_weights(based_on, max_period_risk, risk)
