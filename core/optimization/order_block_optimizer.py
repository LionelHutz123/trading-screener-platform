import pandas as pd
import numpy as np
import vectorbt as vbt
from core.ta_engine.patterns.order_block import OrderBlockDetector, OrderBlockConfig
from core.data_engine.sql_database import SQLDatabaseHandler

class OrderBlockOptimizer:
    """Optimizer for Order Block pattern detection strategy"""
    
    def __init__(self, db: SQLDatabaseHandler):
        self.db = db
    
    def generate_param_space(self) -> dict:
        """Generate parameter space for optimization"""
        return {
            'min_imbalance': [0.01, 0.02, 0.03, 0.04, 0.05],      # 1-5% imbalance
            'max_age_bars': [10, 15, 20, 25, 30],                 # Bar range for valid blocks
            'min_volume_ratio': [1.2, 1.5, 1.8, 2.0, 2.5],       # Volume compared to average
            'min_candle_size': [0.005, 0.01, 0.015, 0.02, 0.025], # 0.5-2.5% candle size
            'max_candle_size': [0.03, 0.04, 0.05, 0.06, 0.07],    # 3-7% max candle size
            'lookback_period': [5, 10, 15, 20, 25],               # Periods for volume average
            'min_confidence': [0.3, 0.4, 0.5, 0.6, 0.7]           # Confidence threshold
        }
    
    def run_optimization(self, symbol: str, timeframe: str, start_date: str, end_date: str):
        """Run optimization for the given symbol and time range"""
        # Get data
        df = self.db.get_bars(symbol, timeframe, start_date, end_date)
        
        # Store optimization run
        run_id = self.db.store_optimization_run(
            strategy_name='ORDER_BLOCK',
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        # Generate parameter combinations
        param_space = self.generate_param_space()
        
        # Test each parameter combination
        for min_imbalance in param_space['min_imbalance']:
            for max_age_bars in param_space['max_age_bars']:
                for min_volume_ratio in param_space['min_volume_ratio']:
                    for min_candle_size in param_space['min_candle_size']:
                        for max_candle_size in param_space['max_candle_size']:
                            for lookback_period in param_space['lookback_period']:
                                for min_confidence in param_space['min_confidence']:
                                    # Create config
                                    config = OrderBlockConfig(
                                        min_imbalance=min_imbalance,
                                        max_age_bars=max_age_bars,
                                        min_volume_ratio=min_volume_ratio,
                                        min_candle_size=min_candle_size,
                                        max_candle_size=max_candle_size,
                                        lookback_period=lookback_period,
                                        min_confidence=min_confidence
                                    )
                                    
                                    # Run backtest with this config
                                    detector = OrderBlockDetector(config)
                                    entry_signals = pd.Series(0, index=df.index)
                                    exit_signals = pd.Series(0, index=df.index)
                                    
                                    for i in range(len(df)):
                                        data = {
                                            'High': df['high'].values,
                                            'Low': df['low'].values,
                                            'Close': df['close'].values,
                                            'Volume': df['volume'].values,
                                            'timestamp': df.index.values
                                        }
                                        pattern = detector.detect(data, i)
                                        if pattern:
                                            if pattern.pattern_type == 'BULLISH_ORDER_BLOCK':
                                                entry_signals.iloc[i] = 1
                                                # Exit after N bars
                                                exit_idx = min(i + 5, len(df) - 1)
                                                exit_signals.iloc[exit_idx] = 1
                                            elif pattern.pattern_type == 'BEARISH_ORDER_BLOCK':
                                                entry_signals.iloc[i] = -1
                                                # Exit after N bars
                                                exit_idx = min(i + 5, len(df) - 1)
                                                exit_signals.iloc[exit_idx] = 1
                                    
                                    # Run vectorbt backtest
                                    portfolio = vbt.Portfolio.from_signals(
                                        close=df['close'],
                                        entries=entry_signals == 1,
                                        exits=exit_signals == 1,
                                        short_entries=entry_signals == -1,
                                        short_exits=exit_signals == 1,
                                        size=0.1,  # Use 10% of portfolio per trade
                                        size_type='percent',
                                        init_cash=100000,
                                        fees=0.001,
                                        freq='1D'
                                    )
                                    
                                    # Calculate metrics
                                    total_return = portfolio.total_return()
                                    sharpe_ratio = portfolio.sharpe_ratio()
                                    sortino_ratio = portfolio.sortino_ratio()
                                    max_drawdown = portfolio.max_drawdown()
                                    
                                    # Store parameters and results
                                    self.db.store_parameter_set(
                                        run_id=run_id,
                                        parameters={
                                            'min_imbalance': min_imbalance,
                                            'max_age_bars': max_age_bars,
                                            'min_volume_ratio': min_volume_ratio,
                                            'min_candle_size': min_candle_size,
                                            'max_candle_size': max_candle_size,
                                            'lookback_period': lookback_period,
                                            'min_confidence': min_confidence
                                        },
                                        metrics={
                                            'total_return': total_return,
                                            'sharpe_ratio': sharpe_ratio,
                                            'sortino_ratio': sortino_ratio,
                                            'max_drawdown': max_drawdown
                                        }
                                    )
        
        return run_id
    
    def get_best_parameters(self, run_id: int) -> dict:
        """Get the best performing parameters from an optimization run"""
        return self.db.get_best_parameters(run_id) 