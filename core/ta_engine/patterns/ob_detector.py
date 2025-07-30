from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np
from .base_detector import DetectionStrategy, DetectionResult
from .swing_detector import SwingDetector, SwingConfig

@dataclass
class OBConfig:
    """Configuration for Order Block detection"""
    swing_config: SwingConfig = field(default_factory=SwingConfig)
    min_block_size: float = 0.002  # Minimum size of order block
    max_block_size: float = 0.02   # Maximum size of order block
    volume_threshold: float = 1.5   # Required volume increase
    min_trend_bars: int = 3        # Minimum bars in trend
    max_mitigation_bars: int = 50  # Maximum bars to track mitigation
    min_confidence: float = 0.5    # Minimum confidence threshold

class OrderBlockDetector(DetectionStrategy):
    """Detects Order Block patterns"""
    
    def __init__(self, config: OBConfig = None):
        self.config = config or OBConfig()
        self.swing_detector = SwingDetector(self.config.swing_config)
    
    def detect(self, data: pd.DataFrame) -> List[DetectionResult]:
        """Detect order blocks in the data"""
        data = data.copy()
        
        # Get swing points for trend context
        swing_points = self.swing_detector.detect(data)
        
        # Find order blocks
        results = []
        for i in range(self.config.min_trend_bars, len(data)-1):
            # Check for bullish OB
            bull_ob = self._check_bullish_ob(data, i)
            if bull_ob:
                results.append(bull_ob)
                
            # Check for bearish OB
            bear_ob = self._check_bearish_ob(data, i)
            if bear_ob:
                results.append(bear_ob)
                
        return results
    
    def _check_bullish_ob(self, data: pd.DataFrame, idx: int) -> Optional[DetectionResult]:
        """Check for bullish order block"""
        try:
            # Need a strong move up after the block
            future_high = data['high'].iloc[idx+1:idx+self.config.min_trend_bars+1].max()
            future_low = data['low'].iloc[idx+1:idx+self.config.min_trend_bars+1].min()
            move_size = (future_high - future_low) / future_low
            
            if move_size < self.config.min_block_size:
                return None
                
            # Block characteristics
            block_high = data['high'].iloc[idx]
            block_low = data['low'].iloc[idx]
            block_size = (block_high - block_low) / block_low
            
            if not (self.config.min_block_size <= block_size <= self.config.max_block_size):
                return None
                
            # Volume confirmation
            volume_ratio = (data['volume'].iloc[idx] / 
                          data['volume'].iloc[idx-5:idx].mean())
            
            if volume_ratio < self.config.volume_threshold:
                return None
                
            # Calculate confidence
            confidence = self._calculate_confidence(data, idx, True)
            
            if confidence < self.config.min_confidence:
                return None
                
            # Check mitigation
            mitigation_idx = self._find_mitigation(data, idx, block_low, True)
            
            return DetectionResult(
                pattern_type="BULLISH_OB",
                timestamp=data.index[idx],
                entry_price=block_low,
                stop_loss=block_low * 0.99,  # 1% below block
                take_profit=future_high,
                confidence=confidence,
                metadata={
                    'block_size': block_size,
                    'volume_ratio': volume_ratio,
                    'move_size': move_size,
                    'mitigation_index': mitigation_idx,
                    'block_high': block_high,
                    'block_low': block_low
                }
            )
            
        except Exception as e:
            print(f"Error checking bullish OB: {str(e)}")
            return None
            
    def _check_bearish_ob(self, data: pd.DataFrame, idx: int) -> Optional[DetectionResult]:
        """Check for bearish order block"""
        try:
            # Need a strong move down after the block
            future_high = data['high'].iloc[idx+1:idx+self.config.min_trend_bars+1].max()
            future_low = data['low'].iloc[idx+1:idx+self.config.min_trend_bars+1].min()
            move_size = (future_high - future_low) / future_high
            
            if move_size < self.config.min_block_size:
                return None
                
            # Block characteristics
            block_high = data['high'].iloc[idx]
            block_low = data['low'].iloc[idx]
            block_size = (block_high - block_low) / block_high
            
            if not (self.config.min_block_size <= block_size <= self.config.max_block_size):
                return None
                
            # Volume confirmation
            volume_ratio = (data['volume'].iloc[idx] / 
                          data['volume'].iloc[idx-5:idx].mean())
            
            if volume_ratio < self.config.volume_threshold:
                return None
                
            # Calculate confidence
            confidence = self._calculate_confidence(data, idx, False)
            
            if confidence < self.config.min_confidence:
                return None
                
            # Check mitigation
            mitigation_idx = self._find_mitigation(data, idx, block_high, False)
            
            return DetectionResult(
                pattern_type="BEARISH_OB",
                timestamp=data.index[idx],
                entry_price=block_high,
                stop_loss=block_high * 1.01,  # 1% above block
                take_profit=future_low,
                confidence=confidence,
                metadata={
                    'block_size': block_size,
                    'volume_ratio': volume_ratio,
                    'move_size': move_size,
                    'mitigation_index': mitigation_idx,
                    'block_high': block_high,
                    'block_low': block_low
                }
            )
            
        except Exception as e:
            print(f"Error checking bearish OB: {str(e)}")
            return None
            
    def _find_mitigation(self, data: pd.DataFrame, start_idx: int, 
                        level: float, is_bullish: bool) -> Optional[int]:
        """Find when the order block is mitigated"""
        try:
            for i in range(start_idx + 1, 
                         min(len(data), start_idx + self.config.max_mitigation_bars)):
                if is_bullish and data['low'].iloc[i] <= level:
                    return i
                elif not is_bullish and data['high'].iloc[i] >= level:
                    return i
            return None
            
        except Exception as e:
            print(f"Error finding mitigation: {str(e)}")
            return None
            
    def _calculate_confidence(self, data: pd.DataFrame, idx: int, is_bullish: bool) -> float:
        """Calculate confidence score for order block"""
        try:
            # Block quality (0-0.4)
            block_high = data['high'].iloc[idx]
            block_low = data['low'].iloc[idx]
            block_size = (block_high - block_low) / (block_high if is_bullish else block_low)
            size_score = 0.4 * min(block_size / self.config.min_block_size, 1.0)
            
            # Volume quality (0-0.3)
            volume_ratio = (data['volume'].iloc[idx] / 
                          data['volume'].iloc[idx-5:idx].mean())
            volume_score = 0.3 * min(volume_ratio / self.config.volume_threshold, 1.0)
            
            # Momentum quality (0-0.3)
            returns = np.log(data['close'].iloc[idx] / data['close'].iloc[idx-1])
            momentum = data['close'].iloc[idx-5:idx].pct_change().mean()
            momentum_aligned = (momentum > 0) != is_bullish  # Opposite momentum for reversal
            momentum_score = 0.3 * (1.5 if momentum_aligned else 0.5) * abs(returns)
            
            return min(size_score + volume_score + momentum_score, 1.0)
            
        except Exception as e:
            print(f"Error calculating confidence: {str(e)}")
            return 0.0 