import vectorbt as vbt
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)

# Set Alpaca credentials directly
vbt.settings.data['alpaca']['key_id'] = 'PK463DCZLB0H1M8TG3DN'
vbt.settings.data['alpaca']['secret_key'] = 'UNWYjiMmOhCdFIhFvKIXNK0AtdBbFUMDs6w1vVZq'

# Test a simple data fetch
symbol = 'AAPL'
timeframe = '1h'
start_date = '2024-01-01'
end_date = '2024-01-10'

print(f"Fetching data for {symbol}")
data = vbt.AlpacaData.download(
    symbol,
    start=start_date,
    end=end_date,
    timeframe=timeframe
).get()

print(f"Data shape: {data.shape}")
print(f"Columns: {data.columns.tolist()}")
print(f"Sample data:\n{data.head()}") 