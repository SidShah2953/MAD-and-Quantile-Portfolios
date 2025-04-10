import os
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

def collect_data():
    data_folder = os.getenv('RAW_DATA_DIRECTORY')
    etfs = os.getenv('ETF_LIST').split(',') + ['^GSPC']
    
    for etf in etfs:
        print(etf)
        get_stock(etf, output_folder=data_folder)


def get_stock(ticker,
                output_folder,
                start_date=str(os.getenv('START_YEAR')) + '-01-01',
                end_date=str(os.getenv('END_YEAR')) + '-12-31',
                s_window=14, 
                l_window=50):
    try:
        #yf.pdr_override()  # Uncomment if necessary
        df = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False)
        # Add additional columns
        if 'Adj Close' not in df.columns:
            df['Adj Close'] = df['Close']

        #df = web.get_data_yahoo(ticker, start=start_date, end=end_date)
        df['Return'] = df['Adj Close'].pct_change()
        df['Return'] = df['Return'].fillna(0)
        df['Date'] = df.index
        df['Date'] = pd.to_datetime(df['Date'])
        df['Month'] = df['Date'].dt.month
        df['Year'] = df['Date'].dt.year
        df['Day'] = df['Date'].dt.day
        for col in ['Open', 'High', 'Low', 'Close', 'Adj Close']:
            df[col] = df[col].round(2)
        df['Weekday'] = df['Date'].dt.day_name()
        df['Week_Number'] = df['Date'].dt.strftime('%U')
        df['Year_Week'] = df['Date'].dt.strftime('%Y-%U')
        df['Short_MA'] = df['Adj Close'].rolling(window=s_window, min_periods=1).mean()
        df['Long_MA'] = df['Adj Close'].rolling(window=l_window, min_periods=1).mean()
        col_list = ['Date', 'Year', 'Month', 'Day', 'Weekday',
                    'Week_Number', 'Year_Week', 'Open',
                    'High', 'Low', 'Close', 'Volume', 'Adj Close',
                    'Return', 'Short_MA', 'Long_MA']
        df = df[col_list]

        if df is not None:
            input_dir = os.getcwd()
            output_file = os.path.join(input_dir, f'{output_folder}/{ticker}.csv')
            df.to_csv(output_file, index=False)
            print(f'\t- Data collected from Yahoo Finance: {len(df)} lines for {ticker}')
        else:
            print('\t- No data collected for ticker' + ticker)

    except Exception as error:
        print(error)
        print('\t- Failed to get Yahoo stock data for ticker:', ticker)
        return None
