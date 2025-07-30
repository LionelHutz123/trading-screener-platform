import os
from datetime import datetime, timedelta
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from core.data_engine.sql_database import SQLDatabaseHandler

# Initialize clients
API_KEY = os.getenv('ALPACA_API_KEY')
API_SECRET = os.getenv('ALPACA_SECRET_KEY')
client = StockHistoricalDataClient(API_KEY, API_SECRET)

# Initialize database
db = SQLDatabaseHandler('financial_data.db')

def fetch_and_store_data(symbol: str, start_date: str, end_date: str):
    # Create request parameters
    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.strptime(start_date, '%Y-%m-%d'),
        end=datetime.strptime(end_date, '%Y-%m-%d')
    )
    
    # Get the data
    bars = client.get_stock_bars(request_params)
    
    # Convert to DataFrame
    df = bars.df.reset_index()
    df = df.rename(columns={
        'timestamp': 'timestamp',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume'
    })
    
    # Store in database
    db.store_bars(symbol, '1d', df)
    print(f"Stored {len(df)} bars for {symbol}")

if __name__ == '__main__':
    # Fetch 2 years of data
    fetch_and_store_data('AAPL', '2022-01-01', '2023-12-31') 