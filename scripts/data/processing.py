import os
import pandas as pd
from dotenv import load_dotenv


def process_data():
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


def add_period_column(df, date_col='Date', freq='1d'):
    """
    Add a 'period' column to the DataFrame that contains the last date in each period group.

    Parameters:
    df (DataFrame): The pandas DataFrame containing the dates
    date_col (str): Name of the column containing dates in 'YYYY-MM-DD' format
    freq (str): Frequency string following yfinance convention
                '1d' for daily, '1wk' for weekly, '1mo' for monthly,
                '3mo' for quarterly, '6mo' for 6-monthly, '1y' for yearly

    Returns:
    DataFrame: Original DataFrame with new 'period' column containing the last date in each group
    """
    # Create a copy to avoid modifying the original DataFrame
    result_df = df.copy()

    # Convert text dates to datetime objects
    result_df['date_obj'] = pd.to_datetime(result_df[date_col])

    # Create a temporary column for grouping
    if freq == '1d':
        # Daily - each date is its own group
        result_df['temp_group'] = result_df['date_obj'].dt.strftime('%Y-%m-%d')

    elif freq == '1wk':
        # Weekly - group by year and week number
        result_df['temp_group'] = result_df['date_obj'].dt.strftime('%Y-%U')  # %U: week number (Sunday as first day)

    elif freq == '1mo':
        # Monthly - group by year and month
        result_df['temp_group'] = result_df['date_obj'].dt.strftime('%Y-%m')

    elif freq == '3mo':
        # Quarterly - group by year and quarter
        result_df['temp_group'] = result_df['date_obj'].dt.year.astype(str) + '-' + \
                                  ((result_df['date_obj'].dt.month - 1) // 3 + 1).astype(str)

    elif freq == '6mo':
        # 6-monthly - group by year and half
        result_df['temp_group'] = result_df['date_obj'].dt.year.astype(str) + '-' + \
                                  ((result_df['date_obj'].dt.month - 1) // 6 + 1).astype(str)

    elif freq == '1y':
        # Yearly - group by year
        result_df['temp_group'] = result_df['date_obj'].dt.year.astype(str)

    else:
        raise ValueError(f"Frequency '{freq}' not supported. Use '1d', '1wk', '1mo', '3mo', '6mo', or '1y'.")

    # Find the first date in each group (rebalancing happens at period start)
    group_first_dates = result_df.groupby('temp_group')['date_obj'].min()

    # Map the first dates back to the original DataFrame
    result_df['period'] = result_df['temp_group'].map(group_first_dates)

    # Convert period back to string format
    result_df['period'] = result_df['period'].dt.strftime('%Y-%m-%d')

    # Remove temporary columns
    result_df = result_df.drop(['date_obj', 'temp_group', date_col], axis=1)

    return result_df