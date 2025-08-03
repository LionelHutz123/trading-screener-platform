#!/usr/bin/env python3
"""
Start HutzTrades Live Trading Platform with Streaming & Pattern Recognition
This starts the complete system ready for paper trading
"""

import asyncio
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Set up environment variables for Alpaca API"""
    # Paper trading credentials
    os.environ['APCA_API_KEY_ID'] = 'PK463DCZLB0H1M8TG3DN'
    os.environ['APCA_API_SECRET_KEY'] = 'UNWYjiMmOhCdFIhFvKIXNK0AtdBbFUMDs6w1vVZq'
    os.environ['APCA_API_BASE_URL'] = 'https://paper-api.alpaca.markets'
    
    # Set production environment
    os.environ['ENV'] = 'development'  # Keep docs available for testing
    os.environ['PORT'] = '8080'
    
    logger.info("✅ Environment variables configured for paper trading")

def main():
    """Main function to start the trading platform"""
    logger.info("🚀 Starting HutzTrades Live Trading Platform")
    logger.info("📊 Paper Trading Mode with Real-time Pattern Recognition")
    
    # Setup environment
    setup_environment()
    
    # Import and start the API
    try:
        from app_platform_api import app
        import uvicorn
        
        logger.info("🌐 Starting web server...")
        logger.info("📡 Live streaming endpoints available:")
        logger.info("   • GET /api/stream/status - Check streaming status")
        logger.info("   • POST /api/stream/start - Start live data feed")
        logger.info("   • GET /api/stream/signals - Get live trading signals")
        logger.info("   • WebSocket /ws/stream - Real-time updates")
        logger.info("   • GET /docs - API documentation")
        
        logger.info("🎯 Pattern Recognition Features:")
        logger.info("   • Flag patterns (bullish/bearish)")
        logger.info("   • Order block detection")
        logger.info("   • Fair value gaps (FVG)")
        logger.info("   • Change of character (CHoCH)")
        logger.info("   • Swing high/low detection")
        logger.info("   • Confluence signal generation")
        
        logger.info("💡 To test the system:")
        logger.info("   1. Open browser: http://localhost:8080")
        logger.info("   2. Start streaming: POST http://localhost:8080/api/stream/start")
        logger.info("   3. Monitor signals: GET http://localhost:8080/api/stream/signals")
        logger.info("   4. WebSocket: ws://localhost:8080/ws/stream")
        
        # Start the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8080,
            log_level="info",
            access_log=False  # Reduce noise since we have our own logging
        )
        
    except KeyboardInterrupt:
        logger.info("👋 Shutting down HutzTrades platform")
    except Exception as e:
        logger.error(f"❌ Failed to start platform: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)