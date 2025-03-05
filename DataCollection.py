import os
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

def main():
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


def get_grouped_returns(ticker, folder):
    input_dir = os.path.join(os.getcwd(), f'{folder}')
    df = pd.read_csv(f'{input_dir}/{ticker}.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    # Add additional columns
    if 'Adj Close' not in df.columns:
        df['Adj Close'] = df['Close']

    # Calculate daily returns and handle NaNs
    df['Return'] = df['Adj Close'].pct_change().fillna(0)
    df['Return'] = df['Return'].round(4)

    # Add columns for week number and year
    df['Week_Number'] = df.index.strftime('%U')
    df['Year'] = df.index.year

    # Select relevant columns for grouping
    df_2 = df[['Year', 'Week_Number', 'Return']]
    df_2.reset_index(drop=True, inplace=True)

    # Group by year and week number to calculate mean return and volatility
    df_grouped = df_2.groupby(['Year', 'Week_Number'])['Return'].agg(['mean', 'std'])
    df_grouped.reset_index(inplace=True)
    df_grouped.rename(columns={'mean': 'mean_return', 'std': 'volatility'}, inplace=True)
    df_grouped.fillna(0, inplace=True)

    # Save the weekly return and volatility data to a new CSV file
    output_file = f"{input_dir}/{ticker}_weekly_return_volatility.csv"
    df_grouped.to_csv(output_file, index=False)
    print(f"\t- Weekly data stored: {len(df_grouped)} lines for {ticker}")

    # Save detailed data by merging original and grouped DataFrames
    try:
        # Ensure the 'Week_Number' is a string for both DataFrames
        df['Week_Number'] = df['Week_Number'].astype(str)
        df_grouped['Week_Number'] = df_grouped['Week_Number'].astype(str)

        # Merge DataFrames on 'Year' and 'Week_Number'
        combined_df = df.reset_index().merge(df_grouped, on=['Year', 'Week_Number'], how='inner')
        detailed_output_file = f"{input_dir}/{ticker}_weekly_return_detailed.csv"
        combined_df.to_csv(detailed_output_file, index=False)
        print(f"\t- Merged data stored: {len(combined_df)} lines for {ticker}")

    except Exception as e:
        print("\t- Error during merge:", e)


main()