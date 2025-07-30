import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import pytest

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from core.ta_engine.patterns.base_detector import DetectionResult
from core.ta_engine.patterns.flag_pattern import FlagPatternDetector, FlagConfig
from core.data_engine.sql_database import SQLDatabaseHandler

def create_sample_data(symbol: str = 'AAPL', timeframe: str = '1h') -> pd.DataFrame:
    """Create sample price data with flag patterns"""
    logger.debug(f"Creating sample data for {symbol} on {timeframe} timeframe")
    
    try:
        # Create date range
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        freq = '1H' if timeframe == '1h' else '1D' if timeframe == '1d' else '15min'
        dates = pd.date_range(start=start_date, end=end_date, freq=freq)
        n = len(dates)
        logger.debug(f"Generated {n} bars of data")
        
        # Generate base price trend with noise
        base_trend = np.linspace(100, 150, n)
        noise = np.random.normal(0, 0.5, n)
        prices = base_trend + noise
        
        # Create bullish flag pattern at 1/3 through the data
        flag1_start = n // 3
        prices[flag1_start:flag1_start+10] += np.linspace(0, 5, 10)  # Pole
        prices[flag1_start+10:flag1_start+20] += 5 + np.random.normal(0, 0.2, 10)  # Flag
        logger.debug(f"Added bullish flag pattern at index {flag1_start}")
        
        # Create bearish flag pattern at 2/3 through the data
        flag2_start = 2 * n // 3
        prices[flag2_start:flag2_start+10] -= np.linspace(0, 5, 10)  # Pole
        prices[flag2_start+10:flag2_start+20] -= 5 + np.random.normal(0, 0.2, 10)  # Flag
        logger.debug(f"Added bearish flag pattern at index {flag2_start}")
        
        # Generate OHLC data
        df = pd.DataFrame({
            'timestamp': dates,
            'symbol': symbol,
            'timeframe': timeframe,
            'Open': prices + np.random.normal(0, 0.2, n),
            'High': prices + np.random.uniform(0.1, 0.5, n),
            'Low': prices - np.random.uniform(0.1, 0.5, n),
            'Close': prices + np.random.normal(0, 0.2, n),
            'Volume': np.random.uniform(1000, 5000, n)
        })
        
        # Adjust volume profile
        df.loc[flag1_start:flag1_start+10, 'Volume'] *= 2  # Higher volume during pole
        df.loc[flag1_start+10:flag1_start+20, 'Volume'] *= 0.5  # Lower volume during flag
        df.loc[flag2_start:flag2_start+10, 'Volume'] *= 2
        df.loc[flag2_start+10:flag2_start+20, 'Volume'] *= 0.5
        
        logger.debug(f"Sample data creation completed. DataFrame shape: {df.shape}")
        logger.debug(f"DataFrame columns: {df.columns.tolist()}")
        logger.debug(f"First few rows:\n{df.head()}")
        return df
        
    except Exception as e:
        logger.error(f"Error creating sample data: {str(e)}")
        raise

@pytest.fixture
def db():
    """Database fixture"""
    db = SQLDatabaseHandler('financial_data.db')
    return db

@pytest.fixture
def detector():
    """Flag pattern detector fixture"""
    return FlagPatternDetector(FlagConfig())

@pytest.mark.parametrize("symbol,timeframe", [
    ('AAPL', '15min'),
    ('MSFT', '1h'),
    ('GOOGL', '1d')
])
def test_flag_pattern_detection(db, detector, symbol, timeframe):
    """Test flag pattern detection"""
    logger.info(f"\nTesting {symbol} on {timeframe} timeframe")
    logger.info("=" * 50)
    
    try:
        # Create and store sample data
        df = create_sample_data(symbol, timeframe)
        logger.debug(f"Created sample data with shape: {df.shape}")
        logger.debug(f"DataFrame columns: {df.columns.tolist()}")
        
        db.store_bars(symbol, timeframe, df)
        logger.debug("Stored bars in database")
        
        # Run detection
        patterns = []
        for i in range(len(df)):
            data = {
                'High': df['High'].values,
                'Low': df['Low'].values,
                'Close': df['Close'].values,
                'Volume': df['Volume'].values,
                'timestamp': df['timestamp'].values
            }
            pattern = detector.detect(data, i)
            if pattern:
                pattern.timestamp = df['timestamp'].iloc[i]  # Set timestamp from data
                patterns.append(pattern)
                logger.debug(f"Found pattern at index {i}")
        
        # Print results
        logger.info(f"\nDetected {len(patterns)} patterns:")
        for i, pattern in enumerate(patterns, 1):
            logger.info(f"\nPattern {i}:")
            logger.info(f"Type: {pattern.pattern_type}")
            logger.info(f"Timestamp: {pattern.timestamp}")
            logger.info(f"Entry Price: {pattern.entry_price:.2f}")
            logger.info(f"Stop Loss: {pattern.stop_loss:.2f}")
            logger.info(f"Take Profit: {pattern.take_profit:.2f}")
            logger.info(f"Confidence: {pattern.confidence:.2f}")
            logger.info("\nMetadata:")
            for key, value in pattern.metadata.items():
                logger.info(f"  {key}: {value:.4f}")
        
        # Assertions
        assert len(patterns) > 0, "No patterns detected"
        assert any(p.pattern_type == "BULLISH_FLAG" for p in patterns), "No bullish flags detected"
        assert any(p.pattern_type == "BEARISH_FLAG" for p in patterns), "No bearish flags detected"
        
    except Exception as e:
        logger.error(f"Error processing {symbol} on {timeframe}: {str(e)}")
        raise 