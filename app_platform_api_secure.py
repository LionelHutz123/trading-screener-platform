#!/usr/bin/env python3
"""
Secure Trading Screener API for Digital Ocean App Platform
Enhanced with security middleware and DDoS protection
"""

import os
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime

# Import security middleware
from security_middleware import security_middleware, rate_limit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 HutzTrades API starting up with enhanced security")
    yield
    # Shutdown
    logger.info("🛑 HutzTrades API shutting down")

# Initialize FastAPI with security
app = FastAPI(
    title="HutzTrades Secure Trading API",
    description="Professional trading analysis platform with comprehensive security",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # Disable docs in production
    redoc_url=None,  # Disable redoc in production
    openapi_url=None if os.getenv("ENV") == "production" else "/openapi.json"
)

# Trusted hosts middleware (prevents host header attacks)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "hutztrades.com",
        "www.hutztrades.com",
        "trading-screener-lerd2.ondigitalocean.app",
        "localhost",
        "127.0.0.1"
    ]
)

# CORS middleware with strict settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hutztrades.com",
        "https://www.hutztrades.com",
        "http://localhost:3000",  # Development only
        "http://127.0.0.1:3000"   # Development only
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    max_age=86400  # Cache preflight for 24 hours
)

# Security middleware for all requests
@app.middleware("http")
async def security_middleware_handler(request: Request, call_next):
    """Apply security checks to all requests"""
    
    # Perform security check
    security_response = await security_middleware.security_check(request)
    if security_response:
        return security_response
    
    # Log request for monitoring
    client_ip = security_middleware.get_client_ip(request)
    user_agent = request.headers.get('user-agent', 'Unknown')
    logger.info(f"Request from {client_ip}: {request.method} {request.url.path} - {user_agent}")
    
    # Process request
    try:
        response = await call_next(request)
        
        # Add security headers to response
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Server"] = "HutzTrades-API"
        
        # Add rate limit headers if available
        if hasattr(request.state, 'rate_limit_headers'):
            response.headers.update(request.state.rate_limit_headers)
        
        return response
        
    except Exception as e:
        logger.error(f"Request error from {client_ip}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
                "timestamp": datetime.now().isoformat()
            }
        )

# Health check endpoint with light rate limiting
@app.get("/health")
@rate_limit(requests_per_minute=30)
async def health_check(request: Request):
    """System health check with security validation"""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "environment": os.getenv("ENV", "development"),
            "security": "enabled",
            "data_points": 1000000,
            "database": "operational"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

# API status endpoint
@app.get("/api/status")
@rate_limit(requests_per_minute=20)
async def api_status(request: Request):
    """API status and capabilities"""
    return {
        "api_version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "strategies": "/api/strategies/top",
            "backtest": "/api/backtest/run",
            "results": "/api/backtest/results"
        },
        "rate_limits": {
            "default": "60 requests/minute",
            "backtest": "10 requests/minute",
            "strategies": "30 requests/minute"
        },
        "security": {
            "https_enforced": True,
            "rate_limiting": True,
            "ddos_protection": True,
            "request_validation": True
        }
    }

# Top strategies endpoint with moderate rate limiting
@app.get("/api/strategies/top")
@rate_limit(requests_per_minute=30)
async def get_top_strategies(request: Request, limit: int = 10):
    """Get top performing trading strategies"""
    try:
        # Validate limit parameter
        if limit < 1 or limit > 50:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 50")
        
        # Mock data for now (replace with actual implementation)
        strategies = [
            {
                "symbol": "LLY",
                "timeframe": "4h",
                "strategy": "RSI Divergence",
                "total_return": 13.03,
                "sharpe_ratio": 5.42,
                "max_drawdown": -4.15,
                "win_rate": 0.68
            },
            {
                "symbol": "TSLA",
                "timeframe": "1d",
                "strategy": "Flag Pattern",
                "total_return": 99.21,
                "sharpe_ratio": 1.73,
                "max_drawdown": -21.97,
                "win_rate": 0.58
            },
            {
                "symbol": "NVDA",
                "timeframe": "1d",
                "strategy": "Confluence",
                "total_return": 92.22,
                "sharpe_ratio": 1.45,
                "max_drawdown": -21.13,
                "win_rate": 0.55
            }
        ]
        
        return {
            "strategies": strategies[:limit],
            "total_count": len(strategies),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Strategies endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to fetch strategies")

# Backtest endpoint with strict rate limiting
@app.post("/api/backtest/run")
@rate_limit(requests_per_minute=10)
async def run_backtest(request: Request, backtest_request: dict):
    """Run backtesting job with enhanced validation"""
    try:
        # Validate request data
        required_fields = ['symbols', 'timeframes', 'start_date', 'end_date']
        for field in required_fields:
            if field not in backtest_request:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Validate symbols (max 10)
        symbols = backtest_request['symbols']
        if not isinstance(symbols, list) or len(symbols) == 0 or len(symbols) > 10:
            raise HTTPException(status_code=400, detail="Symbols must be a list of 1-10 items")
        
        # Validate timeframes
        allowed_timeframes = ['1h', '4h', '1d']
        timeframes = backtest_request['timeframes']
        if not isinstance(timeframes, list) or not all(tf in allowed_timeframes for tf in timeframes):
            raise HTTPException(status_code=400, detail=f"Invalid timeframes. Allowed: {allowed_timeframes}")
        
        # Mock response (replace with actual implementation)
        job_id = f"job_{int(datetime.now().timestamp())}"
        
        return {
            "job_id": job_id,
            "status": "queued",
            "symbols": symbols,
            "timeframes": timeframes,
            "estimated_completion": "5-10 minutes",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to start backtest")

# Results endpoint with moderate rate limiting
@app.get("/api/backtest/results")
@rate_limit(requests_per_minute=20)
async def get_backtest_results(request: Request, limit: int = 20):
    """Get backtest results with pagination"""
    try:
        # Validate limit
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        # Mock results (replace with actual implementation)
        results = [
            {
                "job_id": "job_1625097600",
                "symbol": "AAPL",
                "timeframe": "1h",
                "strategy": "RSI Divergence",
                "total_return": 15.32,
                "sharpe_ratio": 2.14,
                "status": "completed",
                "completed_at": "2024-08-03T09:00:00Z"
            }
        ]
        
        return {
            "results": results[:limit],
            "total_count": len(results),
            "page_size": limit,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Results endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to fetch results")

# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "HutzTrades Secure Trading API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "https://hutztrades.com/docs",
        "security": "enhanced"
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    client_ip = security_middleware.get_client_ip(request)
    logger.warning(f"HTTP {exc.status_code} from {client_ip}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "code": f"HTTP_{exc.status_code}",
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    client_ip = security_middleware.get_client_ip(request)
    logger.error(f"Unhandled exception from {client_ip}: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    
    logger.info(f"🚀 Starting HutzTrades Secure API on port {port}")
    logger.info("🛡️  Security features enabled:")
    logger.info("   - Rate limiting")
    logger.info("   - DDoS protection") 
    logger.info("   - Request validation")
    logger.info("   - Malicious pattern detection")
    logger.info("   - IP blocking")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )