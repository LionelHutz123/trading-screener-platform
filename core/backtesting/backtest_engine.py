import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta
import json
from enum import Enum

from ..data_engine.duckdb_handler import DuckDBHandler
from ..ta_engine.unified_strategy_engine import UnifiedStrategyEngine, UnifiedStrategyConfig, ConfluenceSignal

logger = logging.getLogger(__name__)

class SignalType(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

@dataclass
class Trade:
    """Represents a single trade"""
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    signal_type: SignalType
    signal_strength: float
    stop_loss: float
    take_profit: float
    position_size: float
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    # Position sizing
    initial_capital: float = 100000.0
    position_size_pct: float = 0.1  # 10% of capital per trade
    max_positions: int = 5
    
    # Risk management
    stop_loss_pct: float = 0.02  # 2% stop loss
    take_profit_pct: float = 0.04  # 4% take profit
    trailing_stop: bool = False
    trailing_stop_pct: float = 0.01  # 1% trailing stop
    
    # Signal filtering
    min_signal_strength: float = 0.6
    min_confluence_signals: int = 2
    
    # Time-based filters
    min_hold_period: int = 5  # Minimum bars to hold
    max_hold_period: int = 50  # Maximum bars to hold
    
    # Commission and slippage
    commission_pct: float = 0.001  # 0.1% commission
    slippage_pct: float = 0.0005  # 0.05% slippage

@dataclass
class BacktestResult:
    """Results of a backtest"""
    # Performance metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_return: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    
    # Risk metrics
    volatility: float
    var_95: float  # 95% Value at Risk
    max_consecutive_losses: int
    
    # Trade details
    trades: List[Trade]
    equity_curve: pd.Series
    drawdown_curve: pd.Series
    
    # Strategy details
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    parameters: Dict[str, Any]

class BacktestEngine:
    """Comprehensive backtesting engine with advanced features"""
    
    def __init__(self, db_handler: DuckDBHandler, config: BacktestConfig = None):
        self.db_handler = db_handler
        self.config = config or BacktestConfig()
        self.logger = logger
        
    def run_backtest(self, 
                    symbol: str, 
                    timeframe: str, 
                    start_date: datetime, 
                    end_date: datetime,
                    strategy_config: UnifiedStrategyConfig = None) -> BacktestResult:
        """Run comprehensive backtest"""
        
        self.logger.info(f"Starting backtest for {symbol} {timeframe} from {start_date} to {end_date}")
        
        # Load data
        data = self.db_handler.get_bars(symbol, timeframe, start_date, end_date)
        if data.empty:
            raise ValueError(f"No data found for {symbol} {timeframe}")
        
        # Initialize strategy engine
        strategy_engine = UnifiedStrategyEngine(strategy_config)
        
        # Run strategy analysis
        analysis_results = strategy_engine.run_comprehensive_analysis(data)
        
        # Generate signals
        signals = self._generate_trading_signals(data, analysis_results)
        
        # Execute backtest
        trades, equity_curve = self._execute_trades(data, signals)
        
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(trades, equity_curve)
        
        # Create result object
        result = BacktestResult(
            total_trades=performance_metrics['total_trades'],
            winning_trades=performance_metrics['winning_trades'],
            losing_trades=performance_metrics['losing_trades'],
            win_rate=performance_metrics['win_rate'],
            avg_return=performance_metrics['avg_return'],
            total_return=performance_metrics['total_return'],
            max_drawdown=performance_metrics['max_drawdown'],
            sharpe_ratio=performance_metrics['sharpe_ratio'],
            sortino_ratio=performance_metrics['sortino_ratio'],
            volatility=performance_metrics['volatility'],
            var_95=performance_metrics['var_95'],
            max_consecutive_losses=performance_metrics['max_consecutive_losses'],
            trades=trades,
            equity_curve=equity_curve,
            drawdown_curve=performance_metrics['drawdown_curve'],
            strategy_name="Unified Strategy",
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            parameters=self.config.__dict__
        )
        
        # Store results in database
        self._store_backtest_result(result, analysis_results)
        
        self.logger.info(f"Backtest completed: {result.total_trades} trades, {result.win_rate:.2%} win rate, {result.total_return:.2%} total return")
        
        return result
    
    def _generate_trading_signals(self, data: pd.DataFrame, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate trading signals from analysis results"""
        signals = []
        
        # Process confluence signals
        for confluence_signal in analysis_results['confluence']:
            if confluence_signal.strength >= self.config.min_signal_strength:
                signal = {
                    'timestamp': confluence_signal.timestamp,
                    'signal_type': SignalType.BULLISH if confluence_signal.signal_type == 'bullish' else SignalType.BEARISH,
                    'strength': confluence_signal.strength,
                    'entry_price': confluence_signal.entry_price,
                    'stop_loss': confluence_signal.stop_loss,
                    'take_profit': confluence_signal.take_profit,
                    'metadata': {
                        'confluence_signals': confluence_signal.signals,
                        'signal_count': len(confluence_signal.signals)
                    }
                }
                signals.append(signal)
        
        # Process individual pattern signals
        for pattern_type, patterns in analysis_results['patterns'].items():
            for pattern in patterns:
                if pattern.confidence >= self.config.min_signal_strength:
                    signal_type = self._classify_signal_type(pattern.pattern_type)
                    signal = {
                        'timestamp': pattern.timestamp,
                        'signal_type': signal_type,
                        'strength': pattern.confidence,
                        'entry_price': pattern.entry_price,
                        'stop_loss': pattern.stop_loss,
                        'take_profit': pattern.take_profit,
                        'metadata': {
                            'pattern_type': pattern.pattern_type,
                            'pattern_category': pattern_type
                        }
                    }
                    signals.append(signal)
        
        # Process divergence signals
        for divergence_type, divergences in analysis_results['divergences'].items():
            for divergence in divergences:
                if divergence.confidence >= self.config.min_signal_strength:
                    signal_type = self._classify_signal_type(divergence.pattern_type)
                    signal = {
                        'timestamp': divergence.timestamp,
                        'signal_type': signal_type,
                        'strength': divergence.confidence,
                        'entry_price': divergence.entry_price,
                        'stop_loss': divergence.stop_loss,
                        'take_profit': divergence.take_profit,
                        'metadata': {
                            'divergence_type': divergence.pattern_type,
                            'divergence_category': divergence_type
                        }
                    }
                    signals.append(signal)
        
        # Sort signals by timestamp
        signals.sort(key=lambda x: x['timestamp'])
        
        self.logger.info(f"Generated {len(signals)} trading signals")
        return signals
    
    def _execute_trades(self, data: pd.DataFrame, signals: List[Dict[str, Any]]) -> Tuple[List[Trade], pd.Series]:
        """Execute trades based on signals"""
        trades = []
        equity_curve = pd.Series(index=data.index, dtype=float)
        equity_curve.iloc[0] = self.config.initial_capital
        
        current_capital = self.config.initial_capital
        open_positions = []
        
        for i, (timestamp, row) in enumerate(data.iterrows()):
            # Update open positions
            open_positions = self._update_positions(open_positions, row, timestamp)
            
            # Check for new signals
            for signal in signals:
                if signal['timestamp'] == timestamp and len(open_positions) < self.config.max_positions:
                    # Calculate position size
                    position_size = current_capital * self.config.position_size_pct
                    
                    # Create trade
                    trade = Trade(
                        entry_time=timestamp,
                        exit_time=None,
                        entry_price=signal['entry_price'],
                        exit_price=None,
                        signal_type=signal['signal_type'],
                        signal_strength=signal['strength'],
                        stop_loss=signal['stop_loss'],
                        take_profit=signal['take_profit'],
                        position_size=position_size,
                        metadata=signal['metadata']
                    )
                    
                    open_positions.append(trade)
                    trades.append(trade)
            
            # Update equity curve
            total_pnl = sum(trade.pnl or 0 for trade in open_positions)
            equity_curve.iloc[i] = current_capital + total_pnl
        
        # Close remaining positions at end
        for trade in open_positions:
            trade.exit_time = data.index[-1]
            trade.exit_price = data['Close'].iloc[-1]
            trade.pnl = (trade.exit_price - trade.entry_price) * (1 if trade.signal_type == SignalType.BULLISH else -1)
            trade.pnl_pct = trade.pnl / trade.entry_price
        
        return trades, equity_curve
    
    def _update_positions(self, open_positions: List[Trade], current_bar: pd.Series, timestamp: datetime) -> List[Trade]:
        """Update open positions based on current price action"""
        updated_positions = []
        
        for trade in open_positions:
            current_price = current_bar['Close']
            
            # Check stop loss
            if trade.signal_type == SignalType.BULLISH:
                if current_price <= trade.stop_loss:
                    trade.exit_time = timestamp
                    trade.exit_price = trade.stop_loss
                    trade.pnl = (trade.exit_price - trade.entry_price) * trade.position_size
                    trade.pnl_pct = trade.pnl / (trade.entry_price * trade.position_size)
                    continue
                
                # Check take profit
                if current_price >= trade.take_profit:
                    trade.exit_time = timestamp
                    trade.exit_price = trade.take_profit
                    trade.pnl = (trade.exit_price - trade.entry_price) * trade.position_size
                    trade.pnl_pct = trade.pnl / (trade.entry_price * trade.position_size)
                    continue
                
                # Update trailing stop if enabled
                if self.config.trailing_stop:
                    new_stop = current_price * (1 - self.config.trailing_stop_pct)
                    if new_stop > trade.stop_loss:
                        trade.stop_loss = new_stop
            
            elif trade.signal_type == SignalType.BEARISH:
                if current_price >= trade.stop_loss:
                    trade.exit_time = timestamp
                    trade.exit_price = trade.stop_loss
                    trade.pnl = (trade.entry_price - trade.exit_price) * trade.position_size
                    trade.pnl_pct = trade.pnl / (trade.entry_price * trade.position_size)
                    continue
                
                # Check take profit
                if current_price <= trade.take_profit:
                    trade.exit_time = timestamp
                    trade.exit_price = trade.take_profit
                    trade.pnl = (trade.entry_price - trade.exit_price) * trade.position_size
                    trade.pnl_pct = trade.pnl / (trade.entry_price * trade.position_size)
                    continue
                
                # Update trailing stop if enabled
                if self.config.trailing_stop:
                    new_stop = current_price * (1 + self.config.trailing_stop_pct)
                    if new_stop < trade.stop_loss:
                        trade.stop_loss = new_stop
            
            # Check max hold period
            if trade.exit_time is None:
                bars_held = len([t for t in open_positions if t.entry_time <= trade.entry_time])
                if bars_held >= self.config.max_hold_period:
                    trade.exit_time = timestamp
                    trade.exit_price = current_price
                    trade.pnl = (trade.exit_price - trade.entry_price) * (1 if trade.signal_type == SignalType.BULLISH else -1) * trade.position_size
                    trade.pnl_pct = trade.pnl / (trade.entry_price * trade.position_size)
                    continue
            
            updated_positions.append(trade)
        
        return updated_positions
    
    def _calculate_performance_metrics(self, trades: List[Trade], equity_curve: pd.Series) -> Dict[str, float]:
        """Calculate comprehensive performance metrics"""
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_return': 0.0,
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'volatility': 0.0,
                'var_95': 0.0,
                'max_consecutive_losses': 0,
                'drawdown_curve': pd.Series(dtype=float)
            }
        
        # Basic metrics
        completed_trades = [t for t in trades if t.exit_time is not None]
        winning_trades = [t for t in completed_trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in completed_trades if t.pnl and t.pnl < 0]
        
        total_trades = len(completed_trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        # Return metrics
        returns = [t.pnl_pct for t in completed_trades if t.pnl_pct is not None]
        avg_return = np.mean(returns) if returns else 0
        total_return = (equity_curve.iloc[-1] - equity_curve.iloc[0]) / equity_curve.iloc[0]
        
        # Risk metrics
        returns_series = pd.Series(returns)
        volatility = returns_series.std() if len(returns_series) > 0 else 0
        
        # Drawdown calculation
        peak = equity_curve.expanding().max()
        drawdown_curve = (equity_curve - peak) / peak
        max_drawdown = drawdown_curve.min()
        
        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe_ratio = avg_return / volatility if volatility > 0 else 0
        
        # Sortino ratio (using downside deviation)
        downside_returns = returns_series[returns_series < 0]
        downside_deviation = downside_returns.std() if len(downside_returns) > 0 else 0
        sortino_ratio = avg_return / downside_deviation if downside_deviation > 0 else 0
        
        # Value at Risk (95%)
        var_95 = np.percentile(returns, 5) if len(returns) > 0 else 0
        
        # Consecutive losses
        consecutive_losses = 0
        max_consecutive_losses = 0
        for trade in completed_trades:
            if trade.pnl and trade.pnl < 0:
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            else:
                consecutive_losses = 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_return': avg_return,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'volatility': volatility,
            'var_95': var_95,
            'max_consecutive_losses': max_consecutive_losses,
            'drawdown_curve': drawdown_curve
        }
    
    def _classify_signal_type(self, pattern_type: str) -> SignalType:
        """Classify pattern type as bullish, bearish, or neutral"""
        pattern_lower = pattern_type.lower()
        
        bullish_keywords = ['bull', 'bullish', 'long', 'buy', 'support']
        bearish_keywords = ['bear', 'bearish', 'short', 'sell', 'resistance']
        
        for keyword in bullish_keywords:
            if keyword in pattern_lower:
                return SignalType.BULLISH
        
        for keyword in bearish_keywords:
            if keyword in pattern_lower:
                return SignalType.BEARISH
        
        return SignalType.NEUTRAL
    
    def _store_backtest_result(self, result: BacktestResult, analysis_results: Dict[str, Any]):
        """Store backtest result in database"""
        try:
            backtest_data = {
                'strategy_name': result.strategy_name,
                'symbol': result.symbol,
                'timeframe': result.timeframe,
                'start_date': result.start_date,
                'end_date': result.end_date,
                'total_trades': result.total_trades,
                'winning_trades': result.winning_trades,
                'losing_trades': result.losing_trades,
                'win_rate': result.win_rate,
                'avg_return': result.avg_return,
                'total_return': result.total_return,
                'max_drawdown': result.max_drawdown,
                'sharpe_ratio': result.sharpe_ratio,
                'parameters': result.parameters,
                'equity_curve': result.equity_curve.to_dict()
            }
            
            self.db_handler.store_backtest_result(backtest_data)
            self.logger.info("Backtest result stored in database")
            
        except Exception as e:
            self.logger.error(f"Error storing backtest result: {str(e)}")
    
    def run_optimization(self, 
                        symbol: str, 
                        timeframe: str, 
                        start_date: datetime, 
                        end_date: datetime,
                        param_ranges: Dict[str, List[Any]]) -> Dict[str, Any]:
        """Run parameter optimization"""
        self.logger.info(f"Starting optimization for {symbol} {timeframe}")
        
        best_result = None
        best_params = None
        best_score = float('-inf')
        
        # Generate parameter combinations
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())
        
        total_combinations = np.prod([len(vals) for vals in param_values])
        self.logger.info(f"Testing {total_combinations} parameter combinations")
        
        for i, param_combo in enumerate(np.array(np.meshgrid(*param_values)).T.reshape(-1, len(param_names))):
            # Create config with current parameters
            config_dict = dict(zip(param_names, param_combo))
            
            # Create strategy config
            strategy_config = UnifiedStrategyConfig()
            for key, value in config_dict.items():
                if hasattr(strategy_config, key):
                    setattr(strategy_config, key, value)
            
            try:
                # Run backtest with current parameters
                result = self.run_backtest(symbol, timeframe, start_date, end_date, strategy_config)
                
                # Calculate optimization score (Sharpe ratio * total return)
                score = result.sharpe_ratio * result.total_return
                
                if score > best_score:
                    best_score = score
                    best_result = result
                    best_params = config_dict
                
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Completed {i + 1}/{total_combinations} combinations")
                    
            except Exception as e:
                self.logger.warning(f"Error with parameters {config_dict}: {str(e)}")
                continue
        
        return {
            'best_params': best_params,
            'best_result': best_result,
            'best_score': best_score,
            'total_combinations': total_combinations
        } 