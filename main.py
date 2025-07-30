#!/usr/bin/env python3
"""
Comprehensive Trading Screener Application
=========================================

This application provides a complete trading screener with:
- Data fetching from Alpaca API
- High-performance storage with DuckDB
- Technical analysis and pattern detection
- RSI/price divergence detection
- Comprehensive backtesting
- Parallel processing capabilities
- Dashboard interface

Usage:
    python main.py --mode screening --symbols AAPL,MSFT,GOOGL --timeframes 1h,4h
    python main.py --mode backtesting --symbols AAPL --timeframes 1h --start-date 2023-01-01
    python main.py --mode optimization --symbols AAPL --timeframes 1h --param-ranges '{"rsi_period": [10,14,20]}'
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from core.data_engine.duckdb_handler import DuckDBHandler
from core.ta_engine.unified_strategy_engine import UnifiedStrategyEngine, UnifiedStrategyConfig
from core.backtesting.backtest_engine import BacktestEngine, BacktestConfig
from core.multiprocessing.parallel_engine import ParallelEngine
from alpaca_fetcher_new import get_alpaca_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_screener.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TradingScreenerApp:
    """Main application class for the trading screener"""
    
    def __init__(self, db_path: str = "trading_data.duckdb"):
        self.db_path = db_path
        self.db_handler = DuckDBHandler(db_path)
        self.logger = logger
        
        # Initialize engines
        self.strategy_engine = UnifiedStrategyEngine()
        self.backtest_engine = BacktestEngine(self.db_handler)
        self.parallel_engine = ParallelEngine(db_path=db_path)
        
        self.logger.info("Trading Screener Application initialized")
    
    def fetch_data(self, symbols: List[str], timeframes: List[str], 
                   start_date: str, end_date: str) -> Dict[str, Any]:
        """Fetch and store market data"""
        self.logger.info(f"Fetching data for {len(symbols)} symbols across {len(timeframes)} timeframes")
        
        try:
            # Convert date strings to datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Fetch data using existing Alpaca fetcher
            results = get_alpaca_data(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                timeframes=timeframes,
                use_database=True,
                save_to_csv=False
            )
            
            # Store in DuckDB
            for symbol, timeframes_data in results.items():
                for timeframe, data in timeframes_data.items():
                    if not data.empty:
                        self.db_handler.store_bars(symbol, timeframe, data)
            
            self.logger.info(f"Data fetching completed successfully")
            return {
                'status': 'success',
                'symbols_processed': len(symbols),
                'timeframes_processed': len(timeframes),
                'total_bars': sum(len(data) for symbol_data in results.values() 
                                for data in symbol_data.values())
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching data: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def run_screening(self, symbols: List[str], timeframes: List[str], 
                     start_date: str, end_date: str) -> Dict[str, Any]:
        """Run screening analysis"""
        self.logger.info(f"Running screening for {len(symbols)} symbols")
        
        try:
            # Convert date strings to datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Run parallel screening
            results = self.parallel_engine.run_parallel_screening(
                symbols=symbols,
                timeframes=timeframes,
                start_date=start_dt,
                end_date=end_dt
            )
            
            # Aggregate results
            aggregated = self.parallel_engine.aggregate_results(results)
            report = self.parallel_engine.generate_performance_report(results)
            
            # Save results
            output_path = f"screening_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.parallel_engine.save_results(results, output_path)
            
            return {
                'status': 'success',
                'results': aggregated,
                'report': report,
                'output_file': output_path
            }
            
        except Exception as e:
            self.logger.error(f"Error in screening: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def run_backtesting(self, symbols: List[str], timeframes: List[str],
                       start_date: str, end_date: str) -> Dict[str, Any]:
        """Run backtesting analysis"""
        self.logger.info(f"Running backtesting for {len(symbols)} symbols")
        
        try:
            # Convert date strings to datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Run parallel backtesting
            results = self.parallel_engine.run_parallel_backtesting(
                symbols=symbols,
                timeframes=timeframes,
                start_date=start_dt,
                end_date=end_dt
            )
            
            # Aggregate results
            aggregated = self.parallel_engine.aggregate_results(results)
            report = self.parallel_engine.generate_performance_report(results)
            
            # Save results
            output_path = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.parallel_engine.save_results(results, output_path)
            
            return {
                'status': 'success',
                'results': aggregated,
                'report': report,
                'output_file': output_path
            }
            
        except Exception as e:
            self.logger.error(f"Error in backtesting: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def run_optimization(self, symbols: List[str], timeframes: List[str],
                        start_date: str, end_date: str, param_ranges: Dict[str, List[Any]]) -> Dict[str, Any]:
        """Run parameter optimization"""
        self.logger.info(f"Running optimization for {len(symbols)} symbols")
        
        try:
            # Convert date strings to datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Run parallel optimization
            results = self.parallel_engine.run_parallel_optimization(
                symbols=symbols,
                timeframes=timeframes,
                start_date=start_dt,
                end_date=end_dt,
                param_ranges=param_ranges
            )
            
            # Aggregate results
            aggregated = self.parallel_engine.aggregate_results(results)
            report = self.parallel_engine.generate_performance_report(results)
            
            # Save results
            output_path = f"optimization_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.parallel_engine.save_results(results, output_path)
            
            return {
                'status': 'success',
                'results': aggregated,
                'report': report,
                'output_file': output_path
            }
            
        except Exception as e:
            self.logger.error(f"Error in optimization: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def run_single_analysis(self, symbol: str, timeframe: str, 
                           start_date: str, end_date: str) -> Dict[str, Any]:
        """Run single symbol analysis with detailed output"""
        self.logger.info(f"Running single analysis for {symbol} {timeframe}")
        
        try:
            # Convert date strings to datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Load data
            data = self.db_handler.get_bars(symbol, timeframe, start_dt, end_dt)
            if data.empty:
                return {'status': 'error', 'error': f'No data found for {symbol} {timeframe}'}
            
            # Run comprehensive analysis
            analysis_results = self.strategy_engine.run_comprehensive_analysis(data)
            
            # Run backtest
            backtest_result = self.backtest_engine.run_backtest(
                symbol, timeframe, start_dt, end_dt
            )
            
            return {
                'status': 'success',
                'symbol': symbol,
                'timeframe': timeframe,
                'data_points': len(data),
                'analysis_results': analysis_results,
                'backtest_result': {
                    'total_trades': backtest_result.total_trades,
                    'win_rate': backtest_result.win_rate,
                    'total_return': backtest_result.total_return,
                    'sharpe_ratio': backtest_result.sharpe_ratio,
                    'max_drawdown': backtest_result.max_drawdown
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in single analysis: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def get_available_data(self) -> Dict[str, Any]:
        """Get information about available data"""
        try:
            symbols = self.db_handler.get_available_symbols()
            data_info = {}
            
            for symbol in symbols:
                timeframes = self.db_handler.get_available_timeframes(symbol)
                data_info[symbol] = {}
                
                for timeframe in timeframes:
                    row_count = self.db_handler.get_row_count(symbol, timeframe)
                    data_info[symbol][timeframe] = row_count
            
            return {
                'status': 'success',
                'total_symbols': len(symbols),
                'data_info': data_info
            }
            
        except Exception as e:
            self.logger.error(f"Error getting available data: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def close(self):
        """Clean up resources"""
        self.db_handler.close()
        self.parallel_engine.close()
        self.logger.info("Trading Screener Application closed")

def parse_param_ranges(param_ranges_str: str) -> Dict[str, List[Any]]:
    """Parse parameter ranges from string format"""
    try:
        # Parse JSON string
        param_dict = json.loads(param_ranges_str)
        
        # Convert string values to appropriate types
        for key, values in param_dict.items():
            if isinstance(values, list):
                # Convert string numbers to actual numbers
                converted_values = []
                for val in values:
                    if isinstance(val, str):
                        try:
                            if '.' in val:
                                converted_values.append(float(val))
                            else:
                                converted_values.append(int(val))
                        except ValueError:
                            converted_values.append(val)
                    else:
                        converted_values.append(val)
                param_dict[key] = converted_values
        
        return param_dict
    except Exception as e:
        raise ValueError(f"Invalid parameter ranges format: {str(e)}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Trading Screener Application')
    parser.add_argument('--mode', required=True, 
                       choices=['fetch', 'screening', 'backtesting', 'optimization', 'single', 'info'],
                       help='Operation mode')
    parser.add_argument('--symbols', nargs='+', help='List of symbols')
    parser.add_argument('--timeframes', nargs='+', help='List of timeframes')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--param-ranges', help='Parameter ranges for optimization (JSON string)')
    parser.add_argument('--db-path', default='trading_data.duckdb', help='Database path')
    
    args = parser.parse_args()
    
    # Initialize application
    app = TradingScreenerApp(args.db_path)
    
    try:
        if args.mode == 'fetch':
            if not all([args.symbols, args.timeframes, args.start_date, args.end_date]):
                print("Error: fetch mode requires --symbols, --timeframes, --start-date, and --end-date")
                return
            
            result = app.fetch_data(args.symbols, args.timeframes, args.start_date, args.end_date)
            print(json.dumps(result, indent=2, default=str))
        
        elif args.mode == 'screening':
            if not all([args.symbols, args.timeframes, args.start_date, args.end_date]):
                print("Error: screening mode requires --symbols, --timeframes, --start-date, and --end-date")
                return
            
            result = app.run_screening(args.symbols, args.timeframes, args.start_date, args.end_date)
            print(json.dumps(result, indent=2, default=str))
        
        elif args.mode == 'backtesting':
            if not all([args.symbols, args.timeframes, args.start_date, args.end_date]):
                print("Error: backtesting mode requires --symbols, --timeframes, --start-date, and --end-date")
                return
            
            result = app.run_backtesting(args.symbols, args.timeframes, args.start_date, args.end_date)
            print(json.dumps(result, indent=2, default=str))
        
        elif args.mode == 'optimization':
            if not all([args.symbols, args.timeframes, args.start_date, args.end_date, args.param_ranges]):
                print("Error: optimization mode requires --symbols, --timeframes, --start-date, --end-date, and --param-ranges")
                return
            
            param_ranges = parse_param_ranges(args.param_ranges)
            result = app.run_optimization(args.symbols, args.timeframes, args.start_date, args.end_date, param_ranges)
            print(json.dumps(result, indent=2, default=str))
        
        elif args.mode == 'single':
            if not all([args.symbols, args.timeframes, args.start_date, args.end_date]):
                print("Error: single mode requires --symbols, --timeframes, --start-date, and --end-date")
                return
            
            result = app.run_single_analysis(args.symbols[0], args.timeframes[0], args.start_date, args.end_date)
            print(json.dumps(result, indent=2, default=str))
        
        elif args.mode == 'info':
            result = app.get_available_data()
            print(json.dumps(result, indent=2, default=str))
    
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
    except Exception as e:
        print(f"Error: {str(e)}")
        logger.error(f"Application error: {str(e)}")
    finally:
        app.close()

if __name__ == "__main__":
    main() 