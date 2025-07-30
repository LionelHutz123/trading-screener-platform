from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from typing import List, Optional
from ..patterns.detection_strategy import DetectionStrategy, DetectionResult

@dataclass
class SwingFailureConfig:
    min_swing_size: float = field(default=0.001)  # 0.1% minimum price movement
    retracement_threshold: float = field(default=0.382)  # 38.2% Fibonacci retracement
    volume_increase_factor: float = field(default=1.1)  # 10% volume spike required
    confirmation_candles: int = field(default=3)  # Candles to confirm failure
    swing_length: int = field(default=3)  # Length for swing detection

class SwingFailureDetector(DetectionStrategy):
    """Detects swing failure patterns with volume confirmation"""
    
    def __init__(self, config: SwingFailureConfig = SwingFailureConfig()):
        self.config = config
        
    def detect(self, data: pd.DataFrame) -> List[DetectionResult]:
        """Identify swing failure patterns with trend validation"""
        results = []
        data = data.copy().reset_index()
        
        # Calculate swing highs and lows
        highs = self._get_swing_points(data, high=True)
        lows = self._get_swing_points(data, high=False)
        
        # Detect failures
        for i in range(self.config.swing_length, len(data)-1):
            # Check for swing high failures
            if highs[i] and i > self.config.swing_length:
                result = self._check_swing_high_failure(data, i)
                if result:
                    results.append(result)
            
            # Check for swing low failures
            if lows[i] and i > self.config.swing_length:
                result = self._check_swing_low_failure(data, i)
                if result:
                    results.append(result)
                    
        return results

    def _get_swing_points(self, data: pd.DataFrame, high: bool = True) -> np.ndarray:
        """Identify swing points using price action"""
        swings = np.zeros(len(data), dtype=bool)
        length = self.config.swing_length
        
        for i in range(length, len(data)-length):
            if high:
                # Check if current high is higher than surrounding bars
                window = data['High'].iloc[i-length:i+length+1]
                if data['High'].iloc[i] == window.max() and data['Close'].iloc[i] > data['Open'].iloc[i]:
                    swings[i] = True
            else:
                # Check if current low is lower than surrounding bars
                window = data['Low'].iloc[i-length:i+length+1]
                if data['Low'].iloc[i] == window.min() and data['Close'].iloc[i] < data['Open'].iloc[i]:
                    swings[i] = True
        return swings

    def _check_swing_high_failure(self, data: pd.DataFrame, idx: int) -> Optional[DetectionResult]:
        """Check for valid swing high failure"""
        # Get previous swing high
        prev_high = data['High'].iloc[idx-self.config.swing_length:idx].max()
        current_high = data['High'].iloc[idx]
        
        # Check if price failed to make new high
        if current_high < prev_high:
            # Calculate retracement
            swing_range = prev_high - data['Low'].iloc[idx-self.config.swing_length:idx].min()
            retracement = (prev_high - current_high) / swing_range if swing_range > 0 else 0
            
            if retracement >= self.config.retracement_threshold:
                # Check volume confirmation
                avg_volume = data['Volume'].iloc[idx-self.config.confirmation_candles:idx].mean()
                if data['Volume'].iloc[idx] > avg_volume * self.config.volume_increase_factor:
                    return DetectionResult(
                        pattern_type="SWING_HIGH_FAILURE",
                        timestamp=data['timestamp'].iloc[idx],
                        entry_price=data['Close'].iloc[idx],
                        stop_loss=current_high * 1.005,  # 0.5% above failure point
                        take_profit=data['Low'].iloc[idx-self.config.swing_length:idx].min(),
                        confidence=self._calculate_failure_strength(data, idx, True),
                        metadata={
                            'prev_high': prev_high,
                            'failure_high': current_high,
                            'retracement': retracement,
                            'volume_increase': data['Volume'].iloc[idx] / avg_volume
                        }
                    )
        return None

    def _check_swing_low_failure(self, data: pd.DataFrame, idx: int) -> Optional[DetectionResult]:
        """Check for valid swing low failure"""
        # Get previous swing low
        prev_low = data['Low'].iloc[idx-self.config.swing_length:idx].min()
        current_low = data['Low'].iloc[idx]
        
        # Check if price failed to make new low
        if current_low > prev_low:
            # Calculate retracement
            swing_range = data['High'].iloc[idx-self.config.swing_length:idx].max() - prev_low
            retracement = (current_low - prev_low) / swing_range if swing_range > 0 else 0
            
            if retracement >= self.config.retracement_threshold:
                # Check volume confirmation
                avg_volume = data['Volume'].iloc[idx-self.config.confirmation_candles:idx].mean()
                if data['Volume'].iloc[idx] > avg_volume * self.config.volume_increase_factor:
                    return DetectionResult(
                        pattern_type="SWING_LOW_FAILURE",
                        timestamp=data['timestamp'].iloc[idx],
                        entry_price=data['Close'].iloc[idx],
                        stop_loss=current_low * 0.995,  # 0.5% below failure point
                        take_profit=data['High'].iloc[idx-self.config.swing_length:idx].max(),
                        confidence=self._calculate_failure_strength(data, idx, False),
                        metadata={
                            'prev_low': prev_low,
                            'failure_low': current_low,
                            'retracement': retracement,
                            'volume_increase': data['Volume'].iloc[idx] / avg_volume
                        }
                    )
        return None

    def _calculate_failure_strength(self, data: pd.DataFrame, idx: int, is_high: bool) -> float:
        """Calculate the strength of the swing failure"""
        if is_high:
            price_range = abs(data['High'].iloc[idx] - data['High'].iloc[idx-self.config.swing_length:idx].max())
            base_price = data['High'].iloc[idx-self.config.swing_length:idx].max()
        else:
            price_range = abs(data['Low'].iloc[idx] - data['Low'].iloc[idx-self.config.swing_length:idx].min())
            base_price = data['Low'].iloc[idx-self.config.swing_length:idx].min()
            
        relative_move = price_range / base_price
        volume_factor = data['Volume'].iloc[idx] / data['Volume'].iloc[idx-self.config.confirmation_candles:idx].mean()
        
        # Include retracement in strength calculation
        retracement_factor = relative_move / self.config.min_swing_size
        volume_factor = volume_factor / self.config.volume_increase_factor
        
        return min(1.0, (retracement_factor * 0.7) + (volume_factor * 0.3))

    def get_required_columns(self) -> List[str]:
        return ['Open', 'High', 'Low', 'Close', 'Volume', 'timestamp']