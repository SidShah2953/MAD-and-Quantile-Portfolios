import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def get_yearly_returns(portfolio, max_risk):
    # Load ETFs and input path from environment variables
    etfs = os.getenv('ETF_LIST').split(',')
    input_path = os.getenv('YEARLY_DATA_DIRECTORY')

    start_year = int(os.getenv('START_YEAR')) + 1
    end_year = int(os.getenv("END_YEAR"))

    collector = []
    for year in range(start_year, end_year + 1):
        po = portfolio(etfs, target_year=year, input_path=input_path)
        weights = po.calculate_portfolio(max_risk)
        df = weights.copy()
        df['Year'] = [year]
        df['Return'] = [po.calculate_returns()]
        collector.append(df)

    df = pd.concat(collector)
    df = df[['Year', 'Return'] + etfs]
    for col in etfs + ['Return']:
        df[col] = (df[col] * 100).round(2)
    df = df.reset_index().drop('index', axis=1)

    return df
