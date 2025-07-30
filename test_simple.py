import vectorbt as vbt
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Alpaca credentials directly
vbt.settings.data['alpaca']['key_id'] = 'PK463DCZLB0H1M8TG3DN'
vbt.settings.data['alpaca']['secret_key'] = 'UNWYjiMmOhCdFIhFvKIXNK0AtdBbFUMDs6w1vVZq'

try:
    # Test a simple data fetch
    logger.info("Starting data fetch...")
    data = vbt.AlpacaData.download(
        'AAPL',
        start='2024-01-01',
        end='2024-01-10',
        timeframe='1h'
    ).get()
    
    logger.info(f"Data shape: {data.shape}")
    logger.info(f"Columns: {data.columns.tolist()}")
    logger.info(f"Sample data:\n{data.head()}")
    
except Exception as e:
    logger.error(f"Error: {str(e)}", exc_info=True) 