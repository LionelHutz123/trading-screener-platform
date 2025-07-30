import pandas as pd
from core.optimization.order_block_optimizer import OrderBlockOptimizer
from core.data_engine.sql_database import SQLDatabaseHandler
import logging
from core.ta_engine.patterns.order_block import OrderBlockDetector, OrderBlockConfig
import vectorbt as vbt
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_data(df):
    """Analyze price data characteristics"""
    # Calculate daily returns and volatility
    returns = df['close'].pct_change()
    volatility = returns.std()
    
    # Calculate average candle sizes
    candle_body = abs(df['close'] - df['open'])
    candle_range = df['high'] - df['low']
    avg_price = (df['high'] + df['low']) / 2
    
    body_ratios = candle_body / avg_price
    range_ratios = candle_range / avg_price
    
    # Calculate volume characteristics
    volume_mean = df['volume'].mean()
    volume_std = df['volume'].std()
    volume_ratios = df['volume'] / df['volume'].rolling(10).mean()
    
    # Log analysis
    logger.info("\nData Analysis:")
    logger.info(f"Number of bars: {len(df)}")
    logger.info(f"Daily volatility: {volatility:.2%}")
    logger.info(f"Average candle body ratio: {body_ratios.mean():.2%}")
    logger.info(f"Average candle range ratio: {range_ratios.mean():.2%}")
    logger.info(f"95th percentile candle range: {range_ratios.quantile(0.95):.2%}")
    logger.info(f"Average volume ratio: {volume_ratios.mean():.2f}")
    logger.info(f"95th percentile volume ratio: {volume_ratios.quantile(0.95):.2f}")
    
    # Suggest parameter ranges
    logger.info("\nSuggested parameter ranges based on data:")
    logger.info(f"min_candle_size: {body_ratios.quantile(0.25):.3f}")
    logger.info(f"max_candle_size: {range_ratios.quantile(0.95):.3f}")
    logger.info(f"min_volume_ratio: {volume_ratios.quantile(0.75):.2f}")

def analyze_pattern_detection(df, config):
    """Analyze pattern detection statistics"""
    detector = OrderBlockDetector(config)
    total_checks = 0
    patterns_found = 0
    bullish_patterns = 0
    bearish_patterns = 0
    
    for i in range(len(df)):
        total_checks += 1
        data = {
            'high': df['high'].values,
            'low': df['low'].values,
            'close': df['close'].values,
            'open': df['open'].values,
            'volume': df['volume'].values,
            'timestamp': df.index.values
        }
        pattern = detector.detect(data, i)
        
        if pattern:
            patterns_found += 1
            if pattern.pattern_type == 'BULLISH_ORDER_BLOCK':
                bullish_patterns += 1
            elif pattern.pattern_type == 'BEARISH_ORDER_BLOCK':
                bearish_patterns += 1
    
    # Print analysis
    logger.info(f"\nPattern Detection Analysis:")
    logger.info(f"Total bars analyzed: {total_checks}")
    logger.info(f"Patterns found: {patterns_found} ({patterns_found/total_checks*100:.2f}%)")
    logger.info(f"Bullish patterns: {bullish_patterns}")
    logger.info(f"Bearish patterns: {bearish_patterns}")
    logger.info(f"\nConfiguration used:")
    for param, value in config.__dict__.items():
        logger.info(f"{param}: {value}")
    
    return {
        'total_checks': total_checks,
        'patterns_found': patterns_found,
        'bullish_patterns': bullish_patterns,
        'bearish_patterns': bearish_patterns
    }

