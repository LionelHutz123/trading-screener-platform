import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Tuple, Callable
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta
import json
import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.data_engine.duckdb_handler import DuckDBHandler
from core.ta_engine.unified_strategy_engine import UnifiedStrategyEngine, UnifiedStrategyConfig
from core.backtesting.backtest_engine import BacktestEngine, BacktestConfig

logger = logging.getLogger(__name__)

@dataclass
class ParallelTask:
    """Represents a task for parallel processing"""
    task_id: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    task_type: str  # 'screening', 'backtesting', 'optimization'
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

@dataclass
class ParallelResult:
    """Result from parallel processing"""
    task_id: str
    success: bool
    result: Any
    error: Optional[str] = None
    processing_time: float = 0.0

class ParallelEngine:
    """Multiprocessing engine for parallel trading analysis"""
    
    def __init__(self, max_workers: int = None, db_path: str = "trading_data.duckdb"):
        self.max_workers = max_workers or min(mp.cpu_count(), 8)
        self.db_path = db_path
        self.logger = logger
        
        # Initialize database handler
        self.db_handler = DuckDBHandler(db_path)
        
        self.logger.info(f"Initialized parallel engine with {self.max_workers} workers")
    
    def run_parallel_screening(self, 
                             symbols: List[str], 
                             timeframes: List[str],
                             start_date: datetime,
                             end_date: datetime,
                             strategy_config: UnifiedStrategyConfig = None) -> Dict[str, ParallelResult]:
        """Run parallel screening across multiple symbols and timeframes"""
        
        self.logger.info(f"Starting parallel screening for {len(symbols)} symbols across {len(timeframes)} timeframes")
        
        # Create tasks
        tasks = []
        for symbol in symbols:
            for timeframe in timeframes:
                task_id = f"{symbol}_{timeframe}_screening"
                task = ParallelTask(
                    task_id=task_id,
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    task_type='screening',
                    parameters={'strategy_config': strategy_config}
                )
                tasks.append(task)
        
        # Run parallel processing
        results = self._run_parallel_tasks(tasks, self._screening_worker)
        
        self.logger.info(f"Parallel screening completed: {len([r for r in results.values() if r.success])} successful tasks")
        return results
    
    def run_parallel_backtesting(self,
                               symbols: List[str],
                               timeframes: List[str],
                               start_date: datetime,
                               end_date: datetime,
                               strategy_config: UnifiedStrategyConfig = None,
                               backtest_config: BacktestConfig = None) -> Dict[str, ParallelResult]:
        """Run parallel backtesting across multiple symbols and timeframes"""
        
        self.logger.info(f"Starting parallel backtesting for {len(symbols)} symbols across {len(timeframes)} timeframes")
        
        # Create tasks
        tasks = []
        for symbol in symbols:
            for timeframe in timeframes:
                task_id = f"{symbol}_{timeframe}_backtest"
                task = ParallelTask(
                    task_id=task_id,
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    task_type='backtesting',
                    parameters={
                        'strategy_config': strategy_config,
                        'backtest_config': backtest_config
                    }
                )
                tasks.append(task)
        
        # Run parallel processing
        results = self._run_parallel_tasks(tasks, self._backtesting_worker)
        
        self.logger.info(f"Parallel backtesting completed: {len([r for r in results.values() if r.success])} successful tasks")
        return results
    
    def run_parallel_optimization(self,
                                symbols: List[str],
                                timeframes: List[str],
                                start_date: datetime,
                                end_date: datetime,
                                param_ranges: Dict[str, List[Any]],
                                strategy_config: UnifiedStrategyConfig = None) -> Dict[str, ParallelResult]:
        """Run parallel optimization across multiple symbols and timeframes"""
        
        self.logger.info(f"Starting parallel optimization for {len(symbols)} symbols across {len(timeframes)} timeframes")
        
        # Create tasks
        tasks = []
        for symbol in symbols:
            for timeframe in timeframes:
                task_id = f"{symbol}_{timeframe}_optimization"
                task = ParallelTask(
                    task_id=task_id,
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    task_type='optimization',
                    parameters={
                        'strategy_config': strategy_config,
                        'param_ranges': param_ranges
                    }
                )
                tasks.append(task)
        
        # Run parallel processing
        results = self._run_parallel_tasks(tasks, self._optimization_worker)
        
        self.logger.info(f"Parallel optimization completed: {len([r for r in results.values() if r.success])} successful tasks")
        return results
    
    def _run_parallel_tasks(self, tasks: List[ParallelTask], worker_func: Callable) -> Dict[str, ParallelResult]:
        """Execute tasks in parallel using ProcessPoolExecutor"""
        results = {}
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {executor.submit(worker_func, task): task for task in tasks}
            
            # Collect results as they complete
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results[task.task_id] = result
                except Exception as e:
                    self.logger.error(f"Error processing task {task.task_id}: {str(e)}")
                    results[task.task_id] = ParallelResult(
                        task_id=task.task_id,
                        success=False,
                        result=None,
                        error=str(e)
                    )
        
        return results
    
    def _screening_worker(self, task: ParallelTask) -> ParallelResult:
        """Worker function for screening tasks"""
        import time
        start_time = time.time()
        
        try:
            # Initialize components
            db_handler = DuckDBHandler(self.db_path)
            strategy_config = task.parameters.get('strategy_config')
            strategy_engine = UnifiedStrategyEngine(strategy_config)
            
            # Load data
            data = db_handler.get_bars(task.symbol, task.timeframe, task.start_date, task.end_date)
            if data.empty:
                raise ValueError(f"No data found for {task.symbol} {task.timeframe}")
            
            # Run analysis
            analysis_results = strategy_engine.run_comprehensive_analysis(data)
            
            # Get latest signals
            latest_signals = strategy_engine.get_latest_signals(data, lookback_periods=10)
            
            result = {
                'symbol': task.symbol,
                'timeframe': task.timeframe,
                'analysis_results': analysis_results,
                'latest_signals': latest_signals,
                'data_points': len(data)
            }
            
            processing_time = time.time() - start_time
            
            return ParallelResult(
                task_id=task.task_id,
                success=True,
                result=result,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return ParallelResult(
                task_id=task.task_id,
                success=False,
                result=None,
                error=str(e),
                processing_time=processing_time
            )
    
    def _backtesting_worker(self, task: ParallelTask) -> ParallelResult:
        """Worker function for backtesting tasks"""
        import time
        start_time = time.time()
        
        try:
            # Initialize components
            db_handler = DuckDBHandler(self.db_path)
            strategy_config = task.parameters.get('strategy_config')
            backtest_config = task.parameters.get('backtest_config')
            
            backtest_engine = BacktestEngine(db_handler, backtest_config)
            
            # Run backtest
            result = backtest_engine.run_backtest(
                task.symbol,
                task.timeframe,
                task.start_date,
                task.end_date,
                strategy_config
            )
            
            processing_time = time.time() - start_time
            
            return ParallelResult(
                task_id=task.task_id,
                success=True,
                result=result,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return ParallelResult(
                task_id=task.task_id,
                success=False,
                result=None,
                error=str(e),
                processing_time=processing_time
            )
    
    def _optimization_worker(self, task: ParallelTask) -> ParallelResult:
        """Worker function for optimization tasks"""
        import time
        start_time = time.time()
        
        try:
            # Initialize components
            db_handler = DuckDBHandler(self.db_path)
            strategy_config = task.parameters.get('strategy_config')
            param_ranges = task.parameters.get('param_ranges', {})
            
            backtest_engine = BacktestEngine(db_handler)
            
            # Run optimization
            result = backtest_engine.run_optimization(
                task.symbol,
                task.timeframe,
                task.start_date,
                task.end_date,
                param_ranges
            )
            
            processing_time = time.time() - start_time
            
            return ParallelResult(
                task_id=task.task_id,
                success=True,
                result=result,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return ParallelResult(
                task_id=task.task_id,
                success=False,
                result=None,
                error=str(e),
                processing_time=processing_time
            )
    
    def aggregate_results(self, results: Dict[str, ParallelResult]) -> Dict[str, Any]:
        """Aggregate results from parallel processing"""
        aggregated = {
            'total_tasks': len(results),
            'successful_tasks': len([r for r in results.values() if r.success]),
            'failed_tasks': len([r for r in results.values() if not r.success]),
            'total_processing_time': sum(r.processing_time for r in results.values()),
            'avg_processing_time': np.mean([r.processing_time for r in results.values()]),
            'results_by_type': {},
            'errors': []
        }
        
        # Group results by task type
        for task_id, result in results.items():
            if not result.success:
                aggregated['errors'].append({
                    'task_id': task_id,
                    'error': result.error
                })
                continue
            
            # Extract task type from task_id
            task_type = task_id.split('_')[-1]  # screening, backtesting, optimization
            
            if task_type not in aggregated['results_by_type']:
                aggregated['results_by_type'][task_type] = []
            
            aggregated['results_by_type'][task_type].append(result.result)
        
        return aggregated
    
    def generate_performance_report(self, results: Dict[str, ParallelResult]) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            'summary': {
                'total_tasks': len(results),
                'successful_tasks': len([r for r in results.values() if r.success]),
                'success_rate': len([r for r in results.values() if r.success]) / len(results),
                'total_processing_time': sum(r.processing_time for r in results.values()),
                'avg_processing_time': np.mean([r.processing_time for r in results.values()])
            },
            'backtest_results': [],
            'screening_results': [],
            'optimization_results': []
        }
        
        # Process backtest results
        backtest_results = [r for r in results.values() if r.success and 'backtest' in r.task_id]
        for result in backtest_results:
            if hasattr(result.result, 'total_trades'):
                report['backtest_results'].append({
                    'symbol': result.result.symbol,
                    'timeframe': result.result.timeframe,
                    'total_trades': result.result.total_trades,
                    'win_rate': result.result.win_rate,
                    'total_return': result.result.total_return,
                    'sharpe_ratio': result.result.sharpe_ratio,
                    'max_drawdown': result.result.max_drawdown
                })
        
        # Process screening results
        screening_results = [r for r in results.values() if r.success and 'screening' in r.task_id]
        for result in screening_results:
            if isinstance(result.result, dict) and 'latest_signals' in result.result:
                signal_count = sum(len(signals) for signals in result.result['latest_signals'].values())
                report['screening_results'].append({
                    'symbol': result.result['symbol'],
                    'timeframe': result.result['timeframe'],
                    'signal_count': signal_count,
                    'data_points': result.result['data_points']
                })
        
        # Process optimization results
        optimization_results = [r for r in results.values() if r.success and 'optimization' in r.task_id]
        for result in optimization_results:
            if isinstance(result.result, dict) and 'best_params' in result.result:
                report['optimization_results'].append({
                    'symbol': result.result['best_params'].get('symbol', 'unknown'),
                    'timeframe': result.result['best_params'].get('timeframe', 'unknown'),
                    'best_score': result.result['best_score'],
                    'total_combinations': result.result['total_combinations']
                })
        
        return report
    
    def save_results(self, results: Dict[str, ParallelResult], output_path: str):
        """Save results to file"""
        try:
            # Convert results to serializable format
            serializable_results = {}
            for task_id, result in results.items():
                serializable_results[task_id] = {
                    'success': result.success,
                    'processing_time': result.processing_time,
                    'error': result.error
                }
                
                # Handle result serialization
                if result.success and result.result is not None:
                    if hasattr(result.result, '__dict__'):
                        serializable_results[task_id]['result'] = result.result.__dict__
                    else:
                        serializable_results[task_id]['result'] = str(result.result)
            
            # Save to JSON file
            with open(output_path, 'w') as f:
                json.dump(serializable_results, f, indent=2, default=str)
            
            self.logger.info(f"Results saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")
    
    def close(self):
        """Clean up resources"""
        if hasattr(self, 'db_handler'):
            self.db_handler.close() 