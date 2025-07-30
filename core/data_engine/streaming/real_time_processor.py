import logging
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, timezone
from core.data_engine.historical.sql_database import SQLDatabaseHandler
from core.ta_engine.patterns.flag_pattern_detector import FlagPatternDetector
from core.ta_engine.patterns.fvg_detector import FVGDetector
from core.ta_engine.order_blocks.order_flow_analyzer import OrderFlowAnalyzer

class RealTimeProcessor:
    """Process real-time market data and run strategy screeners"""
    
    def __init__(self, db_handler: SQLDatabaseHandler):
        self.db_handler = db_handler
        self.logger = logging.getLogger(__name__)
        
        # Initialize strategy detectors
        self.flag_detector = FlagPatternDetector()
        self.fvg_detector = FVGDetector()
        self.order_flow = OrderFlowAnalyzer()
        
        # Cache for real-time bars
        self.bar_cache: Dict[str, pd.DataFrame] = {}
        self.latest_signals: Dict[str, List[Dict]] = {}
        
    async def process_trade(self, data: Dict):
        """Process real-time trade data"""
        symbol = data.get('S')  # Symbol
        price = data.get('p')   # Price
        size = data.get('s')    # Size
        timestamp = pd.Timestamp(data.get('t'), unit='ns', tz=timezone.utc)
        
        # Store trade in database
        trade_data = pd.DataFrame({
            'timestamp': [timestamp],
            'symbol': [symbol],
            'price': [price],
            'size': [size]
        })
        self.db_handler.store_trades(trade_data)
        
    async def process_bar(self, data: Dict):
        """Process real-time bar data"""
        symbol = data.get('S')
        timestamp = pd.Timestamp(data.get('t'), unit='ns', tz=timezone.utc)
        
        bar_data = pd.DataFrame({
            'timestamp': [timestamp],
            'symbol': [symbol],
            'open': [data.get('o')],
            'high': [data.get('h')],
            'low': [data.get('l')],
            'close': [data.get('c')],
            'volume': [data.get('v')]
        })
        
        # Update bar cache
        if symbol not in self.bar_cache:
            # Load recent historical data
            historical_data = self.db_handler.get_bars(
                symbol=symbol,
                timeframe='1m',
                limit=100  # Last 100 bars
            )
            self.bar_cache[symbol] = historical_data
        
        # Append new bar
        self.bar_cache[symbol] = pd.concat([
            self.bar_cache[symbol],
            bar_data
        ]).sort_index().tail(100)  # Keep last 100 bars
        
        # Store bar in database
        self.db_handler.store_bars(symbol, '1m', bar_data)
        
        # Run strategy screeners
        await self.run_screeners(symbol)
        
    async def run_screeners(self, symbol: str):
        """Run all strategy screeners on updated data"""
        try:
            data = self.bar_cache[symbol]
            
            # Run detectors
            flag_patterns = self.flag_detector.detect(data)
            fvg_patterns = self.fvg_detector.detect(data)
            
            # Analyze order flow
            order_flow_analysis = self.order_flow.analyze({
                'order_blocks': [],  # Add order block detection
                'fvg': fvg_patterns,
                'swing_failures': []  # Add swing failure detection
            })
            
            # Store latest signals
            self.latest_signals[symbol] = {
                'timestamp': datetime.now(timezone.utc),
                'flag_patterns': flag_patterns,
                'fvg_patterns': fvg_patterns,
                'order_flow': order_flow_analysis
            }
            
            # Log new signals
            if flag_patterns or fvg_patterns:
                self.logger.info(f"New signals for {symbol}:")
                if flag_patterns:
                    self.logger.info(f"Flag patterns: {flag_patterns}")
                if fvg_patterns:
                    self.logger.info(f"FVG patterns: {fvg_patterns}")
                self.logger.info(f"Order flow bias: {order_flow_analysis.get('market_bias', {})}")
                
        except Exception as e:
            self.logger.error(f"Error running screeners for {symbol}: {str(e)}")
            
    def get_latest_signals(self, symbol: Optional[str] = None) -> Dict:
        """Get latest signals for one or all symbols"""
        if symbol:
            return self.latest_signals.get(symbol, {})
        return self.latest_signals 