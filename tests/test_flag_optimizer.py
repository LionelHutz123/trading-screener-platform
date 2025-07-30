import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import pytest

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from core.optimization.flag_pattern_optimizer import FlagPatternOptimizer
from core.data_engine.sql_database import SQLDatabaseHandler
from core.ta_engine.patterns.flag_pattern import FlagConfig

def create_sample_data():
    # Create sample data for testing
    dates = pd.date_range(start='2023-01-01', end='2023-01-31', freq='1H')
    n = len(dates)
    
    # Create a trend with some flag patterns
    close = np.linspace(100, 200, n) + np.random.normal(0, 5, n)
    high = close + np.random.uniform(0, 2, n)
    low = close - np.random.uniform(0, 2, n)
    volume = np.random.uniform(1000, 5000, n)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': close,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })
    return df

@pytest.fixture
def db():
    # Create temporary database for testing
    db = SQLDatabaseHandler(':memory:')
    df = create_sample_data()
    db.store_bars('AAPL', '1h', df)
    return db

@pytest.fixture
def optimizer(db):
    return FlagPatternOptimizer(db)

def test_parameter_generation(optimizer):
    params = optimizer.generate_param_space()
    assert len(params) > 0
    assert isinstance(params, dict)
    assert 'min_pole_height' in params
    assert 'min_flag_bars' in params

def test_optimization(optimizer):
    results = optimizer.run_optimization('AAPL', '1h', 
                                      start_date='2023-01-01',
                                      end_date='2023-01-31')
    assert isinstance(results, pd.DataFrame)
    assert len(results) > 0
    assert 'sharpe_ratio' in results.columns
    assert 'total_return' in results.columns

def test_best_parameters(optimizer):
    # Run optimization first
    optimizer.run_optimization('AAPL', '1h', 
                             start_date='2023-01-01',
                             end_date='2023-01-31')
    
    # Get best parameters
    best_params = optimizer.get_best_parameters()
    assert isinstance(best_params, dict)
    assert 'parameters' in best_params
    assert isinstance(best_params['parameters'], dict)

def test_single_backtest(optimizer):
    config = FlagConfig(
        min_pole_height=0.02,
        min_flag_bars=5,
        max_flag_bars=20,
        max_flag_width_ratio=2.0,
        max_flag_height_ratio=0.5,
        volume_decline=0.8,
        min_confidence=0.6
    )
    
    metrics = optimizer._run_single_backtest('AAPL', '1h',
                                           start_date='2023-01-01',
                                           end_date='2023-01-31',
                                           config=config)
    
    assert isinstance(metrics, dict)
    assert 'sharpe_ratio' in metrics
    assert 'total_return' in metrics
    assert metrics['total_return'] >= -100  # Ensure return is not unreasonable 