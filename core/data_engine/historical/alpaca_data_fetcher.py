import vectorbt as vbt
import pandas as pd
import numpy as np
import logging
from tqdm import tqdm
import traceback

def get_alpaca_data_from_csv(csv_file_path, start_date, end_date, timeframe='1d', symbol_column='Symbol'):
    """
    Retrieve stock data from Alpaca API using vectorbt for symbols listed in a CSV file.
    
    Args:
    csv_file_path (str): Path to the CSV file containing the list of symbols.
    start_date (str): Start date for data retrieval in 'YYYY-MM-DD' format.
    end_date (str): End date for data retrieval in 'YYYY-MM-DD' format.
    timeframe (str): Timeframe for data retrieval. Default is '1d' for daily data.
    symbol_column (str): Name of the column in the CSV file that contains the symbols. Default is 'Symbol'.
    
    Returns:
    dict: A dictionary where keys are symbols and values are the corresponding data frames.
    """
    results = {}
    
    # Load symbols from CSV
    try:
        df = pd.read_csv(csv_file_path)
        logging.info(f"CSV file loaded successfully. Columns: {df.columns.tolist()}")
        logging.info(f"First few rows of the CSV file:\n{df.head()}")
        
        symbols = df[symbol_column].tolist()
        logging.info(f"Found {len(symbols)} symbols.")
        logging.info(f"First few symbols: {symbols[:5]}")
    except Exception as e:
        logging.error(f"Error loading symbols from CSV: {str(e)}")
        logging.error(traceback.format_exc())
        return results

    # Create overall progress bar
    overall_pbar = tqdm(total=len(symbols), desc="Fetching Data", position=0)

    for symbol in symbols:
        logging.info(f"Processing {symbol}")
        
        try:
            # Fetch data
            data = vbt.AlpacaData.download(symbol, start=start_date, end=end_date, timeframe=timeframe).get()
            logging.info(f"Data shape for {symbol}: {data.shape}")
            results[symbol] = data
        
        except Exception as e:
            logging.error(f"Error processing {symbol}: {str(e)}")
            results[symbol] = None
        
        # Update overall progress bar
        overall_pbar.update(1)

    # Close overall progress bar
    overall_pbar.close()

    return results

# Example usage:
# Set Alpaca API credentials
# vbt.settings.data['alpaca']['key_id'] = 'YOUR_KEY_ID'
# vbt.settings.data['alpaca']['secret_key'] = 'YOUR_SECRET_KEY'

# Correct way to specify file path
# csv_file_path = r"C:\Users\python\pyproj\Untitled Folder\sp500_companies.csv"
# start_date = '2020-01-01'
# end_date = '2024-08-16'
# data_dict = get_alpaca_data_from_csv(csv_file_path, start_date, end_date)

# for symbol, data in data_dict.items():
#     if data is not None:
#         print(f"\nData for {symbol}:")
#         print(data.head())
#     else:
#         print(f"\nNo data available for {symbol}")