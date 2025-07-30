#!/usr/bin/env python3
"""
Backtest Demo Script
===================

This script demonstrates the backtesting capabilities of the trading screener
by running a backtest on sample data.
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from core.data_engine.duckdb_handler import DuckDBHandler
from core.ta_engine.unified_strategy_engine import UnifiedStrategyEngine
from core.backtesting.backtest_engine import BacktestEngine, BacktestConfig

def create_sample_data():
    """Create realistic sample data for backtesting"""
    print("📊 Creating sample market data...")
    
    # Create 1 year of hourly data
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='1H')
    
    # Create realistic price movements with trends and volatility
    np.random.seed(42)  # For reproducible results
    
    # Start price
    start_price = 100.0
    
    # Generate price series with trend and volatility
    returns = np.random.normal(0.0001, 0.02, len(dates))  # Small positive trend, 2% volatility
    prices = [start_price]
    
    for ret in returns[1:]:
        new_price = prices[-1] * (1 + ret)
        prices.append(new_price)
    
    # Create OHLC data
    data = pd.DataFrame({
        'Open': prices,
        'High': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'Low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'Close': prices,
        'Volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)
    
    # Ensure High >= Low and proper OHLC relationships
    data['High'] = data[['Open', 'High', 'Close']].max(axis=1)
    data['Low'] = data[['Open', 'Low', 'Close']].min(axis=1)
    
    print(f"✓ Created {len(data)} data points")
    return data

def run_backtest_demo():
    """Run a comprehensive backtest demo"""
    print("🚀 Starting Backtest Demo")
    print("=" * 50)
    
    try:
        # Initialize database
        db_handler = DuckDBHandler("demo_backtest.duckdb")
        
        # Create sample data
        sample_data = create_sample_data()
        
        # Store data in database
        db_handler.store_bars('DEMO', '1h', sample_data)
        print("✓ Data stored in database")
        
        # Initialize strategy engine
        strategy_engine = UnifiedStrategyEngine()
        
        # Run comprehensive analysis
        print("\n🔍 Running comprehensive analysis...")
        analysis_results = strategy_engine.run_comprehensive_analysis(sample_data)
        
        print(f"✓ Analysis completed:")
        print(f"  - Indicators calculated: {len(analysis_results['indicators'])}")
        print(f"  - Pattern categories: {len(analysis_results['patterns'])}")
        print(f"  - Divergence signals: {len(analysis_results['divergences'])}")
        print(f"  - Confluence signals: {len(analysis_results['confluence'])}")
        
        # Initialize backtest engine
        backtest_config = BacktestConfig(
            initial_capital=100000,
            position_size_pct=0.1,
            stop_loss_pct=0.02,
            take_profit_pct=0.04,
            min_signal_strength=0.5
        )
        
        backtest_engine = BacktestEngine(db_handler, backtest_config)
        
        # Run backtest
        print("\n📈 Running backtest...")
        result = backtest_engine.run_backtest(
            'DEMO', '1h',
            datetime(2023, 1, 1),
            datetime(2023, 12, 31)
        )
        
        # Display results
        print("\n" + "=" * 50)
        print("📊 BACKTEST RESULTS")
        print("=" * 50)
        
        print(f"📈 Performance Metrics:")
        print(f"  Total Trades: {result.total_trades}")
        print(f"  Winning Trades: {result.winning_trades}")
        print(f"  Losing Trades: {result.losing_trades}")
        print(f"  Win Rate: {result.win_rate:.2%}")
        print(f"  Total Return: {result.total_return:.2%}")
        print(f"  Average Return: {result.avg_return:.2%}")
        
        print(f"\n📊 Risk Metrics:")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"  Sortino Ratio: {result.sortino_ratio:.2f}")
        print(f"  Max Drawdown: {result.max_drawdown:.2%}")
        print(f"  Volatility: {result.volatility:.2%}")
        print(f"  VaR (95%): {result.var_95:.2%}")
        print(f"  Max Consecutive Losses: {result.max_consecutive_losses}")
        
        print(f"\n💰 Trade Analysis:")
        if result.trades:
            avg_trade_duration = np.mean([
                (t.exit_time - t.entry_time).total_seconds() / 3600 
                for t in result.trades if t.exit_time
            ])
            print(f"  Average Trade Duration: {avg_trade_duration:.1f} hours")
            
            profitable_trades = [t for t in result.trades if t.pnl and t.pnl > 0]
            losing_trades = [t for t in result.trades if t.pnl and t.pnl < 0]
            
            if profitable_trades:
                avg_profit = np.mean([t.pnl for t in profitable_trades])
                print(f"  Average Profit: ${avg_profit:.2f}")
            
            if losing_trades:
                avg_loss = np.mean([t.pnl for t in losing_trades])
                print(f"  Average Loss: ${avg_loss:.2f}")
        
        # Show equity curve statistics
        if hasattr(result, 'equity_curve') and len(result.equity_curve) > 0:
            equity_curve = result.equity_curve
            print(f"\n📈 Equity Curve:")
            print(f"  Starting Capital: ${backtest_config.initial_capital:,.2f}")
            print(f"  Ending Capital: ${equity_curve.iloc[-1]:,.2f}")
            print(f"  Peak Capital: ${equity_curve.max():,.2f}")
            print(f"  Final P&L: ${equity_curve.iloc[-1] - backtest_config.initial_capital:,.2f}")
        
        # Show strategy details
        print(f"\n🎯 Strategy Details:")
        print(f"  Symbol: {result.symbol}")
        print(f"  Timeframe: {result.timeframe}")
        print(f"  Period: {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}")
        print(f"  Data Points: {len(sample_data)}")
        
        # Clean up
        db_handler.close()
        os.remove("demo_backtest.duckdb")
        
        print("\n✅ Backtest demo completed successfully!")
        return result
        
    except Exception as e:
        print(f"❌ Error in backtest demo: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def run_optimization_demo():
    """Run a parameter optimization demo"""
    print("\n🔧 Starting Optimization Demo")
    print("=" * 50)
    
    try:
        # Initialize database
        db_handler = DuckDBHandler("demo_optimization.duckdb")
        
        # Create sample data
        sample_data = create_sample_data()
        db_handler.store_bars('DEMO', '1h', sample_data)
        
        # Initialize backtest engine
        backtest_engine = BacktestEngine(db_handler)
        
        # Define parameter ranges for optimization
        param_ranges = {
            'rsi_period': [10, 14, 20],
            'macd_fast': [8, 12, 16],
            'min_signal_strength': [0.4, 0.6, 0.8]
        }
        
        print("🔍 Running parameter optimization...")
        optimization_result = backtest_engine.run_optimization(
            'DEMO', '1h',
            datetime(2023, 1, 1), datetime(2023, 12, 31),
            param_ranges
        )
        
        print(f"\n📊 Optimization Results:")
        print(f"  Total Combinations Tested: {optimization_result['total_combinations']}")
        print(f"  Best Score: {optimization_result['best_score']:.4f}")
        print(f"  Best Parameters: {optimization_result['best_params']}")
        
        if optimization_result['best_result']:
            best_result = optimization_result['best_result']
            print(f"\n🏆 Best Strategy Performance:")
            print(f"  Win Rate: {best_result.win_rate:.2%}")
            print(f"  Total Return: {best_result.total_return:.2%}")
            print(f"  Sharpe Ratio: {best_result.sharpe_ratio:.2f}")
        
        # Clean up
        db_handler.close()
        os.remove("demo_optimization.duckdb")
        
        print("\n✅ Optimization demo completed successfully!")
        return optimization_result
        
    except Exception as e:
        print(f"❌ Error in optimization demo: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🎯 Trading Screener - Backtest Demo")
    print("=" * 50)
    
    # Run backtest demo
    backtest_result = run_backtest_demo()
    
    # Run optimization demo
    optimization_result = run_optimization_demo()
    
    print("\n🎉 Demo completed! Check the results above.") 