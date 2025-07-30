from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from typing import List
from ..patterns.detection_strategy import DetectionStrategy, DetectionResult

@dataclass
class FVGConfig:
    min_gap_size: float = 0.001    # 0.1% minimum gap size
    lookback_window: int = 3       # Bars to look back for trend
    trend_threshold: float = 0.002  # 0.2% minimum trend strength
    volume_weight: float = 0.4     # Weight of volume in strength calculation
    min_candle_size: float = 0.001 # 0.1% minimum candle size

class FVGDetector(DetectionStrategy):
    """Detects Fair Value Gaps using price imbalance analysis"""
    
    def __init__(self, config: FVGConfig = FVGConfig()):
        self.config = config
        
    def detect(self, data: pd.DataFrame) -> List[DetectionResult]:
        """Identify FVGs based on price imbalances and market structure"""
        results = []
        data = data.copy().reset_index()
        
        # Calculate candle sizes and trends
        data['candle_size'] = abs(data['Close'] - data['Open']) / data['Open']
        data['body_size'] = data['Close'] - data['Open']
        data['is_bullish'] = data['Close'] > data['Open']
        
        for i in range(2, len(data)):
            window = data.iloc[i-2:i+1]
            
            # Check for bullish FVG (gap up)
            if (window['Low'].iloc[-1] > window['High'].iloc[0] and  # Price gap exists
                window['candle_size'].iloc[-1] >= self.config.min_candle_size):  # Significant candle
                
                gap_size = (window['Low'].iloc[-1] - window['High'].iloc[0]) / window['High'].iloc[0]
                
                # Only consider gaps that are significant relative to recent volatility
                if gap_size >= self.config.min_gap_size:
                    # Check if we have a strong move into the gap
                    trend_strength = self._calculate_trend_strength(data, i, "bullish")
                    if trend_strength >= self.config.trend_threshold:
                        entry = self._calculate_fvg_price_zone(window.iloc[0], window.iloc[-1], "bullish")
                        strength = self._calculate_fvg_strength(window, gap_size, trend_strength)
                        
                        results.append(
                            DetectionResult(
                                pattern_type="BULLISH_FVG",
                                timestamp=data['timestamp'].iloc[i],
                                entry_price=entry,
                                stop_loss=window['Low'].iloc[0],  # Below the gap
                                take_profit=window['High'].iloc[-1] + gap_size * window['High'].iloc[-1],
                                confidence=strength,
                                metadata=self._build_metadata(window, gap_size, "bullish", trend_strength)
                            )
                        )
            
            # Check for bearish FVG (gap down)
            elif (window['High'].iloc[-1] < window['Low'].iloc[0] and  # Price gap exists
                  window['candle_size'].iloc[-1] >= self.config.min_candle_size):  # Significant candle
                
                gap_size = (window['Low'].iloc[0] - window['High'].iloc[-1]) / window['Low'].iloc[0]
                
                # Only consider gaps that are significant relative to recent volatility
                if gap_size >= self.config.min_gap_size:
                    # Check if we have a strong move into the gap
                    trend_strength = self._calculate_trend_strength(data, i, "bearish")
                    if trend_strength >= self.config.trend_threshold:
                        entry = self._calculate_fvg_price_zone(window.iloc[0], window.iloc[-1], "bearish")
                        strength = self._calculate_fvg_strength(window, gap_size, trend_strength)
                        
                        results.append(
                            DetectionResult(
                                pattern_type="BEARISH_FVG",
                                timestamp=data['timestamp'].iloc[i],
                                entry_price=entry,
                                stop_loss=window['High'].iloc[0],  # Above the gap
                                take_profit=window['Low'].iloc[-1] - gap_size * window['Low'].iloc[-1],
                                confidence=strength,
                                metadata=self._build_metadata(window, gap_size, "bearish", trend_strength)
                            )
                        )
        
        return results

    def _calculate_trend_strength(self, data: pd.DataFrame, current_idx: int, direction: str) -> float:
        """Calculate the strength of the trend leading into the FVG"""
        window = data.iloc[max(0, current_idx-self.config.lookback_window):current_idx+1]
        
        if direction == "bullish":
            # Count consecutive higher lows
            higher_lows = sum(1 for i in range(1, len(window)) 
                            if window['Low'].iloc[i] > window['Low'].iloc[i-1])
            # Measure momentum
            price_change = (window['Close'].iloc[-1] - window['Close'].iloc[0]) / window['Close'].iloc[0]
            return (higher_lows / len(window) + max(0, price_change)) / 2
            
        else:  # bearish
            # Count consecutive lower highs
            lower_highs = sum(1 for i in range(1, len(window))
                            if window['High'].iloc[i] < window['High'].iloc[i-1])
            # Measure momentum
            price_change = (window['Close'].iloc[0] - window['Close'].iloc[-1]) / window['Close'].iloc[0]
            return (lower_highs / len(window) + max(0, price_change)) / 2

    def _calculate_fvg_strength(self, window: pd.DataFrame, gap_size: float, trend_strength: float) -> float:
        """Calculate FVG strength using gap size, trend and volume"""
        # Volume strength
        avg_volume = window['Volume'].iloc[:-1].mean()
        volume_ratio = window['Volume'].iloc[-1] / avg_volume if avg_volume > 0 else 1.0
        volume_strength = min(1.0, volume_ratio / 2)  # Cap at 1.0
        
        # Gap strength relative to recent volatility
        gap_strength = min(1.0, gap_size / (self.config.min_gap_size * 5))
        
        # Combine components with weights
        return min(0.95, 
                  gap_strength * 0.4 +           # 40% weight on gap size
                  trend_strength * 0.4 +         # 40% weight on trend
                  volume_strength * 0.2)         # 20% weight on volume

    def _calculate_fvg_price_zone(self, c1: pd.Series, c3: pd.Series, direction: str) -> float:
        """Calculate the optimal entry price in the FVG zone"""
        if direction == "bullish":
            gap_bottom = c1['High']  # Top of first candle
            gap_top = c3['Low']      # Bottom of last candle
        else:
            gap_bottom = c3['High']  # Top of last candle
            gap_top = c1['Low']      # Bottom of first candle
            
        # Return price closer to the side where the gap formed
        if direction == "bullish":
            return gap_bottom + (gap_top - gap_bottom) * 0.382  # Lower entry for bullish
        else:
            return gap_bottom + (gap_top - gap_bottom) * 0.618  # Higher entry for bearish

    def _build_metadata(self, window: pd.DataFrame, gap_size: float, direction: str, trend_strength: float) -> dict:
        """Create detailed metadata for the FVG pattern"""
        return {
            'direction': direction,
            'gap_size': gap_size,
            'trend_strength': trend_strength,
            'volume_ratio': window['Volume'].iloc[-1] / window['Volume'].iloc[:-1].mean(),
            'price_movement': abs(window['Close'].iloc[-1] - window['Close'].iloc[0]) / window['Close'].iloc[0],
            'candle_sizes': window['candle_size'].tolist(),
            'is_strong_move': all(abs(c) >= self.config.min_candle_size for c in window['body_size']),
            'candles': {
                'first': window.iloc[0][['Open', 'High', 'Low', 'Close', 'Volume']].to_dict(),
                'middle': window.iloc[1][['Open', 'High', 'Low', 'Close', 'Volume']].to_dict(),
                'last': window.iloc[2][['Open', 'High', 'Low', 'Close', 'Volume']].to_dict()
            }
        }

    def get_required_columns(self) -> List[str]:
        return ['Open', 'High', 'Low', 'Close', 'Volume', 'timestamp']

# Example usage:
# fvg_detector = FVGDetector()
# results = fvg_detector.detect(price_data)