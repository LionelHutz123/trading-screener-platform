import vectorbt as vbt
from dataclasses import dataclass
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
from core.ta_engine.patterns.base_detector import DetectionStrategy, DetectionResult

@dataclass
class DivergenceConfig:
    rsi_period: int = 14
    pivot_lookback_left: int = 5
    pivot_lookback_right: int = 5
    range_upper: int = 60  # Max bars to look back
    range_lower: int = 5   # Min bars to look back
    include_hidden: bool = False  # Whether to detect hidden divergences

class RSIDivergenceStrategy(DetectionStrategy):
    """Implements RSI divergence detection strategy"""
    
    def __init__(self, config: DivergenceConfig):
        self.config = config
        
    def detect(self, data: pd.DataFrame) -> List[DetectionResult]:
        """Detect RSI divergences"""
        results = []
        data = data.copy()
        
        # Calculate RSI using vectorbt
        rsi = vbt.RSI.run(data['Close'], window=self.config.rsi_period).rsi
        data['RSI'] = rsi
        
        # Add debug logging
        print(f"RSI range: {data['RSI'].min():.2f} to {data['RSI'].max():.2f}")
        
        # Find pivot points
        for i in range(self.config.pivot_lookback_left + self.config.pivot_lookback_right, len(data)-1):
            # Check for pivot lows (bullish divergence)
            if self._is_pivot_low(data['RSI'], i):
                prev_pivot_idx = self._find_previous_pivot_low(data['RSI'], i)
                if prev_pivot_idx and self._is_in_range(i - prev_pivot_idx):
                    # Regular bullish divergence
                    if data['Low'].iloc[i] < data['Low'].iloc[prev_pivot_idx] and \
                       data['RSI'].iloc[i] > data['RSI'].iloc[prev_pivot_idx]:
                        print(f"Found bullish divergence at {data['timestamp'].iloc[i]}")
                        results.append(self._create_bullish_result(data, i, prev_pivot_idx))
                    
                    # Hidden bullish divergence
                    elif self.config.include_hidden and \
                         data['Low'].iloc[i] > data['Low'].iloc[prev_pivot_idx] and \
                         data['RSI'].iloc[i] < data['RSI'].iloc[prev_pivot_idx]:
                        print(f"Found hidden bullish divergence at {data['timestamp'].iloc[i]}")
                        results.append(self._create_bullish_result(data, i, prev_pivot_idx, hidden=True))
            
            # Check for pivot highs (bearish divergence)
            if self._is_pivot_high(data['RSI'], i):
                prev_pivot_idx = self._find_previous_pivot_high(data['RSI'], i)
                if prev_pivot_idx and self._is_in_range(i - prev_pivot_idx):
                    # Regular bearish divergence
                    if data['High'].iloc[i] > data['High'].iloc[prev_pivot_idx] and \
                       data['RSI'].iloc[i] < data['RSI'].iloc[prev_pivot_idx]:
                        print(f"Found bearish divergence at {data['timestamp'].iloc[i]}")
                        results.append(self._create_bearish_result(data, i, prev_pivot_idx))
                    
                    # Hidden bearish divergence
                    elif self.config.include_hidden and \
                         data['High'].iloc[i] < data['High'].iloc[prev_pivot_idx] and \
                         data['RSI'].iloc[i] > data['RSI'].iloc[prev_pivot_idx]:
                        print(f"Found hidden bearish divergence at {data['timestamp'].iloc[i]}")
                        results.append(self._create_bearish_result(data, i, prev_pivot_idx, hidden=True))
        
        return results
    
    def _is_pivot_high(self, series: pd.Series, idx: int) -> bool:
        """Check if point is a pivot high"""
        left = series.iloc[idx-self.config.pivot_lookback_left:idx]
        right = series.iloc[idx+1:idx+self.config.pivot_lookback_right+1]
        return series.iloc[idx] > left.max() and series.iloc[idx] > right.max()
    
    def _is_pivot_low(self, series: pd.Series, idx: int) -> bool:
        """Check if point is a pivot low"""
        left = series.iloc[idx-self.config.pivot_lookback_left:idx]
        right = series.iloc[idx+1:idx+self.config.pivot_lookback_right+1]
        return series.iloc[idx] < left.min() and series.iloc[idx] < right.min()
    
    def _find_previous_pivot_high(self, series: pd.Series, current_idx: int) -> Optional[int]:
        """Find the previous pivot high"""
        for i in range(current_idx - self.config.range_lower, 
                      max(self.config.pivot_lookback_left, current_idx - self.config.range_upper), -1):
            if self._is_pivot_high(series, i):
                return i
        return None
    
    def _find_previous_pivot_low(self, series: pd.Series, current_idx: int) -> Optional[int]:
        """Find the previous pivot low"""
        for i in range(current_idx - self.config.range_lower, 
                      max(self.config.pivot_lookback_left, current_idx - self.config.range_upper), -1):
            if self._is_pivot_low(series, i):
                return i
        return None
    
    def _is_in_range(self, bars_since: int) -> bool:
        """Check if bars since last pivot is within valid range"""
        return self.config.range_lower <= bars_since <= self.config.range_upper
    
    def _create_bullish_result(self, data: pd.DataFrame, current_idx: int, prev_idx: int, hidden: bool = False) -> DetectionResult:
        """Create bullish divergence result"""
        pattern_type = "RSI_HIDDEN_BULLISH_DIVERGENCE" if hidden else "RSI_BULLISH_DIVERGENCE"
        return DetectionResult(
            pattern_type=pattern_type,
            timestamp=data['timestamp'].iloc[current_idx],
            entry_price=data['Close'].iloc[current_idx],
            stop_loss=data['Low'].iloc[current_idx] * 0.995,  # 0.5% below
            take_profit=data['High'].iloc[current_idx:current_idx+10].max(),  # Next 10 bars high
            confidence=abs(data['RSI'].iloc[current_idx] - data['RSI'].iloc[prev_idx]) / 100.0,
            metadata={
                'rsi_current': data['RSI'].iloc[current_idx],
                'rsi_previous': data['RSI'].iloc[prev_idx],
                'price_current': data['Low'].iloc[current_idx],
                'price_previous': data['Low'].iloc[prev_idx],
                'bars_between': current_idx - prev_idx
            }
        )
    
    def _create_bearish_result(self, data: pd.DataFrame, current_idx: int, prev_idx: int, hidden: bool = False) -> DetectionResult:
        """Create bearish divergence result"""
        pattern_type = "RSI_HIDDEN_BEARISH_DIVERGENCE" if hidden else "RSI_BEARISH_DIVERGENCE"
        return DetectionResult(
            pattern_type=pattern_type,
            timestamp=data['timestamp'].iloc[current_idx],
            entry_price=data['Close'].iloc[current_idx],
            stop_loss=data['High'].iloc[current_idx] * 1.005,  # 0.5% above
            take_profit=data['Low'].iloc[current_idx:current_idx+10].min(),  # Next 10 bars low
            confidence=abs(data['RSI'].iloc[current_idx] - data['RSI'].iloc[prev_idx]) / 100.0,
            metadata={
                'rsi_current': data['RSI'].iloc[current_idx],
                'rsi_previous': data['RSI'].iloc[prev_idx],
                'price_current': data['High'].iloc[current_idx],
                'price_previous': data['High'].iloc[prev_idx],
                'bars_between': current_idx - prev_idx
            }
        )
    
    def get_required_columns(self) -> List[str]:
        return ['timestamp', 'High', 'Low', 'Close']