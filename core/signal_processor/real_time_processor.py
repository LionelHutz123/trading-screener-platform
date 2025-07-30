import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone, timedelta
import pandas as pd
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from collections import deque

from ..data_engine.duckdb_handler import DuckDBHandler
from ..ta_engine.unified_strategy_engine import UnifiedStrategyEngine, ConfluenceSignal
from ..ta_engine.patterns.base_detector import DetectionResult

logger = logging.getLogger(__name__)

class SignalPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

class SignalStatus(Enum):
    PENDING = "pending"
    TRIGGERED = "triggered"
    EXECUTED = "executed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

@dataclass
class TradingSignal:
    """Represents a trading signal"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str = ""
    timeframe: str = ""
    signal_type: str = ""  # 'bullish', 'bearish', 'neutral'
    pattern_type: str = ""
    priority: SignalPriority = SignalPriority.MEDIUM
    status: SignalStatus = SignalStatus.PENDING
    
    # Trading parameters
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    position_size: Optional[float] = None
    
    # Signal strength and metadata
    confidence: float = 0.0
    strength: float = 0.0
    contributing_signals: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timing
    valid_until: Optional[datetime] = None
    triggered_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "signal_type": self.signal_type,
            "pattern_type": self.pattern_type,
            "priority": self.priority.value,
            "status": self.status.value,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "position_size": self.position_size,
            "confidence": self.confidence,
            "strength": self.strength,
            "contributing_signals": self.contributing_signals,
            "metadata": self.metadata,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None
        }

@dataclass
class ProcessorConfig:
    """Configuration for signal processor"""
    # Analysis settings
    min_confidence: float = 0.6
    min_strength: float = 0.7
    lookback_periods: int = 100
    
    # Signal filtering
    enable_confluence_only: bool = True
    min_confluence_signals: int = 2
    
    # Risk management
    max_concurrent_signals: int = 10
    signal_validity_minutes: int = 30
    
    # Processing settings
    batch_size: int = 5
    processing_interval: int = 60  # seconds
    
    # Priority thresholds
    critical_strength: float = 0.9
    high_strength: float = 0.8
    medium_strength: float = 0.7
    
    # Cooldown settings
    signal_cooldown_minutes: int = 15  # Prevent duplicate signals

class RealTimeSignalProcessor:
    """Processes market data in real-time to generate trading signals"""
    
    def __init__(self, db_handler: DuckDBHandler, config: ProcessorConfig = None):
        self.db_handler = db_handler
        self.config = config or ProcessorConfig()
        self.logger = logger
        
        # Strategy engine
        self.strategy_engine = UnifiedStrategyEngine()
        
        # Signal management
        self.active_signals: Dict[str, TradingSignal] = {}
        self.signal_history: deque = deque(maxlen=1000)
        self.signal_cooldown: Dict[str, datetime] = {}  # symbol_timeframe -> last_signal_time
        
        # Callbacks
        self.signal_callbacks: List[Callable[[TradingSignal], None]] = []
        
        # Processing state
        self.is_running = False
        self.processing_task = None
        self.cleanup_task = None
        
        # Statistics
        self.stats = {
            "total_signals": 0,
            "active_signals": 0,
            "triggered_signals": 0,
            "expired_signals": 0,
            "signals_by_priority": {p.name: 0 for p in SignalPriority}
        }
    
    async def start(self):
        """Start the signal processor"""
        try:
            self.is_running = True
            
            # Start processing loop
            self.processing_task = asyncio.create_task(self._processing_loop())
            
            # Start cleanup loop
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self.logger.info("Real-time signal processor started")
            
        except Exception as e:
            self.logger.error(f"Error starting signal processor: {str(e)}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the signal processor"""
        self.is_running = False
        
        # Cancel tasks
        if self.processing_task:
            self.processing_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Save active signals
        await self._save_active_signals()
        
        self.logger.info("Signal processor stopped")
    
    async def process_symbol(self, symbol: str, timeframe: str) -> List[TradingSignal]:
        """Process a specific symbol/timeframe combination"""
        try:
            # Check cooldown
            if self._is_in_cooldown(symbol, timeframe):
                return []
            
            # Get recent data
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(hours=24)
            
            data = await asyncio.to_thread(
                self.db_handler.get_bars,
                symbol,
                timeframe,
                start_date,
                end_date
            )
            
            if len(data) < self.config.lookback_periods:
                return []
            
            # Run analysis
            analysis_results = await asyncio.to_thread(
                self.strategy_engine.run_comprehensive_analysis,
                data.tail(self.config.lookback_periods)
            )
            
            # Generate signals
            signals = await self._generate_signals(symbol, timeframe, analysis_results, data)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error processing {symbol} {timeframe}: {str(e)}")
            return []
    
    async def _processing_loop(self):
        """Main processing loop"""
        while self.is_running:
            try:
                # Get symbols to process
                symbols = await self._get_symbols_to_process()
                
                # Process in batches
                for i in range(0, len(symbols), self.config.batch_size):
                    batch = symbols[i:i + self.config.batch_size]
                    
                    # Process batch concurrently
                    tasks = []
                    for symbol, timeframe in batch:
                        tasks.append(self.process_symbol(symbol, timeframe))
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Handle results
                    for (symbol, timeframe), result in zip(batch, results):
                        if isinstance(result, Exception):
                            self.logger.error(f"Error processing {symbol} {timeframe}: {str(result)}")
                        else:
                            for signal in result:
                                await self._handle_new_signal(signal)
                
                # Sleep before next cycle
                await asyncio.sleep(self.config.processing_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in processing loop: {str(e)}")
                await asyncio.sleep(10)
    
    async def _cleanup_loop(self):
        """Cleanup expired signals"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = datetime.now(timezone.utc)
                expired_signals = []
                
                # Check for expired signals
                for signal_id, signal in self.active_signals.items():
                    if signal.valid_until and signal.valid_until < current_time:
                        signal.status = SignalStatus.EXPIRED
                        expired_signals.append(signal_id)
                        self.stats["expired_signals"] += 1
                
                # Remove expired signals
                for signal_id in expired_signals:
                    expired_signal = self.active_signals.pop(signal_id)
                    self.signal_history.append(expired_signal)
                    
                    # Notify callbacks
                    await self._notify_signal_update(expired_signal)
                
                # Update stats
                self.stats["active_signals"] = len(self.active_signals)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {str(e)}")
    
    async def _generate_signals(self, symbol: str, timeframe: str, 
                               analysis_results: Dict[str, Any], 
                               data: pd.DataFrame) -> List[TradingSignal]:
        """Generate trading signals from analysis results"""
        signals = []
        current_price = data['close'].iloc[-1]
        
        # Process confluence signals
        if self.config.enable_confluence_only:
            for confluence in analysis_results.get('confluence', []):
                if confluence.strength >= self.config.min_strength:
                    signal = self._create_signal_from_confluence(
                        symbol, timeframe, confluence, current_price
                    )
                    signals.append(signal)
        else:
            # Process all pattern signals
            for pattern_type, patterns in analysis_results.get('patterns', {}).items():
                for pattern in patterns:
                    if pattern.confidence >= self.config.min_confidence:
                        signal = self._create_signal_from_pattern(
                            symbol, timeframe, pattern, pattern_type, current_price
                        )
                        signals.append(signal)
            
            # Process divergence signals
            for div_type, divergences in analysis_results.get('divergences', {}).items():
                for divergence in divergences:
                    if divergence.confidence >= self.config.min_confidence:
                        signal = self._create_signal_from_pattern(
                            symbol, timeframe, divergence, div_type, current_price
                        )
                        signals.append(signal)
        
        return signals
    
    def _create_signal_from_confluence(self, symbol: str, timeframe: str,
                                     confluence: ConfluenceSignal,
                                     current_price: float) -> TradingSignal:
        """Create trading signal from confluence"""
        # Determine priority based on strength
        priority = self._get_priority(confluence.strength)
        
        # Calculate validity period
        valid_minutes = self.config.signal_validity_minutes
        if priority == SignalPriority.CRITICAL:
            valid_minutes *= 2  # Longer validity for critical signals
        
        signal = TradingSignal(
            symbol=symbol,
            timeframe=timeframe,
            signal_type=confluence.signal_type,
            pattern_type="Confluence",
            priority=priority,
            entry_price=confluence.entry_price,
            stop_loss=confluence.stop_loss,
            take_profit=confluence.take_profit,
            confidence=confluence.strength,
            strength=confluence.strength,
            contributing_signals=confluence.signals,
            metadata={
                "signal_count": len(confluence.signals),
                "current_price": current_price,
                "price_distance": abs(current_price - confluence.entry_price) / current_price
            },
            valid_until=datetime.now(timezone.utc) + timedelta(minutes=valid_minutes)
        )
        
        return signal
    
    def _create_signal_from_pattern(self, symbol: str, timeframe: str,
                                  pattern: DetectionResult, pattern_type: str,
                                  current_price: float) -> TradingSignal:
        """Create trading signal from pattern"""
        # Determine signal type from pattern
        signal_type = self._classify_signal_type(pattern.pattern_type)
        
        # Determine priority
        priority = self._get_priority(pattern.confidence)
        
        signal = TradingSignal(
            symbol=symbol,
            timeframe=timeframe,
            signal_type=signal_type,
            pattern_type=pattern.pattern_type,
            priority=priority,
            entry_price=pattern.entry_price,
            stop_loss=pattern.stop_loss,
            take_profit=pattern.take_profit,
            confidence=pattern.confidence,
            strength=pattern.confidence,
            contributing_signals=[pattern_type],
            metadata={
                "pattern_metadata": pattern.metadata,
                "current_price": current_price,
                "price_distance": abs(current_price - pattern.entry_price) / current_price
            },
            valid_until=datetime.now(timezone.utc) + timedelta(minutes=self.config.signal_validity_minutes)
        )
        
        return signal
    
    def _get_priority(self, strength: float) -> SignalPriority:
        """Determine signal priority based on strength"""
        if strength >= self.config.critical_strength:
            return SignalPriority.CRITICAL
        elif strength >= self.config.high_strength:
            return SignalPriority.HIGH
        elif strength >= self.config.medium_strength:
            return SignalPriority.MEDIUM
        else:
            return SignalPriority.LOW
    
    def _classify_signal_type(self, pattern_type: str) -> str:
        """Classify pattern type as bullish, bearish, or neutral"""
        pattern_lower = pattern_type.lower()
        
        bullish_keywords = ['bull', 'bullish', 'long', 'buy', 'support']
        bearish_keywords = ['bear', 'bearish', 'short', 'sell', 'resistance']
        
        for keyword in bullish_keywords:
            if keyword in pattern_lower:
                return 'bullish'
        
        for keyword in bearish_keywords:
            if keyword in pattern_lower:
                return 'bearish'
        
        return 'neutral'
    
    async def _handle_new_signal(self, signal: TradingSignal):
        """Handle a new trading signal"""
        try:
            # Check if we're at max capacity
            if len(self.active_signals) >= self.config.max_concurrent_signals:
                # Remove lowest priority signal
                lowest_priority_signal = min(
                    self.active_signals.values(),
                    key=lambda s: (s.priority.value, s.strength)
                )
                
                if signal.priority.value < lowest_priority_signal.priority.value:
                    # Remove lowest priority signal
                    self.active_signals.pop(lowest_priority_signal.id)
                    lowest_priority_signal.status = SignalStatus.CANCELLED
                    self.signal_history.append(lowest_priority_signal)
                else:
                    # Skip this signal
                    return
            
            # Add to active signals
            self.active_signals[signal.id] = signal
            
            # Update cooldown
            cooldown_key = f"{signal.symbol}_{signal.timeframe}"
            self.signal_cooldown[cooldown_key] = datetime.now(timezone.utc)
            
            # Update statistics
            self.stats["total_signals"] += 1
            self.stats["active_signals"] = len(self.active_signals)
            self.stats["signals_by_priority"][signal.priority.name] += 1
            
            # Store in database
            await self._store_signal(signal)
            
            # Notify callbacks
            await self._notify_new_signal(signal)
            
            self.logger.info(f"New {signal.priority.name} signal: {signal.symbol} {signal.signal_type} "
                           f"@ {signal.entry_price:.2f} (confidence: {signal.confidence:.2f})")
            
        except Exception as e:
            self.logger.error(f"Error handling new signal: {str(e)}")
    
    async def _store_signal(self, signal: TradingSignal):
        """Store signal in database"""
        try:
            signal_data = {
                'timestamp': signal.timestamp,
                'symbol': signal.symbol,
                'timeframe': signal.timeframe,
                'pattern_type': f"{signal.pattern_type}_{signal.signal_type}",
                'entry_price': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'confidence': signal.confidence,
                'metadata': signal.metadata
            }
            
            await asyncio.to_thread(
                self.db_handler.store_pattern_match,
                signal_data
            )
            
        except Exception as e:
            self.logger.error(f"Error storing signal: {str(e)}")
    
    async def _notify_new_signal(self, signal: TradingSignal):
        """Notify all registered callbacks of new signal"""
        for callback in self.signal_callbacks:
            try:
                await callback(signal)
            except Exception as e:
                self.logger.error(f"Error in signal callback: {str(e)}")
    
    async def _notify_signal_update(self, signal: TradingSignal):
        """Notify callbacks of signal status update"""
        # This would be extended to handle different types of updates
        await self._notify_new_signal(signal)
    
    def _is_in_cooldown(self, symbol: str, timeframe: str) -> bool:
        """Check if symbol/timeframe is in cooldown period"""
        cooldown_key = f"{symbol}_{timeframe}"
        
        if cooldown_key in self.signal_cooldown:
            last_signal_time = self.signal_cooldown[cooldown_key]
            cooldown_end = last_signal_time + timedelta(minutes=self.config.signal_cooldown_minutes)
            
            if datetime.now(timezone.utc) < cooldown_end:
                return True
        
        return False
    
    async def _get_symbols_to_process(self) -> List[tuple[str, str]]:
        """Get list of symbol/timeframe combinations to process"""
        try:
            # Get all available symbols from database
            symbols = await asyncio.to_thread(self.db_handler.get_available_symbols)
            
            # For each symbol, get available timeframes
            symbol_timeframes = []
            for symbol in symbols:
                timeframes = await asyncio.to_thread(
                    self.db_handler.get_available_timeframes,
                    symbol
                )
                
                for timeframe in timeframes:
                    # Only process intraday timeframes for real-time signals
                    if timeframe in ['1m', '5m', '15m', '1h', '4h']:
                        symbol_timeframes.append((symbol, timeframe))
            
            return symbol_timeframes
            
        except Exception as e:
            self.logger.error(f"Error getting symbols to process: {str(e)}")
            return []
    
    async def _save_active_signals(self):
        """Save active signals to database"""
        try:
            for signal in self.active_signals.values():
                await self._store_signal(signal)
        except Exception as e:
            self.logger.error(f"Error saving active signals: {str(e)}")
    
    def register_callback(self, callback: Callable[[TradingSignal], None]):
        """Register a callback for new signals"""
        self.signal_callbacks.append(callback)
    
    def get_active_signals(self, symbol: Optional[str] = None,
                          priority: Optional[SignalPriority] = None) -> List[TradingSignal]:
        """Get active signals with optional filtering"""
        signals = list(self.active_signals.values())
        
        if symbol:
            signals = [s for s in signals if s.symbol == symbol]
        
        if priority:
            signals = [s for s in signals if s.priority == priority]
        
        # Sort by priority and strength
        signals.sort(key=lambda s: (s.priority.value, -s.strength))
        
        return signals
    
    def get_signal_by_id(self, signal_id: str) -> Optional[TradingSignal]:
        """Get specific signal by ID"""
        return self.active_signals.get(signal_id)
    
    def update_signal_status(self, signal_id: str, status: SignalStatus):
        """Update signal status"""
        if signal_id in self.active_signals:
            signal = self.active_signals[signal_id]
            signal.status = status
            
            if status == SignalStatus.TRIGGERED:
                signal.triggered_at = datetime.now(timezone.utc)
                self.stats["triggered_signals"] += 1
            elif status == SignalStatus.EXECUTED:
                signal.executed_at = datetime.now(timezone.utc)
                # Move to history
                self.active_signals.pop(signal_id)
                self.signal_history.append(signal)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processor statistics"""
        return {
            **self.stats,
            "cooldown_symbols": len(self.signal_cooldown),
            "history_size": len(self.signal_history)
        }