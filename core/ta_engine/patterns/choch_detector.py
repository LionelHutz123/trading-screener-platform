from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np
from .base_detector import DetectionStrategy, DetectionResult
from .swing_detector import SwingDetector, SwingConfig

@dataclass
class CHoCHConfig:
    """Configuration for Change of Character detection"""
    swing_config: SwingConfig = field(default_factory=SwingConfig)
    min_pattern_bars: int = 4  # Minimum bars between swing points
    max_pattern_bars: int = 20  # Maximum bars between swing points
    min_retracement: float = 0.382  # Minimum retracement level
    max_retracement: float = 0.786  # Maximum retracement level
    volume_factor: float = 1.1  # Required volume increase for confirmation
    min_trend_strength: float = 0.3  # Minimum trend strength for confirmation

class CHoCHDetector(DetectionStrategy):
    """Detects Change of Character patterns"""
    
    def __init__(self, config: CHoCHConfig = None):
        self.config = config or CHoCHConfig()
        self.swing_detector = SwingDetector(self.config.swing_config)
    
    def detect(self, data: pd.DataFrame) -> List[DetectionResult]:
        """Detect CHoCH patterns in the data"""
        data = data.copy()
        
        # Get swing points
        swing_points = self.swing_detector.detect(data)
        if not swing_points:
            return []
            
        # Find CHoCH patterns
        results = []
        for i in range(3, len(swing_points)):
            pattern = self._check_choch_pattern(data, swing_points[i-3:i+1])
            if pattern:
                results.append(pattern)
                
        return results
    
    def _check_choch_pattern(self, data: pd.DataFrame, 
                            swings: List[DetectionResult]) -> Optional[DetectionResult]:
        """Check if four swing points form a valid CHoCH pattern"""
        try:
            # Need 4 swing points
            if len(swings) != 4:
                return None
                
            # Get timestamps and prices
            times = [s.timestamp for s in swings]
            prices = [s.entry_price for s in swings]
            types = [s.pattern_type for s in swings]
            
            # Check sequence (HLHL for bullish, LHLH for bearish)
            is_bullish = (types == ["SWING_HIGH", "SWING_LOW", "SWING_HIGH", "SWING_LOW"])
            is_bearish = (types == ["SWING_LOW", "SWING_HIGH", "SWING_LOW", "SWING_HIGH"])
            
            if not (is_bullish or is_bearish):
                return None
                
            # Check price relationships
            if is_bullish:
                # Bullish CHoCH: HH and HL pattern
                if not (prices[2] > prices[0] and prices[3] > prices[1]):
                    return None
            else:
                # Bearish CHoCH: LL and LH pattern
                if not (prices[2] < prices[0] and prices[3] < prices[1]):
                    return None
                    
            # Check pattern size
            pattern_bars = (times[-1] - times[0]).days
            if not (self.config.min_pattern_bars <= pattern_bars <= self.config.max_pattern_bars):
                return None
                
            # Calculate retracement
            if is_bullish:
                retracement = (prices[2] - prices[3]) / (prices[2] - prices[1])
            else:
                retracement = (prices[3] - prices[2]) / (prices[0] - prices[2])
                
            if not (self.config.min_retracement <= retracement <= self.config.max_retracement):
                return None
                
            # Check volume
            idx = data.index.get_loc(times[-1])
            volume_ratio = (data['Volume'].iloc[idx] / 
                          data['Volume'].iloc[idx-5:idx].mean())
            
            if volume_ratio < self.config.volume_factor:
                return None
                
            # Calculate confidence
            confidence = self._calculate_confidence(data, idx, swings, is_bullish)
            
            # Build result
            return DetectionResult(
                pattern_type="BULLISH_CHOCH" if is_bullish else "BEARISH_CHOCH",
                timestamp=times[-1],
                entry_price=prices[-1],
                stop_loss=min(prices) if is_bullish else max(prices),
                take_profit=self._calculate_target(prices, is_bullish),
                confidence=confidence,
                metadata={
                    'retracement': retracement,
                    'volume_ratio': volume_ratio,
                    'pattern_bars': pattern_bars,
                    'swing_points': [s.timestamp for s in swings]
                }
            )
            
        except Exception as e:
            print(f"Error checking CHoCH pattern: {str(e)}")
            return None
            
    def _calculate_confidence(self, data: pd.DataFrame, idx: int,
                            swings: List[DetectionResult],
                            is_bullish: bool) -> float:
        """Calculate confidence score for CHoCH pattern"""
        try:
            # Pattern quality (0-0.4)
            times = [s.timestamp for s in swings]
            pattern_bars = (times[-1] - times[0]).days
            pattern_score = 0.4 * (1 - (pattern_bars - self.config.min_pattern_bars) / 
                                 (self.config.max_pattern_bars - self.config.min_pattern_bars))
            
            # Retracement quality (0-0.3)
            prices = [s.entry_price for s in swings]
            if is_bullish:
                retracement = (prices[2] - prices[3]) / (prices[2] - prices[1])
            else:
                retracement = (prices[3] - prices[2]) / (prices[0] - prices[2])
            retracement_score = 0.3 * (1 - abs(retracement - 0.618) / 0.236)
            
            # Momentum quality (0-0.3)
            window = data.iloc[idx-20:idx+1]
            if is_bullish:
                up_moves = sum(1 for i in range(len(window)-1) 
                             if window['Close'].iloc[i] < window['Close'].iloc[i+1])
                momentum_score = 0.3 * (up_moves / (len(window)-1))
            else:
                down_moves = sum(1 for i in range(len(window)-1) 
                               if window['Close'].iloc[i] > window['Close'].iloc[i+1])
                momentum_score = 0.3 * (down_moves / (len(window)-1))
            
            return min(pattern_score + retracement_score + momentum_score, 1.0)
            
        except Exception as e:
            print(f"Error calculating confidence: {str(e)}")
            return 0.0
            
    def _calculate_target(self, prices: List[float], is_bullish: bool) -> float:
        """Calculate take profit target based on pattern size"""
        try:
            pattern_height = abs(prices[2] - prices[1])  # Height of the main move
            if is_bullish:
                return prices[-1] + pattern_height
            else:
                return prices[-1] - pattern_height
        except Exception as e:
            print(f"Error calculating target: {str(e)}")
            return prices[-1]  # Return entry price as fallback

    def get_required_columns(self) -> List[str]:
        """Get required columns for detection"""
        return ['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']