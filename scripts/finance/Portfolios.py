import numpy as np
import pandas as pd

from scripts.finance.BasePortfolio import BasePortfolio


class BuyAndHold(BasePortfolio):
    def __init__(self, freq, max_alloc=None):
        super().__init__(freq=freq, max_alloc=max_alloc, use_index_etf=True)
    
    
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
    

class EqWeightPortfolio(BasePortfolio):
    def __init__(self, freq, max_alloc=None):
        super().__init__(freq=freq, max_alloc=max_alloc, use_index_etf=False)
    

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


class MarkowitzPortfolio(BasePortfolio):
    def __init__(self, freq, max_alloc=None):
        super().__init__(freq=freq, max_alloc=max_alloc, use_index_etf=False)
    

    def _calculate_weights(self, based_on, max_risk):
        """
        Calculate Markowitz portfolio weights using mean-variance optimization
        """
        max_risk = max_risk * np.sqrt(1 / 250)
        R = self._load_returns(based_on).to_numpy()
        cov_matrix = np.cov(R, rowvar=False)
        
        def risk(weights):
            return np.sqrt(weights @ cov_matrix @ weights.T)
            
        return self._optimize_weights(based_on, max_risk, risk)


class MeanAbsDevPortfolio(BasePortfolio):
    def __init__(self, freq, max_alloc=None):
        super().__init__(freq=freq, max_alloc=max_alloc, use_index_etf=False)


    def _calculate_weights(self, based_on, max_risk):
        """
        Calculate Mean Absolute Deviation portfolio weights
        """
        max_risk = np.sqrt(2 / np.pi) * max_risk * np.sqrt(1 / 250)
        R = self._load_returns(based_on).to_numpy()
        mu = np.mean(R, axis=0)
        
        def risk(weights):
            risk = np.mean(np.abs(R - mu), axis=0)
            risk = risk @ weights
            return risk
            
        return self._optimize_weights(based_on, max_risk, risk)
