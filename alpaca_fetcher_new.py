import pandas as pd
import numpy as np
import logging
from tqdm import tqdm
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from ratelimit import limits, sleep_and_retry
import requests
from core.data_engine.historical.sql_database import SQLDatabaseHandler
import time
from alpaca_trade_api.rest import REST, TimeFrame
from datetime import datetime, timezone

# Set up logging
logging.basicConfig(level=logging.INFO)

def convert_timeframe(timeframe):
    """Convert timeframe string to Alpaca TimeFrame object"""
    if timeframe == '1h':
        return TimeFrame.Hour
    elif timeframe == '4h':
        return TimeFrame.Hour  # We'll fetch 1h data and resample later
    elif timeframe == '1d':
        return TimeFrame.Day
    else:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(3),
    retry=(
        retry_if_exception_type(requests.exceptions.Timeout) |
        retry_if_exception_type(requests.exceptions.ConnectionError)
    )
)
@sleep_and_retry
@limits(calls=190, period=60)
def get_alpaca_data(symbols, start_date, end_date, timeframes, use_database=True, save_to_csv=False):
    """
    Retrieve stock data from Alpaca API and store in SQL database.
    
    Args:
        symbols (list): List of stock symbols to fetch data for.
        start_date (str): Start date for data retrieval in 'YYYY-MM-DD' format.
        end_date (str): End date for data retrieval in 'YYYY-MM-DD' format.
        timeframes (list): List of timeframes to fetch data for ('1h', '4h', '1d').
        use_database (bool): Whether to use SQL database for storage/retrieval (default: True)
        save_to_csv (bool): Whether to export data to CSV files (default: False)
    
    Returns:
        dict: A dictionary where keys are symbols and values are the corresponding data frames.
    """
    results = {}
    db_handler = SQLDatabaseHandler() if use_database else None
    
    # Set up Alpaca API client
    alpaca = REST(
        key_id='PK463DCZLB0H1M8TG3DN',
        secret_key='UNWYjiMmOhCdFIhFvKIXNK0AtdBbFUMDs6w1vVZq',
        base_url='https://data.alpaca.markets/v2'  # Use data API endpoint
    )
    
    # Convert dates to datetime objects
    start_dt = pd.Timestamp(start_date, tz=timezone.utc)
    end_dt = pd.Timestamp(end_date, tz=timezone.utc)
    
    total_tasks = len(symbols) * len(timeframes)
    error_count = 0
    
    with tqdm(total=total_tasks, desc="Fetching Data", unit="task") as pbar:
        for symbol in symbols:
            results[symbol] = {}
            for timeframe in timeframes:
                try:
                    pbar.set_description(f"Processing {symbol} {timeframe}")
                    
                    # Convert timeframe to Alpaca format
                    alpaca_timeframe = convert_timeframe(timeframe)
                    
                    # Fetch data from Alpaca
                    bars = alpaca.get_bars(
                        symbol,
                        alpaca_timeframe,
                        start=start_dt.isoformat(),
                        end=end_dt.isoformat(),
                        adjustment='raw'
                    ).df
                    
                    # Resample to 4h if needed
                    if timeframe == '4h':
                        bars = bars.resample('4H').agg({
                            'open': 'first',
                            'high': 'max',
                            'low': 'min',
                            'close': 'last',
                            'volume': 'sum',
                            'trade_count': 'sum',
                            'vwap': 'mean'
                        }).dropna()
                    
                    # Log raw data information
                    logging.info(f"Raw data for {symbol} ({timeframe}):")
                    logging.info(f"Shape: {bars.shape}")
                    logging.info(f"Columns: {bars.columns.tolist()}")
                    
                    # Store the original data
                    results[symbol][timeframe] = bars
                    
                    # Store in database if enabled
                    if db_handler and not bars.empty:
                        try:
                            # Validate data format with case-insensitive check
                            required_columns = {'open', 'high', 'low', 'close', 'volume'}
                            actual_columns = {col.lower() for col in bars.columns}
                            missing_cols = required_columns - actual_columns
                            
                            if missing_cols:
                                raise ValueError(f"Missing columns: {missing_cols}")
                            
                            # Create a copy of the data for database storage
                            db_data = bars.copy()
                            # Normalize column names to lowercase for database
                            db_data.columns = db_data.columns.str.lower()
                            
                            # Ensure index is datetime
                            if not isinstance(db_data.index, pd.DatetimeIndex):
                                raise ValueError(f"Data index must be DatetimeIndex for {symbol} {timeframe}")
                            
                            # Validate database connection with timeout
                            max_retries = 3
                            for attempt in range(max_retries):
                                try:
                                    if not db_handler.is_connected():
                                        logging.info(f"Reconnecting to database (attempt {attempt + 1}/{max_retries})")
                                        db_handler.reconnect()
                                    break
                                except Exception as conn_error:
                                    if attempt == max_retries - 1:
                                        raise Exception(f"Failed to establish database connection after {max_retries} attempts: {str(conn_error)}")
                                    time.sleep(2 ** attempt)  # Exponential backoff
                            
                            # Store with detailed logging
                            rows_before = db_handler.get_row_count(symbol, timeframe)
                            db_handler.store_bars(symbol, timeframe, db_data, upsert=True)
                            rows_after = db_handler.get_row_count(symbol, timeframe)
                            
                            rows_added = rows_after - rows_before
                            logging.info(f"Successfully stored {rows_added} new bars for {symbol} {timeframe}")
                            logging.info(f"Data range: {db_data.index[0]} to {db_data.index[-1]}")
                            
                            pbar.update(1)
                        except ValueError as ve:
                            error_count += 1
                            logging.error(f"Data validation error for {symbol} {timeframe}: {str(ve)}")
                            logging.debug("Validation error details:", exc_info=True)
                        except Exception as storage_error:
                            error_count += 1
                            logging.error(f"Database storage failed for {symbol} {timeframe}: {str(storage_error)}")
                            logging.error("Error details:", exc_info=True)
                            
                            # Attempt to log detailed database state
                            try:
                                if db_handler and db_handler.is_connected():
                                    db_state = db_handler.get_connection_info()
                                    logging.info(f"Database state: {db_state}")
                            except Exception as state_error:
                                logging.warning(f"Could not fetch database state: {str(state_error)}")
                except Exception as e:
                    error_count += 1
                    logging.error(f"Error processing {symbol} for {timeframe}: {str(e)}")
                    results[symbol][timeframe] = None
    
    return results