import asyncio
import logging
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime, timezone
import pandas as pd
from dataclasses import dataclass
from enum import Enum
import json

from alpaca_trade_api import Stream
from alpaca_trade_api.stream import Trade, Bar, Quote

from ..duckdb_handler import DuckDBHandler
from ...ta_engine.unified_strategy_engine import UnifiedStrategyEngine

logger = logging.getLogger(__name__)

class StreamDataType(Enum):
    TRADE = "trade"
    QUOTE = "quote"
    BAR = "bar"
    
@dataclass
class StreamConfig:
    """Configuration for stream handler"""
    api_key: str
    secret_key: str
    base_url: str = "https://data.alpaca.markets"
    data_feed: str = "sip"  # 'sip' or 'iex'
    
    # Buffer settings
    buffer_size: int = 1000
    flush_interval: int = 5  # seconds
    
    # Processing settings
    enable_real_time_analysis: bool = True
    analysis_interval: int = 60  # seconds
    
    # Subscription settings
    max_symbols: int = 100
    reconnect_attempts: int = 5
    reconnect_delay: int = 5  # seconds

@dataclass 
class MarketData:
    """Container for market data"""
    symbol: str
    timestamp: datetime
    data_type: StreamDataType
    price: Optional[float] = None
    volume: Optional[int] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    vwap: Optional[float] = None
    trade_count: Optional[int] = None

