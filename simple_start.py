#!/usr/bin/env python3
"""
Simple startup script to diagnose and fix connection issues
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if all required dependencies are installed"""
    logger.info("🔍 Checking dependencies...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'pandas',
        'numpy',
        'requests'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✅ {package}")
        except ImportError:
            missing.append(package)
            logger.error(f"❌ {package} - MISSING")
    
    return missing

def start_minimal_server():
    """Start a minimal FastAPI server without streaming components"""
    logger.info("🚀 Starting minimal server...")
    
    try:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        import uvicorn
        
        # Create minimal app
        app = FastAPI(title="HutzTrades Test Server")
        
        @app.get("/")
        async def root():
            return {"message": "HutzTrades server is running!", "status": "operational"}
        
        @app.get("/health")
        async def health():
            return {"status": "healthy", "timestamp": "2025-08-03"}
        
        @app.get("/test")
        async def test():
            return {
                "server": "running",
                "api": "operational",
                "ready_for": "streaming_integration"
            }
        
        logger.info("🌐 Starting server on http://localhost:8080")
        logger.info("📍 Test endpoints:")
        logger.info("   • http://localhost:8080/ - Root")
        logger.info("   • http://localhost:8080/health - Health check")
        logger.info("   • http://localhost:8080/test - Test endpoint")
        logger.info("   • http://localhost:8080/docs - API docs")
        
        # Start server
        uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
        
    except Exception as e:
        logger.error(f"❌ Server startup failed: {str(e)}")
        raise

def main():
    """Main diagnostic and startup function"""
    logger.info("🔧 HutzTrades Connection Diagnostic Tool")
    
    # Check dependencies
    missing = check_dependencies()
    
    if missing:
        logger.error(f"❌ Missing dependencies: {missing}")
        logger.info("💡 Install with: pip install " + " ".join(missing))
        return 1
    
    logger.info("✅ All dependencies available")
    
    # Set environment variables
    os.environ['APCA_API_KEY_ID'] = 'PK463DCZLB0H1M8TG3DN'
    os.environ['APCA_API_SECRET_KEY'] = 'UNWYjiMmOhCdFIhFvKIXNK0AtdBbFUMDs6w1vVZq'
    os.environ['APCA_API_BASE_URL'] = 'https://paper-api.alpaca.markets'
    
    try:
        start_minimal_server()
    except KeyboardInterrupt:
        logger.info("👋 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)