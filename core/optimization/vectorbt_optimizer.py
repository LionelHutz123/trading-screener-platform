import vectorbt as vbt
import pandas as pd
import numpy as np
from typing import Dict, Any, Type, Optional
from ..data_engine.sql_database import SQLDatabaseHandler
import itertools
from ..ta_engine.patterns.flag_pattern_detector import FlagConfig

class VectorBtOptimizer:
    """Optimizer using vectorbt for parameter optimization"""
    
    def __init__(self, 
                 strategy_class: Type,
                 db_handler: SQLDatabaseHandler):
        self.strategy_class = strategy_class
        self.db = db_handler
        self.results = None
        
    def create_signals(self, data: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
        """Convert strategy signals to vectorbt format"""
        # Create config object with parameters
        config = FlagConfig()
        for key, value in params.items():
            setattr(config, key, value)
            
        strategy = self.strategy_class(config=config)
        signals = strategy.detect(data)
        
        # Create signal series
        signal_series = pd.Series(0, index=data.index)
        
        for signal in signals:
            if signal.pattern_type == 'BULLISH_FLAG':
                signal_series.iloc[data.index.get_loc(signal.timestamp)] = 1
            elif signal.pattern_type == 'BEARISH_FLAG':
                signal_series.iloc[data.index.get_loc(signal.timestamp)] = -1
                
        return signal_series
        
    def optimize(self,
                symbol: str,
                timeframe: str,
                param_grid: Dict[str, Any],
                metrics: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Run vectorbt parameter optimization"""
        # Load data from database
        data = self.db.get_bars(symbol, timeframe)
        
        # Standardize column names to uppercase
        data.columns = [col.capitalize() for col in data.columns]
        
        # Default metrics if none provided
        if metrics is None:
            metrics = {
                'total_return': lambda pf: pf.total_return(),
                'sharpe_ratio': lambda pf: pf.sharpe_ratio(),
                'max_drawdown': lambda pf: pf.max_drawdown()
            }
            
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(itertools.product(*param_values))
        
        # Generate signals for each parameter combination
        all_signals = []
        for params in param_combinations:
            param_dict = dict(zip(param_names, params))
            signals = self.create_signals(data, param_dict)
            all_signals.append(signals)
            
        # Combine signals into a DataFrame
        signals_df = pd.concat(all_signals, axis=1)
        signals_df.columns = [str(i) for i in range(len(param_combinations))]
        
        # Run backtest
        portfolio = vbt.Portfolio.from_orders(
            close=data['Close'],
            size=signals_df,  # Convert signals to position sizes
            size_type='value',
            init_cash=100000,
            fees=0.001,
            freq=pd.Timedelta(timeframe)
        )
        
        # Calculate metrics and convert Series to regular Python values
        results = {}
        for name, metric_func in metrics.items():
            metric_value = metric_func(portfolio)
            # Convert Series to dict if needed
            if isinstance(metric_value, pd.Series):
                results[name] = {str(k): float(v) for k, v in metric_value.items()}
            else:
                results[name] = float(metric_value)
            
        # Store results in database
        self.db.store_optimization_result(
            strategy_name=self.strategy_class.__name__,
            symbol=symbol,
            timeframe=timeframe,
            parameters=param_grid,
            metrics=results,
            equity_curve=portfolio.value().values
        )
        
        self.results = {
            'portfolio': portfolio,
            'param_combinations': param_combinations,
            'param_names': param_names
        }
        
        return pd.DataFrame(results)
        
    def get_best_parameters(self) -> Dict[str, Any]:
        """Get best parameters from optimization results"""
        if self.results is None:
            raise ValueError("No optimization results available")
            
        portfolio = self.results['portfolio']
        param_combinations = self.results['param_combinations']
        param_names = self.results['param_names']
        
        # Find best combination based on Sharpe ratio
        sharpe_ratios = portfolio.sharpe_ratio()
        best_idx = sharpe_ratios.argmax()
        best_params = param_combinations[best_idx]
        
        return dict(zip(param_names, best_params))
        
    def plot_results(self):
        """Plot optimization results"""
        if self.results is None:
            raise ValueError("No optimization results available")
            
        portfolio = self.results['portfolio']
        
        # Plot equity curves
        portfolio.plot()
        
        # Plot metrics heatmap if we have 2 parameters
        if len(self.results['param_names']) == 2:
            metrics_df = pd.DataFrame({
                'sharpe_ratio': portfolio.sharpe_ratio()
            })
            metrics_df.index = pd.MultiIndex.from_tuples(
                self.results['param_combinations'],
                names=self.results['param_names']
            )
            metrics_df = metrics_df.unstack()
            
            vbt.plotting.heatmap(
                metrics_df,
                title='Parameter Optimization Heatmap'
            ) 