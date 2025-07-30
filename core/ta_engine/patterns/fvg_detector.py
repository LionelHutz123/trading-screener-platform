from dataclasses import dataclass
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np
from .base_detector import DetectionStrategy, DetectionResult

@dataclass
class FVGConfig:
    """Configuration for Fair Value Gap detection"""
    min_gap_size: float = 0.002  # Minimum gap size as percentage
    max_gap_size: float = 0.02   # Maximum gap size as percentage
    volume_threshold: float = 1.2  # Required volume increase
    trend_bars: int = 5          # Bars to confirm trend
    max_mitigation_bars: int = 50  # Maximum bars to track mitigation
    min_confidence: float = 0.5   # Minimum confidence threshold

class FVGDetector(DetectionStrategy):
    """Detects Fair Value Gap patterns"""
    
    def __init__(self, config: FVGConfig = None):
        self.config = config or FVGConfig()
    
    def detect(self, data: pd.DataFrame) -> List[DetectionResult]:
        """Detect fair value gaps in the data"""
        data = data.copy()
        
        # Find gaps
        results = []
        for i in range(1, len(data)-1):
            # Check for bullish FVG
            bull_fvg = self._check_bullish_fvg(data, i)
            if bull_fvg:
                results.append(bull_fvg)
                
            # Check for bearish FVG
            bear_fvg = self._check_bearish_fvg(data, i)
            if bear_fvg:
                results.append(bear_fvg)
                
        return results
    
    def _check_bullish_fvg(self, data: pd.DataFrame, idx: int) -> Optional[DetectionResult]:
        """Check for bullish fair value gap"""
        try:
            # Previous high should be lower than next low
            if data['High'].iloc[idx-1] >= data['Low'].iloc[idx+1]:
                return None
                
            # Current candle should be bullish
            if data['Close'].iloc[idx] <= data['Open'].iloc[idx]:
                return None
                
            # Calculate gap size
            gap_bottom = data['High'].iloc[idx-1]
            gap_top = data['Low'].iloc[idx+1]
            gap_size = (gap_top - gap_bottom) / gap_bottom
            
            if not (self.config.min_gap_size <= gap_size <= self.config.max_gap_size):
                return None
                
            # Volume confirmation
            volume_ratio = (data['Volume'].iloc[idx] / 
                          data['Volume'].iloc[idx-5:idx].mean())
            
            if volume_ratio < self.config.volume_threshold:
                return None
                
            # Calculate confidence
            confidence = self._calculate_confidence(data, idx, True)
            
            if confidence < self.config.min_confidence:
                return None
                
            # Check mitigation
            mitigation_idx = self._find_mitigation(data, idx, gap_top, True)
            
            return DetectionResult(
                pattern_type="BULLISH_FVG",
                timestamp=data.index[idx],
                entry_price=gap_bottom,
                stop_loss=gap_bottom * 0.99,  # 1% below gap
                take_profit=gap_top * 1.01,   # 1% above gap
                confidence=confidence,
                metadata={
                    'gap_size': gap_size,
                    'volume_ratio': volume_ratio,
                    'mitigation_index': mitigation_idx,
                    'gap_top': gap_top,
                    'gap_bottom': gap_bottom
                }
            )
            
        except Exception as e:
            print(f"Error checking bullish FVG: {str(e)}")
            return None
            
    def _check_bearish_fvg(self, data: pd.DataFrame, idx: int) -> Optional[DetectionResult]:
        """Check for bearish fair value gap"""
        try:
            # Previous low should be higher than next high
            if data['Low'].iloc[idx-1] <= data['High'].iloc[idx+1]:
                return None
                
            # Current candle should be bearish
            if data['Close'].iloc[idx] >= data['Open'].iloc[idx]:
                return None
                
            # Calculate gap size
            gap_top = data['Low'].iloc[idx-1]
            gap_bottom = data['High'].iloc[idx+1]
            gap_size = (gap_top - gap_bottom) / gap_top
            
            if not (self.config.min_gap_size <= gap_size <= self.config.max_gap_size):
                return None
                
            # Volume confirmation
            volume_ratio = (data['Volume'].iloc[idx] / 
                          data['Volume'].iloc[idx-5:idx].mean())
            
            if volume_ratio < self.config.volume_threshold:
                return None
                
            # Calculate confidence
            confidence = self._calculate_confidence(data, idx, False)
            
            if confidence < self.config.min_confidence:
                return None
                
            # Check mitigation
            mitigation_idx = self._find_mitigation(data, idx, gap_bottom, False)
            
            return DetectionResult(
                pattern_type="BEARISH_FVG",
                timestamp=data.index[idx],
                entry_price=gap_top,
                stop_loss=gap_top * 1.01,    # 1% above gap
                take_profit=gap_bottom * 0.99,  # 1% below gap
                confidence=confidence,
                metadata={
                    'gap_size': gap_size,
                    'volume_ratio': volume_ratio,
                    'mitigation_index': mitigation_idx,
                    'gap_top': gap_top,
                    'gap_bottom': gap_bottom
                }
            )
            
        except Exception as e:
            print(f"Error checking bearish FVG: {str(e)}")
            return None
            
    def _find_mitigation(self, data: pd.DataFrame, start_idx: int, 
                        level: float, is_bullish: bool) -> Optional[int]:
        """Find when the gap is mitigated"""
        try:
            for i in range(start_idx + 2, 
                         min(len(data), start_idx + self.config.max_mitigation_bars)):
                if is_bullish and data['Low'].iloc[i] <= level:
                    return i
                elif not is_bullish and data['High'].iloc[i] >= level:
                    return i
            return None
            
        except Exception as e:
            print(f"Error finding mitigation: {str(e)}")
            return None
            
    def _calculate_confidence(self, data: pd.DataFrame, idx: int, is_bullish: bool) -> float:
        """Calculate confidence score for fair value gap"""
        try:
            # Gap quality (0-0.4)
            if is_bullish:
                gap_size = (data['Low'].iloc[idx+1] - data['High'].iloc[idx-1]) / data['High'].iloc[idx-1]
            else:
                gap_size = (data['Low'].iloc[idx-1] - data['High'].iloc[idx+1]) / data['Low'].iloc[idx-1]
            size_score = 0.4 * min(gap_size / self.config.min_gap_size, 1.0) if not pd.isna(gap_size) else 0.2
            
            # Volume quality (0-0.3)
            volume_ratio = (data['Volume'].iloc[idx] / 
                          data['Volume'].iloc[idx-5:idx].mean())
            volume_score = 0.3 * min(volume_ratio / self.config.volume_threshold, 1.0) if not pd.isna(volume_ratio) else 0.15
            
            # Trend quality (0-0.3)
            window = data.iloc[idx-self.config.trend_bars:idx+1]
            if is_bullish:
                up_moves = sum(1 for i in range(len(window)-1) 
                             if window['Close'].iloc[i] < window['Close'].iloc[i+1])
                trend_score = 0.3 * (up_moves / (len(window)-1))
            else:
                down_moves = sum(1 for i in range(len(window)-1) 
                               if window['Close'].iloc[i] > window['Close'].iloc[i+1])
                trend_score = 0.3 * (down_moves / (len(window)-1))
            
            return min(size_score + volume_score + trend_score, 1.0)
            
        except Exception as e:
            print(f"Error calculating confidence: {str(e)}")
            return 0.5  # Return neutral confidence on error 