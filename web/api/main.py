# -*- coding: utf-8 -*-
import asyncio
import sys
import io
import pandas as pd
import alpaca_trade_api as tradeapi
from alpaca_trade_api.stream import Stream
import json
import asyncio
from fastapi import FastAPI, Request, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from stock_screener.core.ta_engine.order_blocks.order_block_detector import OrderBlockDetector
from core.ta_engine.divergences.rsi_divergence import RSIDivergenceStrategy
from core.ta_engine.patterns.flag_pattern import FlagPatternDetector
from core.data_engine.historical.sql_database import SQLDatabaseHandler
from config import Config

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = FastAPI(title="Stock Screener API", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
# Initialize Alpaca WebSocket client
alpaca = tradeapi.REST(
    key_id='PK463DCZLB0H1M8TG3DN',
    secret_key='UNWYjiMmOhCdFIhFvKIXNK0AtdBbFUMDs6w1vVZq',
    base_url='https://paper-api.alpaca.markets'
)
stream = alpaca.stream

detector = OrderBlockDetector()
rsi_divergence = RSIDivergenceStrategy()
flag_detector = FlagPatternDetector()
db_handler = SQLDatabaseHandler(Config.DATABASE_PATH)

active_connections = set()

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    with open("web/templates/dashboard.html") as f:
        return HTMLResponse(content=f.read())

@app.websocket("/ws/market-data")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        # Alpaca async message handler
        async def handle_msg(msg):
            if msg.trade:
                await websocket.send_json({
                    "symbol": msg.symbol,
                    "price": msg.price,
                    "size": msg.size,
                    "timestamp": msg.timestamp
                })

        # Subscribe to all symbols from our database
        symbols = db_handler.get_all_symbols()
        await alpaca.subscribe_trades(handle_msg, *symbols)

        # Keep connection alive
        while True:
            await asyncio.sleep(10)
            await websocket.send_json({"type": "heartbeat"})

    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        active_connections.remove(websocket)
        await alpaca.unsubscribe_trades()
        await websocket.close()

@app.get("/full-analysis/{symbol}/{timeframe}")
async def full_analysis(symbol: str, timeframe: str):
    try:
        data = db_handler.load_data(symbol, timeframe)
        return {
            "symbol": symbol,
            "timestamps": data['timestamp'].tolist(),
            "opens": data['open'].tolist(),
            "highs": data['high'].tolist(),
            "lows": data['low'].tolist(),
            "closes": data['close'].tolist(),
            "order_blocks": detector.detect(data),
            "rsi_divergence": rsi_divergence.analyze(data),
            "flag_patterns": flag_detector.detect(data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "OK", "version": "1.0.0"}