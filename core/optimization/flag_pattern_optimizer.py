import vectorbt as vbt
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from ..ta_engine.patterns.flag_pattern import FlagPatternDetector, FlagConfig
from ..data_engine.sql_database import SQLDatabaseHandler
from itertools import product

class FlagPatternOptimizer:
    """Optimizer for flag pattern strategy using vectorbt"""
    
    def __init__(self, db: SQLDatabaseHandler):
        self.db = db
        
    def generate_param_space(self) -> Dict[str, List[float]]:
        """Generate parameter space for optimization"""
        return {
            'min_pole_height': [0.01, 0.02, 0.03],
            'min_flag_bars': [3, 5, 7, 10],
            'max_flag_bars': [15, 20, 25, 30],
            'max_flag_width_ratio': [1.5, 2.0, 2.5],
            'max_flag_height_ratio': [0.3, 0.5, 0.7],
            'volume_decline': [0.0],  # Effectively disable volume requirement
            'min_confidence': [0.5, 0.6, 0.7]
        }
        
    def run_optimization(self, symbol: str, timeframe: str, 
                        start_date: pd.Timestamp = None,
                        end_date: pd.Timestamp = None) -> pd.DataFrame:
        """Run optimization using vectorbt's Portfolio"""
        # Get data from database
        df = self.db.get_bars(symbol, timeframe, start_date, end_date)
        if df.empty:
            raise ValueError(f"No data found for {symbol} {timeframe}")
            
        # Generate parameter combinations
        param_space = self.generate_param_space()
        param_names = list(param_space.keys())
        param_values = list(param_space.values())
        param_combinations = list(product(*param_values))
        
        # Run backtests for each parameter combination
        results = []
        for params in param_combinations:
            param_dict = dict(zip(param_names, params))
            detector = FlagPatternDetector(FlagConfig(**param_dict))
            
            # Generate signals
            signals = pd.Series(0, index=df.index)
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
                    if pattern.pattern_type == 'BULLISH_FLAG':
                        signals.iloc[i] = 1
                    elif pattern.pattern_type == 'BEARISH_FLAG':
                        signals.iloc[i] = -1
            
            # Run vectorbt backtest
            portfolio = vbt.Portfolio.from_signals(
                close=df['close'],
                entries=signals == 1,
                short_entries=signals == -1,
                size=1.0,
                size_type='value',
                init_cash=100000,
                fees=0.001,
                freq='1D'
            )
            
            # Calculate metrics
            metrics = {
                'total_return': portfolio.total_return(),
                'sharpe_ratio': portfolio.sharpe_ratio(),
                'max_drawdown': portfolio.max_drawdown(),
                'sortino_ratio': portfolio.sortino_ratio(),
                'params': param_dict
            }
            results.append(metrics)
        
        # Convert results to DataFrame
        results_df = pd.DataFrame(results)
        
        # Store best parameters
        best_params = results_df.loc[results_df['total_return'].idxmax(), 'params']
        self.db.store_optimization_result(
            strategy_name='FLAG_PATTERN',
            symbol=symbol,
            timeframe=timeframe,
            parameters=best_params,
            metrics={
                'total_return': float(results_df['total_return'].max()),
                'sharpe_ratio': float(results_df.loc[results_df['total_return'].idxmax(), 'sharpe_ratio']),
                'max_drawdown': float(results_df.loc[results_df['total_return'].idxmax(), 'max_drawdown']),
                'sortino_ratio': float(results_df.loc[results_df['total_return'].idxmax(), 'sortino_ratio'])
            }
        )
        
        return results_df
        
    def _run_single_backtest(self, symbol: str, timeframe: str,
                           start_date: pd.Timestamp = None,
                           end_date: pd.Timestamp = None,
                           config: FlagConfig = None) -> dict:
        """Run a single backtest with given parameters"""
        # Get data from database
        df = self.db.get_bars(symbol, timeframe, start_date, end_date)
        if df.empty:
            raise ValueError(f"No data found for {symbol} {timeframe}")

        detector = FlagPatternDetector(config)

        # Generate signals
        signals = pd.Series(0, index=df.index)
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
                if pattern.pattern_type == 'BULLISH_FLAG':
                    signals.iloc[i] = 1
                elif pattern.pattern_type == 'BEARISH_FLAG':
                    signals.iloc[i] = -1

        # Run vectorbt backtest
        portfolio = vbt.Portfolio.from_signals(
            close=df['close'],
            entries=signals == 1,
            short_entries=signals == -1,
            size=1.0,
            size_type='value',
            init_cash=100000,
            fees=0.001,
            freq='1D'
        )

        # Calculate metrics
        return {
            'total_return': portfolio.total_return(),
            'sharpe_ratio': portfolio.sharpe_ratio(),
            'max_drawdown': portfolio.max_drawdown(),
            'sortino_ratio': portfolio.sortino_ratio()
        }
        
    def get_best_parameters(self) -> Dict[str, Any]:
        """Get best performing parameters from database"""
        return self.db.get_best_parameters('FLAG_PATTERN') 