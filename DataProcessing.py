import os
import pandas as pd
from dotenv import load_dotenv

def main():
    load_dotenv()

    input_folder = os.getenv('RAW_DATA_DIRECTORY')
    etfs = os.getenv('ETF_LIST').split(',')

    files = {}
    for etf in etfs:
        file = pd.read_csv(f'{input_folder}{etf}.csv')
        files[etf] = file.dropna()

    start = int(os.getenv('START_YEAR'))
    end = int(os.getenv('END_YEAR'))
    output_folder = os.getenv('YEARLY_DATA_DIRECTORY')

    for year in range(start, end + 1):
        yearly_data = None
        for etf in etfs:
            etf_yearly = files[etf]
            etf_yearly = etf_yearly[etf_yearly['Year'] == year][['Date', 'Return']]
            etf_yearly.columns = ['Date', etf]
            
            if yearly_data is None:
                yearly_data = etf_yearly
            else:
                yearly_data = pd.merge(yearly_data, etf_yearly)
        # yearly_data['CSH'] = 0
        yearly_data.to_csv(f'{output_folder}{year}.csv', index=False)

main()