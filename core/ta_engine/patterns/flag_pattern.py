from dataclasses import dataclass
import numpy as np
import pandas as pd
import vectorbt as vbt
from scipy.stats import linregress
from typing import List, Optional, Dict, Any
from .base_detector import DetectionStrategy, DetectionResult
from datetime import datetime

@dataclass
class FlagConfig:
    """Configuration for flag pattern detection"""
    min_pole_height: float = 0.005  # 0.5% minimum flag pole
    min_flag_bars: int = 3
    max_flag_bars: int = 20
    max_flag_width_ratio: float = 3.0  # Flag width should be less than 3x pole width
    max_flag_height_ratio: float = 0.75  # Flag height should be less than 75% pole height
    volume_decline: float = 0.0  # Volume requirement disabled by default
    min_confidence: float = 0.3

class FlagPatternDetector(DetectionStrategy):
    """Detects flag patterns in price data"""
    
    def __init__(self, config: FlagConfig):
        self.config = config
        self.pole_fails = 0
        self.flag_fails = 0
        self.patterns_found = 0
        
    def detect(self, data: pd.DataFrame) -> List[DetectionResult]:
        """Detect flag patterns in the entire dataset"""
        results = []
        
        # Convert DataFrame to numpy arrays for processing
        high = data['High'].values
        low = data['Low'].values
        close = data['Close'].values
        volume = data['Volume'].values
        timestamps = data.index
        
        # Process each point in the dataset
        for i in range(self.config.min_flag_bars, len(data)):
            # Check for bullish flag
            pattern = self._check_bullish_flag(high, low, close, volume, i, timestamps[i])
            if pattern:
                self.patterns_found += 1
                results.append(pattern)
                
            # Check for bearish flag
            pattern = self._check_bearish_flag(high, low, close, volume, i, timestamps[i])
            if pattern:
                self.patterns_found += 1
                results.append(pattern)
        
        return results

    def _is_significant_low(self, low: np.ndarray, index: int, window: int) -> bool:
        """Check if point is a significant low (lower than most surrounding points)"""
        if index < window:
            return False
        window_lows = low[max(0, index-window):index+1]
        current_low = low[index]
        return current_low <= np.percentile(window_lows, 20)  # In lowest 20% of points

    def _is_significant_high(self, high: np.ndarray, index: int, window: int) -> bool:
        """Check if point is a significant high (higher than most surrounding points)"""
        if index < window:
            return False
        window_highs = high[max(0, index-window):index+1]
        current_high = high[index]
        return current_high >= np.percentile(window_highs, 80)  # In highest 20% of points

    def _check_bullish_flag(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, index: int, timestamp: datetime) -> Optional[DetectionResult]:
        # Find pole low and high points
        pole_window = min(50, index)  # Increased from 20 to 50
        
        # Find significant lows/highs in the pole window
        significant_lows = [i for i in range(index-pole_window, index) 
                          if self._is_significant_low(low, i, 5)]
        significant_highs = [i for i in range(index-pole_window, index)
                           if self._is_significant_high(high, i, 5)]
        
        if not significant_lows or not significant_highs:
            self.pole_fails += 1
            return None
            
        # Find best pole formation
        best_pole_height = 0
        best_pole_low_idx = None
        best_pole_high_idx = None
        
        for low_idx in significant_lows:
            for high_idx in significant_highs:
                if high_idx > low_idx:  # Valid pole formation
                    pole_height = (high[high_idx] - low[low_idx]) / low[low_idx]
                    if pole_height > best_pole_height:
                        best_pole_height = pole_height
                        best_pole_low_idx = low_idx
                        best_pole_high_idx = high_idx
        
        if best_pole_height < self.config.min_pole_height:
            self.pole_fails += 1
            return None
            
        # Calculate flag metrics
        flag_high = np.max(high[best_pole_high_idx:index+1])
        flag_low = np.min(low[best_pole_high_idx:index+1])
        flag_height = (flag_high - flag_low) / flag_low
        flag_width = index - best_pole_high_idx
        pole_width = best_pole_high_idx - best_pole_low_idx
        
        # Check flag width ratio
        if flag_width / pole_width > self.config.max_flag_width_ratio:
            self.flag_fails += 1
            return None
        
        if flag_width > self.config.max_flag_bars or flag_width < self.config.min_flag_bars:
            self.flag_fails += 1
            return None
            
        if flag_height > best_pole_height * self.config.max_flag_height_ratio:
            self.flag_fails += 1
            return None
            
        # Check volume decline if enabled
        volume_ratio = 1.0
        if self.config.volume_decline > 0:
            pole_volume = np.mean(volume[best_pole_low_idx:best_pole_high_idx+1])
            flag_volume = np.mean(volume[best_pole_high_idx:index+1])
            volume_ratio = flag_volume / pole_volume
            
            if volume_ratio > self.config.volume_decline:
                self.flag_fails += 1
                return None
            
        # Calculate confidence
        confidence = self._calculate_confidence(best_pole_height, flag_height/best_pole_height,
                                             flag_width/pole_width,
                                             volume_ratio)
                                             
        if confidence < self.config.min_confidence:
            return None
            
        # Calculate entry, stop and target
        entry = close[index]
        stop = low[best_pole_low_idx]
        target = entry + (entry - stop) * 2
        
        metadata = {
            'pole_height': float(best_pole_height),
            'flag_height': float(flag_height),
            'flag_width': float(flag_width),
            'volume_trend': float(volume_ratio),
            'pole_volume': float(np.mean(volume[best_pole_low_idx:best_pole_high_idx+1]))
        }
        
        return DetectionResult(
            pattern_type='BULLISH_FLAG',
            timestamp=timestamp,
            entry_price=float(entry),
            stop_loss=float(stop),
            take_profit=float(target),
            confidence=float(confidence),
            metadata=metadata
        )

    def _check_bearish_flag(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, index: int, timestamp: datetime) -> Optional[DetectionResult]:
        # Find pole high and low points
        pole_window = min(50, index)  # Increased from 20 to 50
        
        # Find significant lows/highs in the pole window
        significant_lows = [i for i in range(index-pole_window, index)
                          if self._is_significant_low(low, i, 5)]
        significant_highs = [i for i in range(index-pole_window, index)
                           if self._is_significant_high(high, i, 5)]
        
        if not significant_lows or not significant_highs:
            self.pole_fails += 1
            return None
            
        # Find best pole formation
        best_pole_height = 0
        best_pole_low_idx = None
        best_pole_high_idx = None
        
        for high_idx in significant_highs:
            for low_idx in significant_lows:
                if low_idx > high_idx:  # Valid pole formation
                    pole_height = (high[high_idx] - low[low_idx]) / low[low_idx]
                    if pole_height > best_pole_height:
                        best_pole_height = pole_height
                        best_pole_low_idx = low_idx
                        best_pole_high_idx = high_idx
        
        if best_pole_height < self.config.min_pole_height:
            self.pole_fails += 1
            return None
            
        # Calculate flag metrics
        flag_high = np.max(high[best_pole_low_idx:index+1])
        flag_low = np.min(low[best_pole_low_idx:index+1])
        flag_height = (flag_high - flag_low) / flag_low
        flag_width = index - best_pole_low_idx
        pole_width = best_pole_low_idx - best_pole_high_idx
        
        # Check flag width ratio
        if flag_width / pole_width > self.config.max_flag_width_ratio:
            self.flag_fails += 1
            return None
        
        if flag_width > self.config.max_flag_bars or flag_width < self.config.min_flag_bars:
            self.flag_fails += 1
            return None
            
        if flag_height > best_pole_height * self.config.max_flag_height_ratio:
            self.flag_fails += 1
            return None
            
        # Check volume decline if enabled
        volume_ratio = 1.0
        if self.config.volume_decline > 0:
            pole_volume = np.mean(volume[best_pole_high_idx:best_pole_low_idx+1])
            flag_volume = np.mean(volume[best_pole_low_idx:index+1])
            volume_ratio = flag_volume / pole_volume
            
            if volume_ratio > self.config.volume_decline:
                self.flag_fails += 1
                return None
            
        # Calculate confidence
        confidence = self._calculate_confidence(best_pole_height, flag_height/best_pole_height,
                                             flag_width/pole_width,
                                             volume_ratio)
                                             
        if confidence < self.config.min_confidence:
            return None
            
        # Calculate entry, stop and target
        entry = close[index]
        stop = high[best_pole_high_idx]
        target = entry - (stop - entry) * 2
        
        metadata = {
            'pole_height': float(best_pole_height),
            'flag_height': float(flag_height),
            'flag_width': float(flag_width),
            'volume_trend': float(volume_ratio),
            'pole_volume': float(np.mean(volume[best_pole_high_idx:best_pole_low_idx+1]))
        }
        
        return DetectionResult(
            pattern_type='BEARISH_FLAG',
            timestamp=timestamp,
            entry_price=float(entry),
            stop_loss=float(stop),
            take_profit=float(target),
            confidence=float(confidence),
            metadata=metadata
        )

    def _calculate_confidence(self, pole_height: float, height_ratio: float, 
                            width_ratio: float, volume_ratio: float) -> float:
        # Pole quality (0-0.4)
        pole_score = min(0.4, pole_height / 0.05)
        
        # Flag quality (0-0.4)
        height_score = 0.4 * (1 - height_ratio)
        width_score = 0.4 * (1 - width_ratio)
        flag_score = min(0.4, (height_score + width_score) / 2)
        
        # Volume quality (0-0.2)
        volume_score = 0.2 if self.config.volume_decline == 0 else 0.2 * (1 - volume_ratio)
        
        return pole_score + flag_score + volume_score

    def get_required_columns(self) -> List[str]:
        """Get required columns for detection"""
        return ['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']