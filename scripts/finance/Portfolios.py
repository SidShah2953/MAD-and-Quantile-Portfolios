import numpy as np
import pandas as pd

from scripts.finance.BasePortfolio import BasePortfolio
from scripts.finance.helpers import get_trading_days
from scipy.stats import norm


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
        # Convert annual risk to period risk
        max_risk = max_risk * np.sqrt(self.period_length / get_trading_days('1y'))
        R = self._load_returns(based_on).to_numpy()
        cov_matrix = np.cov(R, rowvar=False)
        

        def risk(weights):
            # Return daily standard deviation of portfolio
            return np.sqrt(weights @ cov_matrix @ weights.T)
            
        return self._optimize_weights(based_on, max_risk, risk)


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
        # Convert annual max_risk (in volatility terms) to period-level
        max_risk_period = max_risk * np.sqrt(self.period_length / get_trading_days('1y'))
        
        # Convert volatility constraint to MAD constraint
        # For normal distribution: MAD ≈ 0.7979 * σ
        # So if max_risk is in σ terms, MAD constraint should be 0.7979 * max_risk
        max_mad = max_risk_period
        
        R = self._load_returns(based_on).to_numpy()
        
        def risk(weights):
            R_weighted = R @ weights
            mu = np.mean(R_weighted)
            mad = np.mean(np.abs(R_weighted - mu))
            return mad
        
        return self._optimize_weights(based_on, max_mad, risk)


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
        # Convert annual max_risk (in volatility terms) to period-level
        max_risk_period = max_risk * np.sqrt(self.period_length / get_trading_days('1y'))
        
        # Convert volatility constraint to IQR constraint
        # For normal distribution: IQR ≈ 1.349 * σ
        # Standard IQR uses Q75-Q25, which captures ~50% of the distribution (two-sided)
        # If using custom trim, adjust accordingly
        if self.trim == 0.5:
            # Standard IQR: Q75 - Q25 ≈ 1.349σ
            max_iqr = max_risk_period * 2
        else:
            # For custom percentiles, use z-score difference
            from scipy.stats import norm
            lower = self.trim / 2
            upper = 1 - self.trim / 2
            z_upper = norm.ppf(upper)
            z_lower = norm.ppf(lower)
            max_iqr = max_risk_period * (z_upper - z_lower)
        
        R = self._load_returns(based_on).to_numpy()

        lower = self.trim / 2
        upper = 1 - self.trim / 2

        def risk(weights):
            R_weighted = R @ weights
            q_upper, q_lower = np.percentile(R_weighted, [upper * 100, lower * 100])
            iqr = q_upper - q_lower
            return iqr
        
        return self._optimize_weights(based_on, max_iqr, risk)
