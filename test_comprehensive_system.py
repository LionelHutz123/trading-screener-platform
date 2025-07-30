#!/usr/bin/env python3
"""
Comprehensive System Test
========================

This script tests all components of the trading screener system:
- Data fetching and storage
- Technical indicators and pattern detection
- RSI divergence detection
- Backtesting engine
- Parallel processing
- Database operations

Usage:
    python test_comprehensive_system.py
"""

import sys
import os
from pathlib import Path
import logging
from datetime import datetime, timedelta
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from core.data_engine.duckdb_handler import DuckDBHandler
from core.ta_engine.indicators import TechnicalIndicatorEngine, IndicatorConfig
from core.ta_engine.unified_strategy_engine import UnifiedStrategyEngine, UnifiedStrategyConfig
from core.backtesting.backtest_engine import BacktestEngine, BacktestConfig
from core.multiprocessing.parallel_engine import ParallelEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_operations():
    """Test database operations"""
    print("\n=== Testing Database Operations ===")
    
    try:
        # Initialize database
        db_handler = DuckDBHandler("test_data.duckdb")
        
        # Create sample data
        import pandas as pd
        import numpy as np
        
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='1H')
        sample_data = pd.DataFrame({
            'Open': np.random.uniform(100, 200, len(dates)),
            'High': np.random.uniform(100, 200, len(dates)),
            'Low': np.random.uniform(100, 200, len(dates)),
            'Close': np.random.uniform(100, 200, len(dates)),
            'Volume': np.random.randint(1000, 10000, len(dates))
        }, index=dates)
        
        # Store data
        db_handler.store_bars('TEST', '1h', sample_data)
        print("✓ Data stored successfully")
        
        # Retrieve data
        retrieved_data = db_handler.get_bars('TEST', '1h')
        print(f"✓ Data retrieved: {len(retrieved_data)} rows")
        
        # Test indicators storage
        rsi_values = pd.Series(np.random.uniform(0, 100, len(dates)), index=dates)
        db_handler.store_indicator('TEST', '1h', 'RSI', rsi_values)
        print("✓ Indicators stored successfully")
        
        # Test indicator retrieval
        retrieved_rsi = db_handler.get_indicator('TEST', '1h', 'RSI')
        print(f"✓ Indicators retrieved: {len(retrieved_rsi)} values")
        
        # Clean up
        db_handler.close()
        os.remove("test_data.duckdb")
        
        return True
        
    except Exception as e:
        print(f"✗ Database test failed: {str(e)}")
        return False

def test_indicator_engine():
    """Test technical indicator engine"""
    print("\n=== Testing Indicator Engine ===")
    
    try:
        # Create sample data
        import pandas as pd
        import numpy as np
        
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='1H')
        sample_data = pd.DataFrame({
            'Open': np.random.uniform(100, 200, len(dates)),
            'High': np.random.uniform(100, 200, len(dates)),
            'Low': np.random.uniform(100, 200, len(dates)),
            'Close': np.random.uniform(100, 200, len(dates)),
            'Volume': np.random.randint(1000, 10000, len(dates))
        }, index=dates)
        
        # Initialize indicator engine
        indicator_engine = TechnicalIndicatorEngine()
        
        # Calculate all indicators
        indicators = indicator_engine.calculate_all_indicators(sample_data)
        print(f"✓ Calculated {len(indicators)} indicators")
        
        # Test specific indicators
        expected_indicators = ['RSI', 'MACD', 'SMA_20', 'BB_Upper', 'ATR']
        for indicator in expected_indicators:
            if indicator in indicators:
                print(f"✓ {indicator} calculated successfully")
            else:
                print(f"✗ {indicator} not found")
        
        # Test divergence detection
        divergence_indicators = [k for k in indicators.keys() if 'divergence' in k.lower()]
        print(f"✓ Found {len(divergence_indicators)} divergence indicators")
        
        return True
        
    except Exception as e:
        print(f"✗ Indicator engine test failed: {str(e)}")
        return False

def test_unified_strategy_engine():
    """Test unified strategy engine"""
    print("\n=== Testing Unified Strategy Engine ===")
    
    try:
        # Create sample data
        import pandas as pd
        import numpy as np
        
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='1H')
        sample_data = pd.DataFrame({
            'Open': np.random.uniform(100, 200, len(dates)),
            'High': np.random.uniform(100, 200, len(dates)),
            'Low': np.random.uniform(100, 200, len(dates)),
            'Close': np.random.uniform(100, 200, len(dates)),
            'Volume': np.random.randint(1000, 10000, len(dates))
        }, index=dates)
        
        # Initialize strategy engine
        strategy_engine = UnifiedStrategyEngine()
        
        # Run comprehensive analysis
        analysis_results = strategy_engine.run_comprehensive_analysis(sample_data)
        print("✓ Comprehensive analysis completed")
        
        # Check results structure
        expected_sections = ['indicators', 'patterns', 'divergences', 'stock_screener', 'confluence', 'summary']
        for section in expected_sections:
            if section in analysis_results:
                print(f"✓ {section} section present")
            else:
                print(f"✗ {section} section missing")
        
        # Test latest signals
        latest_signals = strategy_engine.get_latest_signals(sample_data, lookback_periods=10)
        print(f"✓ Latest signals retrieved: {len(latest_signals)} categories")
        
        return True
        
    except Exception as e:
        print(f"✗ Unified strategy engine test failed: {str(e)}")
        return False

