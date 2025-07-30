from dataclasses import dataclass
from typing import Dict, Optional, Any
import numpy as np
from .detection_strategy import DetectionResult

@dataclass
class OrderBlockConfig:
    """Configuration for Order Block detection"""
    min_imbalance: float = 0.02      # Minimum price imbalance (2%)
    max_age_bars: int = 20           # Maximum age of order block in bars
    min_volume_ratio: float = 1.5    # Minimum volume compared to average
    min_candle_size: float = 0.01    # Minimum candle size (1%)
    max_candle_size: float = 0.05    # Maximum candle size (5%)
    lookback_period: int = 10        # Period for calculating average volume
    min_confidence: float = 0.5      # Minimum confidence threshold

class OrderBlockDetector:
    """Detector for Order Block patterns"""
    
    def __init__(self, config: OrderBlockConfig):
        self.config = config
    
    def _calculate_average_volume(self, volumes: np.ndarray, current_idx: int) -> float:
        """Calculate average volume over lookback period"""
        start_idx = max(0, current_idx - self.config.lookback_period)
        return np.mean(volumes[start_idx:current_idx])
    
    def _is_valid_candle_size(self, open_price: float, high: float, low: float, close: float) -> bool:
        """Check if candle size is within valid range"""
        candle_body = abs(close - open_price)
        candle_range = high - low
        avg_price = (high + low) / 2
        
        body_ratio = candle_body / avg_price
        range_ratio = candle_range / avg_price
        
        return (self.config.min_candle_size <= body_ratio and 
                self.config.min_candle_size <= range_ratio <= self.config.max_candle_size)
    
    def _calculate_confidence(self, 
                            volume_ratio: float,
                            imbalance_ratio: float,
                            age_ratio: float) -> float:
        """Calculate confidence score based on multiple factors"""
        # Normalize ratios
        vol_score = min(volume_ratio / 2.0, 1.0)  # Cap at 2x average
        imb_score = min(imbalance_ratio / 0.05, 1.0)  # Cap at 5%
        age_score = 1.0 - age_ratio  # Newer blocks get higher score
        
        # Weight the factors
        confidence = (vol_score * 0.4 +    # Volume importance
                     imb_score * 0.4 +     # Imbalance importance
                     age_score * 0.2)      # Age importance
        
        return confidence
    
    def detect(self, data: Dict[str, np.ndarray], current_idx: int) -> Optional[DetectionResult]:
        """
        Detect Order Block patterns at the current index.
        
        Order Blocks are areas of significant trading activity where large players 
        enter positions, often leading to price imbalances and trend changes.
        """
        if current_idx < 2:  # Need at least 2 bars of history
            return None
            
        high = data['high']
        low = data['low']
        close = data['close']
        open_price = data['open']
        volume = data['volume']
        timestamp = data['timestamp']
        
        # Check reversal candle size
        if not self._is_valid_candle_size(
            open_price[current_idx-1], 
            high[current_idx-1], 
            low[current_idx-1], 
            close[current_idx-1]
        ):
            return None
        
        # Calculate volume ratio for reversal candle
        avg_volume = self._calculate_average_volume(volume, current_idx-1)
        volume_ratio = volume[current_idx-1] / avg_volume if avg_volume > 0 else 0
        
        if volume_ratio < self.config.min_volume_ratio:
            return None
            
        # Look for bullish order block (strong bearish candle followed by reversal)
        bullish_ob = (
            close[current_idx-1] < open_price[current_idx-1] and  # Bearish candle
            close[current_idx] > open_price[current_idx] and      # Bullish reversal
            high[current_idx] > high[current_idx-1] and          # Price moves above OB
            (high[current_idx] - low[current_idx-1]) / low[current_idx-1] > self.config.min_imbalance  # Imbalance
        )
        
        # Look for bearish order block (strong bullish candle followed by reversal)
        bearish_ob = (
            close[current_idx-1] > open_price[current_idx-1] and  # Bullish candle
            close[current_idx] < open_price[current_idx] and      # Bearish reversal
            low[current_idx] < low[current_idx-1] and           # Price moves below OB
            (high[current_idx-1] - low[current_idx]) / low[current_idx] > self.config.min_imbalance  # Imbalance
        )
        
        if not (bullish_ob or bearish_ob):
            return None
            
        # Calculate confidence based on reversal candle
        candle_range = high[current_idx-1] - low[current_idx-1]
        avg_price = (high[current_idx-1] + low[current_idx-1]) / 2
        imbalance_ratio = candle_range / avg_price
        age_ratio = 0  # Current bar, so age is 0
        confidence = self._calculate_confidence(volume_ratio, imbalance_ratio, age_ratio)
        
        if confidence < self.config.min_confidence:
            return None
            
        # Create detection result
        pattern_type = "BULLISH_ORDER_BLOCK" if bullish_ob else "BEARISH_ORDER_BLOCK"
        
        metadata = {
            'volume_ratio': volume_ratio,
            'imbalance_ratio': imbalance_ratio,
            'confidence': confidence,
            'entry_price': close[current_idx],
            'stop_loss': low[current_idx-1] if bullish_ob else high[current_idx-1],
            'ob_high': high[current_idx-1],
            'ob_low': low[current_idx-1]
        }
        
        return DetectionResult(
            pattern_type=pattern_type,
            timestamp=timestamp[current_idx],
            confidence=confidence,
            metadata=metadata
        ) 