import pandas as pd
from skfolio import Population, RiskMeasure
from skfolio.preprocessing import returns_from_prices
from skfolio.optimization import MeanVarianceOptimization, MeanAbsoluteDeviationOptimization

class PortfolioOptimizer:
    def __init__(self, stocks, weekly=False):
        """
        Initialize optimizer with stock price files
        
        :param stocks: List of Excel files with stock prices
        """
        self.prices = self._load_prices(stocks, weekly)
        self.returns = returns_from_prices(self.prices)
        self.population = Population(self.returns)
    
    def _load_prices(self, stocks, weekly=False):
        """
        Load stock prices from Excel files
        
        :param price_files: List of file paths
        :return: List of price DataFrames
        """
        return [pd.read_excel(file) for file in stocks]
    
    def optimize_mvo(self, target_risk):
        """
        Optimize portfolio using Mean-Variance Optimization
        
        :param target_risk: Target portfolio risk
        :return: Portfolio weights
        """
        mvo = MeanVarianceOptimization(
            risk_measure=RiskMeasure.VARIANCE,
            max_risk=target_risk
        )
        portfolio = mvo.optimize(self.population)
        return portfolio.weights
    
    def optimize_mad(self, target_risk):
        """
        Optimize portfolio using Mean Absolute Deviation
        
        :param target_risk: Target portfolio risk
        :return: Portfolio weights
        """
        mad = MeanAbsoluteDeviationOptimization(
            max_mad=target_risk
        )
        portfolio = mad.optimize(self.population)
        return portfolio.weights