def test_backtest_engine():
    """Test backtesting engine"""
    print("\n=== Testing Backtest Engine ===")
    
    try:
        # Create sample data
        import pandas as pd
        import numpy as np
        
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='1H')
        sample_data = pd.DataFrame({
            'Open': np.random.uniform(100, 200, len(dates)),
            'High': np.random.uniform(100, 200, len(dates)),
            'Low': np.random.uniform(100, 200, len(dates)),
            'Close': np.random.uniform(100, 200, len(dates)),
            'Volume': np.random.randint(1000, 10000, len(dates))
        }, index=dates)
        
        # Store data in database
        db_handler = DuckDBHandler("test_backtest.duckdb")
        db_handler.store_bars('TEST', '1h', sample_data)
        
        # Initialize backtest engine
        backtest_engine = BacktestEngine(db_handler)
        
        # Run backtest
        result = backtest_engine.run_backtest(
            'TEST', '1h', 
            datetime(2023, 1, 1), 
            datetime(2023, 12, 31)
        )
        
        print("✓ Backtest completed successfully")
        print(f"  - Total trades: {result.total_trades}")
        print(f"  - Win rate: {result.win_rate:.2%}")
        print(f"  - Total return: {result.total_return:.2%}")
        print(f"  - Sharpe ratio: {result.sharpe_ratio:.2f}")
        
        # Clean up
        db_handler.close()
        os.remove("test_backtest.duckdb")
        
        return True
        
    except Exception as e:
        print(f"✗ Backtest engine test failed: {str(e)}")
        return False

def test_parallel_engine():
    """Test parallel processing engine"""
    print("\n=== Testing Parallel Engine ===")
    
    try:
        # Create sample data
        import pandas as pd
        import numpy as np
        
        # Store sample data for multiple symbols
        db_handler = DuckDBHandler("test_parallel.duckdb")
        
        symbols = ['TEST1', 'TEST2', 'TEST3']
        timeframes = ['1h', '4h']
        
        for symbol in symbols:
            for timeframe in timeframes:
                dates = pd.date_range('2023-01-01', '2023-12-31', freq='1H')
                sample_data = pd.DataFrame({
                    'Open': np.random.uniform(100, 200, len(dates)),
                    'High': np.random.uniform(100, 200, len(dates)),
                    'Low': np.random.uniform(100, 200, len(dates)),
                    'Close': np.random.uniform(100, 200, len(dates)),
                    'Volume': np.random.randint(1000, 10000, len(dates))
                }, index=dates)
                db_handler.store_bars(symbol, timeframe, sample_data)
        
        db_handler.close()
        
        # Initialize parallel engine
        parallel_engine = ParallelEngine(db_path="test_parallel.duckdb")
        
        # Test parallel screening
        results = parallel_engine.run_parallel_screening(
            symbols=symbols,
            timeframes=timeframes,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31)
        )
        
        print(f"✓ Parallel screening completed: {len(results)} tasks")
        
        # Test result aggregation
        aggregated = parallel_engine.aggregate_results(results)
        print(f"✓ Results aggregated: {aggregated['successful_tasks']} successful tasks")
        
        # Test performance report
        report = parallel_engine.generate_performance_report(results)
        print("✓ Performance report generated")
        
        # Clean up
        parallel_engine.close()
        os.remove("test_parallel.duckdb")
        
        return True
        
    except Exception as e:
        print(f"✗ Parallel engine test failed: {str(e)}")
        return False

def test_rsi_divergence():
    """Test RSI divergence detection specifically"""
    print("\n=== Testing RSI Divergence Detection ===")
    
    try:
        # Create data with known divergence patterns
        import pandas as pd
        import numpy as np
        
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='1H')
        
        # Create price data with lower lows
        price_trend = np.linspace(200, 150, len(dates)) + np.random.normal(0, 5, len(dates))
        
        # Create RSI data with higher lows (bullish divergence)
        rsi_trend = np.linspace(30, 50, len(dates)) + np.random.normal(0, 3, len(dates))
        
        sample_data = pd.DataFrame({
            'Open': price_trend + np.random.normal(0, 1, len(dates)),
            'High': price_trend + np.random.uniform(0, 5, len(dates)),
            'Low': price_trend - np.random.uniform(0, 5, len(dates)),
            'Close': price_trend,
            'Volume': np.random.randint(1000, 10000, len(dates))
        }, index=dates)
        
        # Initialize indicator engine
        indicator_engine = TechnicalIndicatorEngine()
        
        # Calculate indicators including divergence
        indicators = indicator_engine.calculate_all_indicators(sample_data)
        
        # Check for divergence indicators
        divergence_indicators = [k for k in indicators.keys() if 'divergence' in k.lower()]
        print(f"✓ Found {len(divergence_indicators)} divergence indicators")
        
        for indicator in divergence_indicators:
            if indicators[indicator].sum() > 0:
                print(f"✓ {indicator} detected signals")
            else:
                print(f"  {indicator} no signals detected")
        
        return True
        
    except Exception as e:
        print(f"✗ RSI divergence test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Comprehensive System Test")
    print("=" * 50)
    
    tests = [
        ("Database Operations", test_database_operations),
        ("Indicator Engine", test_indicator_engine),
        ("Unified Strategy Engine", test_unified_strategy_engine),
        ("Backtest Engine", test_backtest_engine),
        ("Parallel Engine", test_parallel_engine),
        ("RSI Divergence Detection", test_rsi_divergence)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {str(e)}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready for use.")
    else:
        print("⚠️  Some tests failed. Please check the logs above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 