def run_individual_parameter_tests(optimizer, symbol: str, timeframe: str, start_date: str, end_date: str):
    """Test each parameter individually while keeping others at default values"""
    logger.info(f"\nRunning individual parameter tests ({start_date} to {end_date})...")
    
    # Get data first
    df = optimizer.db.get_bars(symbol, timeframe, start_date, end_date)
    
    # Analyze data characteristics
    analyze_data(df)
    
    # Test ranges for each parameter
    param_ranges = {
        'min_imbalance': [0.002, 0.003, 0.005, 0.007, 0.01],  # 0.2-1% imbalance
        'max_age_bars': [5, 10, 15, 20, 25],                  # Bar range for valid blocks
        'min_volume_ratio': [1.1, 1.2, 1.3, 1.4, 1.5],       # Volume compared to average
        'min_candle_size': [0.001, 0.002, 0.003, 0.004, 0.005], # 0.1-0.5% candle size
        'max_candle_size': [0.005, 0.007, 0.01, 0.012, 0.015],  # 0.5-1.5% max candle size
        'lookback_period': [5, 10, 15, 20, 25],               # Periods for volume average
        'min_confidence': [0.3, 0.4, 0.5, 0.6, 0.7]           # Confidence threshold
    }
    
    # Default configuration with initial values
    default_config = {
        'min_imbalance': 0.003,     # 0.3% minimum imbalance
        'max_age_bars': 15,         # 15 bars maximum age
        'min_volume_ratio': 1.2,    # 1.2x average volume
        'min_candle_size': 0.002,   # 0.2% minimum candle size
        'max_candle_size': 0.01,    # 1% maximum candle size
        'lookback_period': 10,      # 10 bars for volume average
        'min_confidence': 0.4       # 0.4 minimum confidence
    }
    
    # Test each parameter individually
    for param_name, param_values in param_ranges.items():
        logger.info(f"\nTesting {param_name}:")
        logger.info("=" * 50)
        
        for value in param_values:
            # Create config with current parameter value
            test_config = default_config.copy()
            test_config[param_name] = value
            config = OrderBlockConfig(**test_config)
            
            # Analyze pattern detection
            stats = analyze_pattern_detection(df, config)
            
            # Skip backtest if no patterns found
            if stats['patterns_found'] == 0:
                logger.info(f"\n{param_name} = {value}:")
                logger.info(f"Patterns found: 0 (0.00%)")
                logger.info(f"Bullish/Bearish ratio: 0/0")
                logger.info("No patterns found, skipping backtest")
                continue
            
            # Run backtest
            detector = OrderBlockDetector(config)
            entry_signals = pd.Series(0, index=df.index)
            exit_signals = pd.Series(0, index=df.index)
            
            # Generate signals
            for i in range(len(df)):
                data = {
                    'high': df['high'].values,
                    'low': df['low'].values,
                    'close': df['close'].values,
                    'open': df['open'].values,
                    'volume': df['volume'].values,
                    'timestamp': df.index.values
                }
                pattern = detector.detect(data, i)
                
                if pattern:
                    # Set entry signal
                    entry_signals.iloc[i] = 1
                    # Set exit signal 5 bars later (configurable)
                    if i + 5 < len(df):
                        exit_signals.iloc[i + 5] = 1
            
            try:
                # Create portfolio
                pf = vbt.Portfolio.from_signals(
                    close=df['close'],
                    entries=entry_signals,
                    exits=exit_signals,
                    size=0.1,  # Use 10% of portfolio per trade
                    size_type='percent',
                    init_cash=100000,
                    fees=0.001,  # 0.1% trading fee
                    freq='1D'
                )
                
                # Calculate metrics safely
                total_return = pf.total_return if not np.isnan(pf.total_return) else 0.0
                sharpe_ratio = pf.sharpe_ratio if not np.isnan(pf.sharpe_ratio) else 0.0
                max_drawdown = pf.max_drawdown if not np.isnan(pf.max_drawdown) else 0.0
                sortino_ratio = pf.sortino_ratio if not np.isnan(pf.sortino_ratio) else 0.0
                
                # Log results
                logger.info(f"\n{param_name} = {value}:")
                logger.info(f"Patterns found: {stats['patterns_found']} ({stats['patterns_found']/stats['total_checks']*100:.2f}%)")
                logger.info(f"Bullish/Bearish ratio: {stats['bullish_patterns']}/{stats['bearish_patterns']}")
                logger.info(f"Total return: {total_return:.2%}")
                logger.info(f"Sharpe ratio: {sharpe_ratio:.2f}")
                logger.info(f"Max drawdown: {max_drawdown:.2%}")
                logger.info(f"Sortino ratio: {sortino_ratio:.2f}")
            
            except Exception as e:
                logger.warning(f"Error in backtest calculation: {str(e)}")
                logger.info(f"\n{param_name} = {value}:")
                logger.info(f"Patterns found: {stats['patterns_found']} ({stats['patterns_found']/stats['total_checks']*100:.2f}%)")
                logger.info(f"Bullish/Bearish ratio: {stats['bullish_patterns']}/{stats['bearish_patterns']}")
                logger.info("Could not calculate performance metrics")

def main():
    # Initialize database and optimizer
    db = SQLDatabaseHandler()
    optimizer = OrderBlockOptimizer(db)
    
    # Run individual parameter tests
    run_individual_parameter_tests(
        optimizer=optimizer,
        symbol='GOOGL',
        timeframe='1d',
        start_date='2023-01-01',
        end_date='2023-03-31'
    )

if __name__ == '__main__':
    main() 