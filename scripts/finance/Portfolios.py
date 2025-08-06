import numpy as np
import pandas as pd

from scripts.finance.BasePortfolio import BasePortfolio
from scripts.finance.helpers import get_trading_days


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
        max_risk = max_risk * np.sqrt(1 / get_trading_days('1y'))
        R = self._load_returns(based_on).to_numpy()
        cov_matrix = np.cov(R, rowvar=False)
        

        def risk(weights):
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
        max_risk = max_risk * np.sqrt(1 / get_trading_days('1y'))
        R = self._load_returns(based_on).to_numpy()
        
        def risk(weights):
            R_weighted = R @ weights
            mu = np.mean(R_weighted)
            risk = np.mean(np.abs(R_weighted - mu))
            return risk
            
        return self._optimize_weights(based_on, max_risk, risk)


class IQRPortfolio(BasePortfolio):
    def __init__(self, freq, max_alloc=None):
        super().__init__(
            freq=freq, 
            max_alloc=max_alloc,
            use_index_etf=False
            )


    def _calculate_weights(self, based_on, max_risk):
        """
        Calculate Interquartile Range portfolio weights
        """
        max_risk = max_risk * np.sqrt(1 / get_trading_days('1y'))
        R = self._load_returns(based_on).to_numpy()
        
        def risk(weights):
            R_weighted = R @ weights
            q75, q25 = np.percentile(R_weighted, [75, 25])
            iqr = q75 - q25
            return iqr / 2
            
        return self._optimize_weights(based_on, max_risk, risk)
