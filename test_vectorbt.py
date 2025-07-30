import vectorbt as vbt
import logging
import sys
from config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Set Alpaca API credentials
vbt.settings.data['alpaca']['key_id'] = config.alpaca.api_key
vbt.settings.data['alpaca']['secret_key'] = config.alpaca.secret_key

def test_alpaca_fetch():
    symbol = 'AAPL'
    timeframe = '1h'
    start_date = '2024-01-01'
    end_date = '2024-03-13'
    
    logger.info(f"Fetching data for {symbol}")
    data = vbt.AlpacaData.download(
        symbol,
        start=start_date,
        end=end_date,
        timeframe=timeframe,
        limit=50000
    ).get()
    
    logger.info(f"Data shape: {data.shape}")
    logger.info(f"Raw columns: {data.columns.tolist()}")
    logger.info(f"Sample data:\n{data.head()}")
    
    # Try to access specific columns
    try:
        logger.info("\nTrying to access columns:")
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in data.columns:
                logger.info(f"{col} exists")
            else:
                logger.info(f"{col} does not exist")
    except Exception as e:
        logger.error(f"Error accessing columns: {str(e)}")

if __name__ == "__main__":
    test_alpaca_fetch() 