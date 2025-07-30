import sys
import os

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from core.ta_engine.order_blocks import (
    OrderBlockDetector, 
    FVGDetector,
    SwingFailureDetector,
    OrderBlockConfig,
    FVGConfig,
    SwingFailureConfig
)
from core.ta_engine.divergences import RSIDivergenceStrategy, DivergenceConfig
from core.ta_engine.patterns import (
    FlagPatternDetector, 
    FlagConfig,
    CHoCHDetector,
    CHoCHConfig
)
import vectorbt as vbt

class StrategyValidator:
    def __init__(self, csv_path=None):
        # Default to WYNN if no path provided
        if not csv_path:
            csv_path = "WYNN_4h_2022-01-01_2024-09-13.csv"
        self.df = self._load_and_format_data(csv_path)
        self.results = {}
        
    def _load_and_format_data(self, path):
        """Adapt CSV data to strategy expectations"""
        df = pd.read_csv(path, parse_dates=['timestamp'])
        # Keep original column order but don't set index
        return df[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']]

    def _plot_strategy_events(self, strategy_name, events):
        """Generate candlestick chart with strategy markers"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 15), gridspec_kw={'height_ratios': [2, 1]})
        
        # Plot price data on top subplot
        ax1.plot(self.df['timestamp'], self.df['Close'], 
                label='Price', color='black', alpha=0.7)
        
        # Calculate and plot RSI on bottom subplot
        rsi = vbt.RSI.run(self.df['Close'], window=14).rsi
        ax2.plot(self.df['timestamp'], rsi, label='RSI', color='blue', alpha=0.7)
        ax2.axhline(y=70, color='r', linestyle='--', alpha=0.5)  # Overbought line
        ax2.axhline(y=30, color='g', linestyle='--', alpha=0.5)  # Oversold line
        ax2.set_ylim(0, 100)
        ax2.set_title('RSI (14)')
        
        # Plot strategy-specific markers on price chart
        colors = {
            'BULL': 'green',
            'BEAR': 'red',
            'FVG': 'blue',
            'SWING_FAIL': 'orange',
            'DIVERGENCE': 'purple',
            'FLAG': 'cyan',
            'CHOCH': 'magenta'
        }
        
        for event in events:
            marker = self._get_marker(event.pattern_type)
            pattern_type = event.pattern_type.split('_')[0]
            color = colors.get(pattern_type, 'gray')
            ax1.scatter(event.timestamp, event.entry_price,
                       marker=marker, color=color, s=100,
                       label=f'{strategy_name} - {event.pattern_type}')
            
            # Add stop loss and take profit levels for CHoCH patterns
            if 'CHOCH' in event.pattern_type:
                ax1.axhline(y=event.stop_loss, color=color, linestyle=':', alpha=0.5)
                ax1.axhline(y=event.take_profit, color=color, linestyle='--', alpha=0.5)

        ax1.set_title(f'{strategy_name} Detection Results')
        ax1.legend()
        ax2.legend()
        
        # Format x-axis
        plt.gcf().autofmt_xdate()
        
        plt.tight_layout()
        plt.show()

    def _get_marker(self, pattern_type):
        """Map event types to plot markers"""
        return {
            'BULLISH_ORDER_BLOCK': '^',
            'BEARISH_ORDER_BLOCK': 'v',
            'BULLISH_FVG': '>',
            'BEARISH_FVG': '<',
            'SWING_FAILURE': 'X',
            'RSI_BULLISH_DIVERGENCE': 'P',
            'RSI_BEARISH_DIVERGENCE': 'D',
            'BULL_FLAG': 's',
            'BEAR_FLAG': 's',
            'BULLISH_CHOCH': '*',
            'BEARISH_CHOCH': 'h'
        }.get(pattern_type, 'o')

    def _generate_stats(self, strategy_name, events):
        """Calculate performance metrics"""
        stats = {
            'total_events': len(events),
            'bullish_count': sum(1 for e in events if 'BULL' in e.pattern_type),
            'bearish_count': sum(1 for e in events if 'BEAR' in e.pattern_type),
            'avg_confidence': np.mean([e.confidence for e in events]) if events else 0,
            'avg_hold_period': None,
            'success_rate': None
        }
        
        # Add strategy-specific metrics
        if 'CHOCH' in strategy_name:
            # Calculate average swing strength
            swing_strengths = [e.metadata.get('swing_strength', 0) for e in events]
            volume_ratios = [e.metadata.get('volume_ratio', 0) for e in events]
            stats.update({
                'avg_swing_strength': np.mean(swing_strengths),
                'avg_volume_ratio': np.mean(volume_ratios),
                'strong_moves': sum(1 for s in swing_strengths if s > 0.5)
            })
            
        return stats

    def run_full_analysis(self):
        """Execute all strategy tests"""
        strategies = {
            'CHoCH Patterns': self.test_choch,
            'Flag Patterns': self.test_flag_patterns
        }
        
        report = {}
        for name, test_fn in strategies.items():
            print(f"\n=== Testing {name} ===")
            events = test_fn()
            self._plot_strategy_events(name, events)
            report[name] = self._generate_stats(name, events)
            
        self._generate_final_report(report)
        return report

    def test_order_blocks(self):
        """Order Block Strategy Test"""
        config = OrderBlockConfig(
            window_size=14,
            n_pips=3,
            min_strength=0.4
        )
        detector = OrderBlockDetector(config)
        events = detector.detect(self.df)
        self.results['order_blocks'] = events
        return events

    def test_fvg(self):
        """Test Fair Value Gap detection"""
        config = FVGConfig(
            min_gap_size=0.01,       # Increased to 1%
            lookback_window=3,        # Keep at 3 bars
            trend_threshold=0.015,    # Increased to 1.5%
            volume_weight=0.4,        # Keep at 0.4
            min_candle_size=0.005    # Increased to 0.5%
        )
        detector = FVGDetector(config)
        events = detector.detect(self.df)
        self.results['fvg'] = events
        return events

    def test_swing_failures(self):
        """Test swing failure detection"""
        config = SwingFailureConfig(
            min_swing_size=0.001,  # More sensitive
            retracement_threshold=0.382,  # Fibonacci level
            volume_increase_factor=1.1,  # Lower volume requirement
            confirmation_candles=2,
            swing_length=3  # Shorter swing length
        )
        detector = SwingFailureDetector(config)
        events = detector.detect(self.df)
        self.results['swing_failures'] = events
        return events

    def test_rsi_divergence(self):
        """Test RSI divergence detection"""
        config = DivergenceConfig(
            rsi_period=14,
            pivot_lookback_left=5,
            pivot_lookback_right=5,
            range_upper=60,
            range_lower=5,
            include_hidden=True  # Include hidden divergences for more signals
        )
        detector = RSIDivergenceStrategy(config)
        events = detector.detect(self.df)
        self.results['rsi_divergence'] = events
        return events

    def test_flag_patterns(self):
        """Flag Pattern Test"""
        config = FlagConfig(
            min_pole_height=0.03,     # 3% minimum flag pole
            min_flag_bars=5,          # At least 5 bars in flag
            max_flag_bars=15,         # At most 15 bars in flag
            max_retracement=0.382,    # Fibonacci retracement
            volume_decline=0.7,       # Volume should decline by 30%
            breakout_threshold=0.005,  # 0.5% breakout confirmation
            trend_bars=20,            # Look back for trend
            min_confidence=0.65       # Minimum confidence threshold
        )
        detector = FlagPatternDetector(config)
        events = detector.detect(self.df)
        self.results['flag_patterns'] = events
        return events

    def test_choch(self):
        """Test Change of Character detection"""
        config = CHoCHConfig(
            swing_window=5,         # Window for swing point detection
            min_swing_size=0.001,   # Minimum size for valid swing
            confirmation_bars=2,     # Bars to confirm the change
            trend_strength=0.2      # Minimum trend strength
        )
        detector = CHoCHDetector(config)
        events = detector.detect(self.df)
        self.results['choch'] = events
        return events

    def _generate_final_report(self, report):
        """Generate consolidated statistics"""
        print("\n=== Final Validation Report ===")
        for strategy, stats in report.items():
            print(f"\n{strategy}:")
            print(f" - Total Events: {stats['total_events']}")
            print(f" - Bullish/Bearish: {stats['bullish_count']}/{stats['bearish_count']}")
            if 'avg_swing_strength' in stats:
                print(f" - Avg Swing Strength: {stats['avg_swing_strength']:.2f}")
                print(f" - Avg Volume Ratio: {stats['avg_volume_ratio']:.2f}")
                print(f" - Strong Moves: {stats['strong_moves']}")

if __name__ == "__main__":
    # Test with TSLA which tends to have strong trend changes
    symbols = ["TSLA_4h_2022-01-01_2024-09-13.csv"]
    
    for symbol in symbols:
        print(f"\n{'='*50}")
        print(f"Testing {symbol}")
        print(f"{'='*50}")
        validator = StrategyValidator(symbol)
        report = validator.run_full_analysis()