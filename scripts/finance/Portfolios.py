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
        # Convert annual risk to period risk (MAD scales with sqrt of time like volatility)
        max_risk = max_risk * np.sqrt(self.period_length / get_trading_days('1y'))
        R = self._load_returns(based_on).to_numpy()
        
        def risk(weights):
            R_weighted = R @ weights
            mu = np.mean(R_weighted)
            mad = np.mean(np.abs(R_weighted - mu))
            return mad
            
        return self._optimize_weights(based_on, max_risk, risk)


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
        # Convert annual risk to period risk (IQR scales with sqrt of time)
        max_risk = max_risk * np.sqrt(self.period_length / get_trading_days('1y'))
        R = self._load_returns(based_on).to_numpy()

        lower = self.trim / 2
        upper = 1 - self.trim / 2

        def risk(weights):
            R_weighted = R @ weights
            q_upper, q_lower = np.percentile(R_weighted, [upper * 100, lower * 100])
            iqr = q_upper - q_lower
            return iqr
            
        return self._optimize_weights(based_on, max_risk, risk)