class AlpacaStreamHandler:
    """Real-time streaming data handler for Alpaca"""
    
    def __init__(self, config: StreamConfig, db_handler: DuckDBHandler):
        self.config = config
        self.db_handler = db_handler
        self.logger = logger
        
        # Initialize stream
        self.stream = Stream(
            key_id=config.api_key,
            secret_key=config.secret_key,
            base_url=config.base_url,
            data_feed=config.data_feed
        )
        
        # Data buffers
        self.trade_buffer: Dict[str, List[MarketData]] = {}
        self.bar_buffer: Dict[str, List[MarketData]] = {}
        self.quote_buffer: Dict[str, List[MarketData]] = {}
        
        # Callbacks
        self.callbacks: Dict[StreamDataType, List[Callable]] = {
            StreamDataType.TRADE: [],
            StreamDataType.QUOTE: [],
            StreamDataType.BAR: []
        }
        
        # Strategy engine for real-time analysis
        self.strategy_engine = UnifiedStrategyEngine()
        
        # State
        self.subscribed_symbols: set = set()
        self.is_running = False
        self.last_flush = datetime.now()
        self.last_analysis = datetime.now()
        
        # Tasks
        self.flush_task = None
        self.analysis_task = None
        
    async def start(self, symbols: List[str]):
        """Start streaming data for given symbols"""
        try:
            self.is_running = True
            
            # Validate symbols
            if len(symbols) > self.config.max_symbols:
                self.logger.warning(f"Too many symbols ({len(symbols)}), limiting to {self.config.max_symbols}")
                symbols = symbols[:self.config.max_symbols]
            
            # Set up handlers
            self.stream.subscribe_trades(self._handle_trade, *symbols)
            self.stream.subscribe_bars(self._handle_bar, *symbols)
            self.stream.subscribe_quotes(self._handle_quote, *symbols)
            
            self.subscribed_symbols.update(symbols)
            
            # Start background tasks
            self.flush_task = asyncio.create_task(self._flush_loop())
            if self.config.enable_real_time_analysis:
                self.analysis_task = asyncio.create_task(self._analysis_loop())
            
            self.logger.info(f"Started streaming for {len(symbols)} symbols")
            
            # Run stream
            await self.stream.run()
            
        except Exception as e:
            self.logger.error(f"Error starting stream: {str(e)}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop streaming and clean up"""
        self.is_running = False
        
        # Cancel tasks
        if self.flush_task:
            self.flush_task.cancel()
        if self.analysis_task:
            self.analysis_task.cancel()
        
        # Flush remaining data
        await self._flush_all_buffers()
        
        # Close stream
        await self.stream.stop()
        
        self.logger.info("Stream handler stopped")
    
    async def _handle_trade(self, trade: Trade):
        """Handle incoming trade data"""
        try:
            market_data = MarketData(
                symbol=trade.symbol,
                timestamp=pd.Timestamp(trade.timestamp, tz='UTC'),
                data_type=StreamDataType.TRADE,
                price=trade.price,
                volume=trade.size
            )
            
            # Add to buffer
            if trade.symbol not in self.trade_buffer:
                self.trade_buffer[trade.symbol] = []
            self.trade_buffer[trade.symbol].append(market_data)
            
            # Trigger callbacks
            await self._trigger_callbacks(StreamDataType.TRADE, market_data)
            
            # Check buffer size
            if len(self.trade_buffer[trade.symbol]) >= self.config.buffer_size:
                await self._flush_symbol_buffer(trade.symbol, StreamDataType.TRADE)
                
        except Exception as e:
            self.logger.error(f"Error handling trade: {str(e)}")
    
    async def _handle_bar(self, bar: Bar):
        """Handle incoming bar data"""
        try:
            market_data = MarketData(
                symbol=bar.symbol,
                timestamp=pd.Timestamp(bar.timestamp, tz='UTC'),
                data_type=StreamDataType.BAR,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                vwap=getattr(bar, 'vwap', None),
                trade_count=getattr(bar, 'trade_count', None)
            )
            
            # Add to buffer
            if bar.symbol not in self.bar_buffer:
                self.bar_buffer[bar.symbol] = []
            self.bar_buffer[bar.symbol].append(market_data)
            
            # Store immediately for analysis
            await self._store_bar_data(bar.symbol, [market_data])
            
            # Trigger callbacks
            await self._trigger_callbacks(StreamDataType.BAR, market_data)
            
        except Exception as e:
            self.logger.error(f"Error handling bar: {str(e)}")
    
    async def _handle_quote(self, quote: Quote):
        """Handle incoming quote data"""
        try:
            market_data = MarketData(
                symbol=quote.symbol,
                timestamp=pd.Timestamp(quote.timestamp, tz='UTC'),
                data_type=StreamDataType.QUOTE,
                bid=quote.bid_price,
                ask=quote.ask_price,
                bid_size=quote.bid_size,
                ask_size=quote.ask_size
            )
            
            # Add to buffer
            if quote.symbol not in self.quote_buffer:
                self.quote_buffer[quote.symbol] = []
            self.quote_buffer[quote.symbol].append(market_data)
            
            # Trigger callbacks
            await self._trigger_callbacks(StreamDataType.QUOTE, market_data)
            
            # Check buffer size
            if len(self.quote_buffer[quote.symbol]) >= self.config.buffer_size:
                await self._flush_symbol_buffer(quote.symbol, StreamDataType.QUOTE)
                
        except Exception as e:
            self.logger.error(f"Error handling quote: {str(e)}")
    
    async def _flush_loop(self):
        """Periodically flush buffers to database"""
        while self.is_running:
            try:
                await asyncio.sleep(self.config.flush_interval)
                await self._flush_all_buffers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in flush loop: {str(e)}")
    
    async def _analysis_loop(self):
        """Periodically run analysis on recent data"""
        while self.is_running:
            try:
                await asyncio.sleep(self.config.analysis_interval)
                await self._run_real_time_analysis()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in analysis loop: {str(e)}")
    
    async def _flush_all_buffers(self):
        """Flush all data buffers to database"""
        # Flush trade data
        for symbol in list(self.trade_buffer.keys()):
            if self.trade_buffer[symbol]:
                await self._flush_symbol_buffer(symbol, StreamDataType.TRADE)
        
        # Flush quote data  
        for symbol in list(self.quote_buffer.keys()):
            if self.quote_buffer[symbol]:
                await self._flush_symbol_buffer(symbol, StreamDataType.QUOTE)
        
        self.last_flush = datetime.now()
    
    async def _flush_symbol_buffer(self, symbol: str, data_type: StreamDataType):
        """Flush specific symbol buffer to database"""
        try:
            if data_type == StreamDataType.TRADE:
                buffer = self.trade_buffer.get(symbol, [])
                if buffer:
                    await self._store_trade_data(symbol, buffer)
                    self.trade_buffer[symbol] = []
                    
            elif data_type == StreamDataType.QUOTE:
                buffer = self.quote_buffer.get(symbol, [])
                if buffer:
                    await self._store_quote_data(symbol, buffer)
                    self.quote_buffer[symbol] = []
                    
        except Exception as e:
            self.logger.error(f"Error flushing {symbol} {data_type.value} buffer: {str(e)}")
    
    async def _store_trade_data(self, symbol: str, trades: List[MarketData]):
        """Store trade data in database"""
        try:
            # Convert to DataFrame
            df = pd.DataFrame([{
                'timestamp': t.timestamp,
                'price': t.price,
                'volume': t.volume
            } for t in trades])
            
            # Store in database (you may want to create a separate table for tick data)
            # For now, we'll aggregate into 1-minute bars
            if not df.empty:
                bars = df.resample('1T', on='timestamp').agg({
                    'price': ['first', 'max', 'min', 'last'],
                    'volume': 'sum'
                }).dropna()
                
                if not bars.empty:
                    bars.columns = ['open', 'high', 'low', 'close', 'volume']
                    bars.reset_index(inplace=True)
                    
                    # Use existing store_bars method
                    await asyncio.to_thread(
                        self.db_handler.store_bars, 
                        symbol, 
                        '1m', 
                        bars
                    )
                    
        except Exception as e:
            self.logger.error(f"Error storing trade data: {str(e)}")
    
    async def _store_bar_data(self, symbol: str, bars: List[MarketData]):
        """Store bar data in database"""
        try:
            # Convert to DataFrame
            df = pd.DataFrame([{
                'timestamp': b.timestamp,
                'open': b.open,
                'high': b.high,
                'low': b.low,
                'close': b.close,
                'volume': b.volume
            } for b in bars])
            
            if not df.empty:
                # Store in database
                await asyncio.to_thread(
                    self.db_handler.store_bars,
                    symbol,
                    '1m',  # Alpaca streams 1-minute bars
                    df
                )
                
        except Exception as e:
            self.logger.error(f"Error storing bar data: {str(e)}")
    
    async def _store_quote_data(self, symbol: str, quotes: List[MarketData]):
        """Store quote data (bid/ask spread)"""
        # For now, we'll just log the spread
        # You may want to create a separate table for quote data
        try:
            spreads = [(q.ask - q.bid) / q.bid * 100 for q in quotes if q.bid and q.ask]
            if spreads:
                avg_spread = sum(spreads) / len(spreads)
                self.logger.debug(f"{symbol} average spread: {avg_spread:.3f}%")
        except Exception as e:
            self.logger.error(f"Error processing quote data: {str(e)}")
    
    async def _run_real_time_analysis(self):
        """Run technical analysis on recent data"""
        try:
            for symbol in self.subscribed_symbols:
                # Get recent data from database
                end_date = datetime.now(timezone.utc)
                start_date = end_date - pd.Timedelta(days=1)
                
                data = await asyncio.to_thread(
                    self.db_handler.get_bars,
                    symbol,
                    '1m',
                    start_date,
                    end_date
                )
                
                if len(data) > 60:  # Need at least 60 minutes of data
                    # Run analysis
                    analysis_results = await asyncio.to_thread(
                        self.strategy_engine.get_latest_signals,
                        data,
                        lookback_periods=60
                    )
                    
                    # Process any new signals
                    await self._process_signals(symbol, analysis_results)
            
            self.last_analysis = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error in real-time analysis: {str(e)}")
    
    async def _process_signals(self, symbol: str, analysis_results: Dict[str, Any]):
        """Process and store new trading signals"""
        # This will be implemented with the signal processor
        # For now, just log significant signals
        confluence_signals = analysis_results.get('confluence', [])
        if confluence_signals:
            self.logger.info(f"New signals for {symbol}: {len(confluence_signals)} confluence signals")
    
    async def _trigger_callbacks(self, data_type: StreamDataType, market_data: MarketData):
        """Trigger registered callbacks"""
        for callback in self.callbacks.get(data_type, []):
            try:
                await callback(market_data)
            except Exception as e:
                self.logger.error(f"Error in callback: {str(e)}")
    
    def register_callback(self, data_type: StreamDataType, callback: Callable):
        """Register a callback for specific data type"""
        self.callbacks[data_type].append(callback)
    
    async def subscribe_symbols(self, symbols: List[str]):
        """Add additional symbols to subscription"""
        new_symbols = set(symbols) - self.subscribed_symbols
        if new_symbols:
            self.stream.subscribe_trades(self._handle_trade, *new_symbols)
            self.stream.subscribe_bars(self._handle_bar, *new_symbols)
            self.stream.subscribe_quotes(self._handle_quote, *new_symbols)
            self.subscribed_symbols.update(new_symbols)
            self.logger.info(f"Subscribed to {len(new_symbols)} new symbols")
    
    async def unsubscribe_symbols(self, symbols: List[str]):
        """Remove symbols from subscription"""
        remove_symbols = set(symbols) & self.subscribed_symbols
        if remove_symbols:
            self.stream.unsubscribe_trades(*remove_symbols)
            self.stream.unsubscribe_bars(*remove_symbols)
            self.stream.unsubscribe_quotes(*remove_symbols)
            self.subscribed_symbols -= remove_symbols
            self.logger.info(f"Unsubscribed from {len(remove_symbols)} symbols")