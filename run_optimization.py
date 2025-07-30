import pandas as pd
from core.optimization.flag_pattern_optimizer import FlagPatternOptimizer
from core.data_engine.sql_database import SQLDatabaseHandler
import logging
from core.ta_engine.patterns.flag_pattern import FlagPatternDetector, FlagConfig
import vectorbt as vbt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_pattern_detection(df, config):
    """Analyze pattern detection statistics"""
    detector = FlagPatternDetector(config)
    total_checks = 0
    patterns_found = 0
    bullish_patterns = 0
    bearish_patterns = 0
    
    for i in range(len(df)):
        total_checks += 1
        data = {
            'High': df['high'].values,
            'Low': df['low'].values,
            'Close': df['close'].values,
            'Volume': df['volume'].values,
            'timestamp': df.index.values
        }
        pattern = detector.detect(data, i)
        
        if pattern:
            patterns_found += 1
            if pattern.pattern_type == 'BULLISH_FLAG':
                bullish_patterns += 1
            elif pattern.pattern_type == 'BEARISH_FLAG':
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
    
    # Test ranges for each parameter
    param_ranges = {
        'min_pole_height': [0.02, 0.03, 0.04, 0.05, 0.06],  # Increased pole height requirements for stronger trends
        'min_flag_bars': [3, 4, 5, 6, 7],  # Focus on medium-length consolidations
        'max_flag_bars': [8, 10, 12, 15, 20],  # Shorter max bars for tighter patterns
        'max_flag_width_ratio': [1.5, 2.0, 2.5, 3.0, 3.5],  # More conservative width ratios
        'max_flag_height_ratio': [0.3, 0.4, 0.5, 0.6, 0.7],  # Tighter height ratios for cleaner flags
        'min_confidence': [0.4, 0.5, 0.6, 0.7, 0.8]  # Higher confidence thresholds
    }
    
    # Default configuration with refined values
    default_config = {
        'min_pole_height': 0.03,     # Strong trend requirement (3%)
        'min_flag_bars': 5,          # Optimal consolidation period
        'max_flag_bars': 12,         # Tight upper bound
        'max_flag_width_ratio': 2.5,  # Conservative width ratio
        'max_flag_height_ratio': 0.7, # Optimal height ratio for pattern quality
        'volume_decline': 0.0,        # Volume check disabled
        'min_confidence': 0.5         # Balanced confidence threshold
    }
    
    # Test each parameter individually
    for param_name, param_values in param_ranges.items():
        logger.info(f"\nTesting {param_name}:")
        logger.info("=" * 50)
        
        for value in param_values:
            # Create config with current parameter value
            test_config = default_config.copy()
            test_config[param_name] = value
            config = FlagConfig(**test_config)
            
            # Analyze pattern detection
            stats = analyze_pattern_detection(df, config)
            
            # Run backtest
            detector = FlagPatternDetector(config)
            entry_signals = pd.Series(0, index=df.index)
            exit_signals = pd.Series(0, index=df.index)
            
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
                        entry_signals.iloc[i] = 1
                        # Exit after N bars
                        exit_idx = min(i + 5, len(df) - 1)  # Exit after 5 bars or at end
                        exit_signals.iloc[exit_idx] = 1
                    elif pattern.pattern_type == 'BEARISH_FLAG':
                        entry_signals.iloc[i] = -1
                        # Exit after N bars
                        exit_idx = min(i + 5, len(df) - 1)  # Exit after 5 bars or at end
                        exit_signals.iloc[exit_idx] = 1
            
            # Run vectorbt backtest with proper exits
            portfolio = vbt.Portfolio.from_signals(
                close=df['close'],
                entries=entry_signals == 1,
                exits=exit_signals == 1,
                short_entries=entry_signals == -1,
                short_exits=exit_signals == 1,
                size=0.1,  # Use 10% of portfolio per trade
                size_type='percent',  # Size as percentage of portfolio
                init_cash=100000,
                fees=0.001,
                freq='1D'
            )
            
            # Calculate metrics
            metrics = {
                'total_return': portfolio.total_return(),
                'sharpe_ratio': portfolio.sharpe_ratio(),
                'max_drawdown': portfolio.max_drawdown(),
                'sortino_ratio': portfolio.sortino_ratio()
            }
            
            logger.info(f"\n{param_name} = {value}:")
            logger.info(f"Patterns found: {stats['patterns_found']} ({stats['patterns_found']/stats['total_checks']*100:.2f}%)")
            logger.info(f"Bullish/Bearish ratio: {stats['bullish_patterns']}/{stats['bearish_patterns']}")
            logger.info(f"Total return: {metrics['total_return']:.2%}")
            logger.info(f"Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
            logger.info(f"Max drawdown: {metrics['max_drawdown']:.2%}")
            logger.info(f"Sortino ratio: {metrics['sortino_ratio']:.2f}")

def main():
    # Initialize database and optimizer
    db = SQLDatabaseHandler('financial_data.db')
    optimizer = FlagPatternOptimizer(db)
    
    # Run individual parameter tests for Q1 2023
    run_individual_parameter_tests(
        optimizer=optimizer,
        symbol='GOOGL',
        timeframe='1d',
        start_date='2023-01-01',
        end_date='2023-03-31'
    )

if __name__ == '__main__':
    main() 