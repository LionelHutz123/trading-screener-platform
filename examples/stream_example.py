import sys
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from core.data_engine.streaming.alpaca_stream import AlpacaStreamClient, AlpacaStreamConfig
from config import config  # Import your config with API keys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def handle_trade_update(data: Dict[str, Any]):
    """Handle incoming trade updates"""
    logger.info(f"Trade Update: {data}")
    # Add your trade processing logic here

async def handle_quote_update(data: Dict[str, Any]):
    """Handle incoming quote updates"""
    logger.info(f"Quote Update: {data}")
    # Add your quote processing logic here

async def handle_bar_update(data: Dict[str, Any]):
    """Handle incoming bar updates"""
    logger.info(f"Bar Update: {data}")
    # Add your bar processing logic here

async def main():
    # Initialize stream config
    stream_config = AlpacaStreamConfig(
        api_key=config.alpaca.api_key,
        secret_key=config.alpaca.secret_key,
        paper_trading=True  # Set to False for live trading
    )
    
    # Create stream client
    client = AlpacaStreamClient(stream_config)
    
    try:
        # Connect to WebSocket
        await client.connect()
        
        # Register callbacks
        client.callbacks["trade_updates"] = [handle_trade_update]
        client.callbacks["AM.AAPL"] = [handle_bar_update]  # 1-minute bars for AAPL
        client.callbacks["Q.AAPL"] = [handle_quote_update]  # Quotes for AAPL
        
        # Subscribe to streams
        await client.subscribe([
            "trade_updates",  # Trading account updates
            "AM.AAPL",       # 1-minute bars for AAPL
            "Q.AAPL"         # Quotes for AAPL
        ])
        
        # Start streaming
        logger.info("Starting WebSocket stream...")
        await client.start_streaming()
        
    except KeyboardInterrupt:
        logger.info("Stopping stream...")
        await client.stop()
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")
        await client.stop()
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stream example terminated by user") 