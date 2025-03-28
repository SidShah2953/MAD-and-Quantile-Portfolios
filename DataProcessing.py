import os
import pandas as pd
from dotenv import load_dotenv


def main():
    load_dotenv()

    input_folder = os.getenv('RAW_DATA_DIRECTORY')
    etfs = os.getenv('ETF_LIST').split(',') + [os.getenv('INDEX_ETF')]

    files = {}
    for etf in etfs:
        file = pd.read_csv(f'{input_folder}{etf}.csv')
        files[etf] = file.dropna()

    output_file = os.getenv('COMBINED_DATA_FILE')

    combined = None
    for etf in etfs:
        etf_data = files[etf]
        etf_data = etf_data[['Date', 'Return']]
        etf_data.columns = ['Date', etf]

        if combined is None:
            combined = etf_data
        else:
            combined = pd.merge(combined, etf_data)
    combined['CSH'] = 0.00
    combined.sort_values('Date') \
        .to_csv(f'{output_file}', index=False)


main()