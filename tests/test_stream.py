import sys
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Load environment variables from .env file
env_path = Path(project_root) / '.env'
load_dotenv(dotenv_path=env_path)

# Get API credentials directly
api_key = "PK463DCZLB0H1M8TG3DN"
secret_key = "UNWYjiMmOhCdFIhFvKIXNK0AtdBbFUMDs6w1vVZq"

from core.data_engine.streaming.alpaca_stream import AlpacaStreamClient, AlpacaStreamConfig

# Set up logging with debug level
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Debug log the API credentials
logger.debug(f"API Key: {api_key}")
logger.debug(f"Secret Key: {secret_key}")

# Message counters
message_counts = {
    "trade_updates": 0,
    "trades": 0,
    "quotes": 0,
    "bars": 0
}

async def handle_trade_update(data):
    """Handle trade updates from trading API"""
    message_counts["trade_updates"] += 1
    logger.info(f"Trade Update ({message_counts['trade_updates']}): {data}")

async def handle_trade(data):
    """Handle trade messages from data API"""
    message_counts["trades"] += 1
    logger.info(f"Trade ({message_counts['trades']}): {data}")

async def handle_quote(data):
    """Handle quote messages from data API"""
    message_counts["quotes"] += 1
    if message_counts["quotes"] <= 5:  # Log only first 5 quotes to avoid spam
        logger.info(f"Quote ({message_counts['quotes']}): {data}")
    elif message_counts["quotes"] % 100 == 0:  # Log every 100th quote
        logger.info(f"Quote ({message_counts['quotes']}): {data}")

async def handle_bar(data):
    """Handle bar messages from data API"""
    message_counts["bars"] += 1
    logger.info(f"Bar ({message_counts['bars']}): {data}")

async def test_connection():
    """Test WebSocket connections and data streaming"""
    logger.info("Testing Alpaca WebSocket connections...")
    
    stream_config = AlpacaStreamConfig(
        api_key=api_key,
        secret_key=secret_key,
        paper_trading=True
    )
    
    client = AlpacaStreamClient(stream_config)
    
    try:
        # Connect to WebSockets
        logger.info("Connecting to WebSockets...")
        await client.connect()
        logger.info("Connection successful!")
        
        # Register callbacks
        client.callbacks["trade_updates"] = [handle_trade_update]
        client.callbacks["t"] = [handle_trade]  # Trade messages have type "t"
        client.callbacks["q"] = [handle_quote]  # Quote messages have type "q"
        client.callbacks["b"] = [handle_bar]    # Bar messages have type "b"
        
        # Subscribe to streams
        test_streams = [
            "trade_updates",           # Account updates
            "T.AAPL", "T.MSFT",       # Trades for AAPL and MSFT
            "Q.AAPL", "Q.MSFT",       # Quotes for AAPL and MSFT
            "AM.AAPL", "AM.MSFT"      # 1-minute bars for AAPL and MSFT
        ]
        logger.info(f"Subscribing to streams: {test_streams}")
        await client.subscribe(test_streams)
        
        # Run for 10 seconds to test message reception
        logger.info("Starting message reception test (10 seconds)...")
        start_time = datetime.now()
        
        async def stop_after_10s():
            await asyncio.sleep(10)
            client.running = False
            
        # Create tasks for streaming and timeout
        stream_task = asyncio.create_task(client.start_streaming())
        timeout_task = asyncio.create_task(stop_after_10s())
        
        # Wait for both tasks
        await asyncio.gather(stream_task, timeout_task)
        
        # Print message statistics
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"\nTest completed after {duration:.1f} seconds")
        logger.info("\nMessage Statistics:")
        for stream, count in message_counts.items():
            logger.info(f"{stream}: {count} messages ({count/duration:.2f} msgs/sec)")
            
        # Check if any messages were received
        total_messages = sum(message_counts.values())
        if total_messages == 0:
            logger.warning("\nNo messages received. This is normal if the market is closed.")
            logger.info("The US stock market is open Monday-Friday, 9:30 AM - 4:00 PM Eastern Time.")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise
    finally:
        await client.stop()
        logger.info("Test finished, connections closed")

if __name__ == "__main__":
    try:
        asyncio.run(test_connection())
    except KeyboardInterrupt:
        logger.info("Test terminated by user")
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        raise 