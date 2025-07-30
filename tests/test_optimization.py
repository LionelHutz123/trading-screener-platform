import sys
import os
import asyncio
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from core.data_engine.sql_database import SQLDatabaseHandler
from core.optimization.vectorbt_optimizer import VectorBtOptimizer
from core.ta_engine.patterns.flag_pattern_detector import FlagPatternDetector

def create_sample_data(symbol: str = 'AAPL', timeframe: str = '1h'):
    """Create sample price data with flag patterns"""
    # Generate dates
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq=timeframe)
    n = len(dates)
    
    # Base price trend
    base_trend = np.linspace(100, 150, n)  # Upward trend
    noise = np.random.normal(0, 1, n) * 0.5
    
    # Create two flag patterns
    flag1_start = n // 3
    flag2_start = 2 * n // 3
    
    # First bullish flag
    base_trend[flag1_start-20:flag1_start] += np.linspace(0, 10, 20)  # Pole
    base_trend[flag1_start:flag1_start+15] -= np.linspace(0, 3, 15)   # Flag
    
    # Second bullish flag
    base_trend[flag2_start-20:flag2_start] += np.linspace(0, 15, 20)  # Pole
    base_trend[flag2_start:flag2_start+15] -= np.linspace(0, 5, 15)   # Flag
    
    # Add noise
    prices = base_trend + noise
    
    # Create OHLCV data
    df = pd.DataFrame({
        'timestamp': dates,
        'symbol': symbol,
        'timeframe': timeframe,
        'Open': prices,
        'High': prices + np.random.uniform(0.1, 0.5, n),
        'Low': prices - np.random.uniform(0.1, 0.5, n),
        'Close': prices,
        'Volume': np.random.uniform(1000, 5000, n)
    })
    
    # Increase volume during pole formation
    df.loc[flag1_start-20:flag1_start, 'Volume'] *= 2
    df.loc[flag2_start-20:flag2_start, 'Volume'] *= 2
    
    # Decrease volume during flag formation
    df.loc[flag1_start:flag1_start+15, 'Volume'] *= 0.5
    df.loc[flag2_start:flag2_start+15, 'Volume'] *= 0.5
    
    return df.set_index('timestamp')

async def main():
    # Initialize database handler
    db = SQLDatabaseHandler()
    
    # Clear existing data
    print("Clearing existing data...")
    db.clear_table('price_bars')
    
    # Create and store sample data
    print("Creating sample data...")
    data = create_sample_data()
    db.store_bars('AAPL', '1h', data)
    
    # Create optimizer
    optimizer = VectorBtOptimizer(FlagPatternDetector, db)
    
    # Define parameter grid
    param_grid = {
        'min_pole_height': [0.005, 0.0075, 0.01],        # Reduced from [0.01, 0.015, 0.02]
        'max_flag_height_ratio': [0.5, 0.75, 1.0],     # Keeping same
        'volume_decline_threshold': [0.7, 0.8, 0.9],   # Keeping same
        'min_confidence': [0.3, 0.4, 0.5]              # Keeping same
    }
    
    # Run optimization
    print("Starting optimization...")
    results = optimizer.optimize(
        symbol='AAPL',
        timeframe='1h',
        param_grid=param_grid
    )
    
    print("\nOptimization Results:")
    print(results)
    
    # Get best parameters
    best_params = optimizer.get_best_parameters()
    print("\nBest Parameters:")
    print(best_params)
    
    # Plot results
    optimizer.plot_results()
    
    # Get optimization history
    history = db.get_optimization_history(
        strategy_name='FlagPatternDetector',
        symbol='AAPL',
        limit=5
    )
    print("\nRecent Optimization History:")
    print(history)
    
if __name__ == "__main__":
    asyncio.run(main()) 