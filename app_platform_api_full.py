#!/usr/bin/env python3
"""
Trading Screener API for Digital Ocean App Platform
Optimized for serverless deployment with health checks and backtesting endpoints
"""

import os
import asyncio
import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime, timedelta
import json

# Import our core modules
from core.data_engine.duckdb_handler import DuckDBHandler
from core.backtesting.backtest_engine import BacktestEngine, BacktestConfig
from core.ta_engine.unified_strategy_engine import UnifiedStrategyEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Trading Screener API",
    description="High-performance trading analysis and backtesting platform",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
db_handler = None
backtest_engine = None
strategy_engine = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global db_handler, backtest_engine, strategy_engine
    
    logger.info("🚀 Starting Trading Screener API...")
    
    try:
        # Initialize database
        db_path = os.getenv("DATABASE_PATH", "/app/data/trading_data.duckdb")
        db_handler = DuckDBHandler(db_path)
        logger.info(f"✅ Database initialized: {db_path}")
        
        # Initialize backtesting engine
        config = BacktestConfig(
            initial_capital=100000.0,
            position_size_pct=0.1,
            stop_loss_pct=0.02,
            take_profit_pct=0.04,
            min_signal_strength=0.6
        )
        backtest_engine = BacktestEngine(db_handler, config)
        logger.info("✅ Backtesting engine initialized")
        
        # Initialize strategy engine
        strategy_engine = UnifiedStrategyEngine()
        logger.info("✅ Strategy engine initialized")
        
        logger.info("🎯 Trading Screener API ready!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global db_handler
    if db_handler:
        db_handler.close()
    logger.info("👋 Trading Screener API shutdown complete")

@app.get("/health")
async def health_check():
    """Health check endpoint for App Platform"""
    try:
        # Test database connection
        if db_handler:
            count = db_handler.execute_query("SELECT COUNT(*) as count FROM price_bars").iloc[0]['count']
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database": "connected",
                "data_points": count,
                "version": "2.0.0"
            }
        else:
            return {"status": "initializing", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.get("/api/status")
async def get_status():
    """Get detailed API status"""
    try:
        stats = {}
        if db_handler:
            # Get data statistics
            stats["symbols"] = db_handler.execute_query(
                "SELECT COUNT(DISTINCT symbol) as count FROM price_bars"
            ).iloc[0]['count'] if db_handler else 0
            
            stats["timeframes"] = db_handler.execute_query(
                "SELECT COUNT(DISTINCT timeframe) as count FROM price_bars"
            ).iloc[0]['count'] if db_handler else 0
            
            stats["total_bars"] = db_handler.execute_query(
                "SELECT COUNT(*) as count FROM price_bars"
            ).iloc[0]['count'] if db_handler else 0
        
        return {
            "status": "active",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": "connected" if db_handler else "disconnected",
                "backtesting": "ready" if backtest_engine else "not_ready",
                "strategy_engine": "ready" if strategy_engine else "not_ready"
            },
            "data_stats": stats,
            "environment": os.getenv("ENV", "development")
        }
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backtest/run")
async def run_backtest(
    background_tasks: BackgroundTasks,
    symbols: list = ["AAPL", "MSFT", "GOOGL"],
    timeframes: list = ["1h", "4h"],
    start_date: str = "2023-01-01",
    end_date: str = "2024-01-01"
):
    """Run comprehensive backtesting"""
    if not backtest_engine:
        raise HTTPException(status_code=503, detail="Backtesting engine not ready")
    
    try:
        # Start backtesting in background
        background_tasks.add_task(
            run_comprehensive_backtest,
            symbols, timeframes, start_date, end_date
        )
        
        return {
            "status": "started",
            "message": "Backtesting job started in background",
            "parameters": {
                "symbols": symbols,
                "timeframes": timeframes,
                "start_date": start_date,
                "end_date": end_date
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Backtest failed to start: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backtest/results")
async def get_backtest_results():
    """Get latest backtesting results"""
    try:
        if not db_handler:
            raise HTTPException(status_code=503, detail="Database not ready")
        
        # Get recent backtest results
        results = db_handler.execute_query("""
            SELECT strategy_name, symbol, timeframe, 
                   total_return, win_rate, sharpe_ratio, max_drawdown,
                   created_at
            FROM backtest_results 
            ORDER BY created_at DESC 
            LIMIT 50
        """)
        
        if results.empty:
            return {"results": [], "message": "No backtest results found"}
        
        return {
            "results": results.to_dict('records'),
            "count": len(results),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/strategies/top")
async def get_top_strategies(limit: int = 10):
    """Get top performing strategies"""
    try:
        if not db_handler:
            raise HTTPException(status_code=503, detail="Database not ready")
        
        # Get top strategies by Sharpe ratio
        top_strategies = db_handler.execute_query(f"""
            SELECT strategy_name, symbol, timeframe,
                   total_return, win_rate, sharpe_ratio, max_drawdown
            FROM backtest_results 
            WHERE sharpe_ratio > 1.0 AND total_return > 0.05
            ORDER BY sharpe_ratio DESC 
            LIMIT {limit}
        """)
        
        return {
            "strategies": top_strategies.to_dict('records') if not top_strategies.empty else [],
            "count": len(top_strategies),
            "criteria": "Sharpe Ratio > 1.0, Total Return > 5%",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get top strategies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_comprehensive_backtest(symbols, timeframes, start_date, end_date):
    """Background task for comprehensive backtesting"""
    logger.info(f"🚀 Starting comprehensive backtest: {symbols} {timeframes}")
    
    try:
        from datetime import datetime
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        results = []
        
        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    logger.info(f"📊 Running backtest: {symbol} {timeframe}")
                    result = backtest_engine.run_backtest(symbol, timeframe, start_dt, end_dt)
                    
                    if result:
                        results.append({
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "total_return": result.total_return,
                            "win_rate": result.win_rate,
                            "sharpe_ratio": result.sharpe_ratio,
                            "max_drawdown": result.max_drawdown,
                            "total_trades": result.total_trades
                        })
                        logger.info(f"✅ {symbol} {timeframe}: {result.win_rate:.1%} win rate, {result.sharpe_ratio:.2f} Sharpe")
                        
                except Exception as e:
                    logger.error(f"❌ Backtest failed for {symbol} {timeframe}: {str(e)}")
                    continue
        
        logger.info(f"🎉 Comprehensive backtest completed! {len(results)} results")
        
        # Save results summary
        if results:
            summary_path = "/app/data/backtest_summary.json"
            with open(summary_path, 'w') as f:
                json.dump({
                    "timestamp": datetime.utcnow().isoformat(),
                    "parameters": {
                        "symbols": symbols,
                        "timeframes": timeframes,
                        "start_date": start_date,
                        "end_date": end_date
                    },
                    "results": results,
                    "summary": {
                        "total_results": len(results),
                        "avg_win_rate": sum(r["win_rate"] for r in results) / len(results),
                        "avg_sharpe": sum(r["sharpe_ratio"] for r in results) / len(results),
                        "best_performer": max(results, key=lambda x: x["sharpe_ratio"])
                    }
                }, f, indent=2)
            
    except Exception as e:
        logger.error(f"❌ Comprehensive backtest failed: {str(e)}")

if __name__ == "__main__":
    # Run with uvicorn for App Platform
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "app_platform_api:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )