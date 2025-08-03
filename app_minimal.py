#!/usr/bin/env python3
"""
Minimal HutzTrades API - Fallback version for deployment issues
"""

import os
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="HutzTrades Minimal API",
    description="Minimal trading platform API - Streaming features loading...",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    try:
        with open("index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return {
            "message": "HutzTrades API",
            "status": "minimal_mode",
            "note": "Full streaming features loading...",
            "timestamp": datetime.now().isoformat()
        }

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "mode": "minimal",
        "streaming": "loading",
        "security": {"enabled": True},
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/status")
async def api_status():
    """API status"""
    return {
        "api": "operational",
        "mode": "minimal",
        "streaming": "initializing",
        "pattern_recognition": "loading",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/stream/status")
async def stream_status():
    """Stream status - minimal version"""
    return {
        "stream_status": "initializing",
        "message": "Streaming service starting up...",
        "features": [
            "Real-time data streaming",
            "Pattern recognition",
            "Live signal generation"
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/stream/start")
async def start_stream():
    """Start streaming - placeholder"""
    return {
        "status": "initializing",
        "message": "Streaming service is loading. Please try again in a few minutes.",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/stream/signals")
async def get_signals():
    """Get signals - placeholder"""
    return {
        "signals": [],
        "count": 0,
        "message": "Signal generation starting up...",
        "timestamp": datetime.now().isoformat()
    }

# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Service temporarily unavailable",
            "message": "Full streaming features are loading",
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)