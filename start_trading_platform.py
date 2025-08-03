#!/usr/bin/env python3
"""
Production startup script for HutzTrades with full streaming capabilities
"""

import os
import sys
import logging
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Setup environment variables"""
    # Alpaca paper trading
    os.environ['APCA_API_KEY_ID'] = 'PK463DCZLB0H1M8TG3DN'
    os.environ['APCA_API_SECRET_KEY'] = 'UNWYjiMmOhCdFIhFvKIXNK0AtdBbFUMDs6w1vVZq'
    os.environ['APCA_API_BASE_URL'] = 'https://paper-api.alpaca.markets'
    os.environ['ENV'] = 'development'
    os.environ['PORT'] = '8080'
    
def start_with_streaming():
    """Start the full API with streaming capabilities"""
    try:
        logger.info("🚀 Starting HutzTrades with Full Streaming...")
        
        # Try to import the full API
        from app_platform_api import app
        import uvicorn
        
        logger.info("✅ Full streaming API loaded successfully")
        logger.info("🌐 Server starting on http://localhost:8080")
        logger.info("📡 Available endpoints:")
        logger.info("   • GET / - Dashboard")
        logger.info("   • GET /health - System health")
        logger.info("   • GET /api/stream/status - Streaming status")
        logger.info("   • POST /api/stream/start - Start live streaming")
        logger.info("   • GET /api/stream/signals - Live signals")
        logger.info("   • WebSocket /ws/stream - Real-time updates")
        logger.info("   • GET /docs - API documentation")
        
        # Start the server
        uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
        
    except ImportError as e:
        logger.error(f"❌ Import error: {str(e)}")
        logger.info("💡 Falling back to basic API...")
        start_basic_api()
    except Exception as e:
        logger.error(f"❌ Streaming startup failed: {str(e)}")
        logger.info("💡 Falling back to basic API...")
        start_basic_api()

def start_basic_api():
    """Start basic API without streaming (fallback)"""
    try:
        logger.info("🔧 Starting basic API (no streaming)...")
        
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        import uvicorn
        
        app = FastAPI(title="HutzTrades Basic API")
        
        @app.get("/")
        async def root():
            return {"message": "HutzTrades API", "mode": "basic", "status": "operational"}
        
        @app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "mode": "basic_api",
                "streaming": "not_available"
            }
        
        @app.get("/api/status")
        async def api_status():
            return {
                "api": "operational",
                "streaming": "unavailable",
                "pattern_recognition": "offline",
                "note": "Basic mode - restart to try full streaming"
            }
        
        logger.info("✅ Basic API ready")
        logger.info("🌐 Server: http://localhost:8080")
        logger.info("📚 Docs: http://localhost:8080/docs")
        
        uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
        
    except Exception as e:
        logger.error(f"❌ Basic API startup failed: {str(e)}")
        raise

def main():
    """Main startup function"""
    logger.info("🎯 HutzTrades Trading Platform Startup")
    
    # Setup environment
    setup_environment()
    
    try:
        # Try full streaming first
        start_with_streaming()
    except KeyboardInterrupt:
        logger.info("👋 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ All startup methods failed: {str(e)}")
        logger.info("💡 Try installing missing dependencies:")
        logger.info("   pip install fastapi uvicorn pandas numpy requests alpaca-trade-api")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)