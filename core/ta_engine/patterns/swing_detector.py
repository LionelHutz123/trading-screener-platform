from dataclasses import dataclass
from typing import List, Tuple
import pandas as pd
import numpy as np
from .base_detector import DetectionStrategy, DetectionResult

@dataclass
class SwingConfig:
    """Configuration for swing point detection"""
    window: int = 5  # Window size for swing point detection
    min_strength: float = 0.001  # Minimum swing strength
    trend_strength: float = 0.3  # Required strength for trend confirmation
    volume_factor: float = 1.1  # Volume requirement for swing confirmation
    
class SwingDetector(DetectionStrategy):
    """Detects swing points in price data"""
    
    def __init__(self, config: SwingConfig = None):
        self.config = config or SwingConfig()
    
    def detect(self, data: pd.DataFrame) -> List[DetectionResult]:
        """Detect swing points in the data"""
        data = data.copy()
        
        # Calculate swing points
        highs = self._find_swing_highs(data)
        lows = self._find_swing_lows(data)
        
        # Combine results
        results = []
        for idx in range(len(data)):
            if highs[idx]:
                results.append(self._build_swing_high(data, idx))
            elif lows[idx]:
                results.append(self._build_swing_low(data, idx))
                
        return [r for r in results if r is not None]
    
    def _find_swing_highs(self, data: pd.DataFrame) -> np.ndarray:
        """Find swing high points"""
        highs = np.zeros(len(data), dtype=bool)
        
        for i in range(self.config.window, len(data)-self.config.window):
            window = data.iloc[i-self.config.window:i+self.config.window+1]
            
            # Price conditions
            is_highest = data['High'].iloc[i] == window['High'].max()
            
            # Volume confirmation
            vol_increase = (data['Volume'].iloc[i] > 
                          data['Volume'].iloc[i-self.config.window:i].mean() * 
                          self.config.volume_factor)
            
            # Trend strength
            up_moves = sum(1 for j in range(i-self.config.window, i) 
                         if data['Close'].iloc[j] < data['Close'].iloc[j+1])
            trend_strength = up_moves / self.config.window
            
            if is_highest and vol_increase and trend_strength >= self.config.trend_strength:
                highs[i] = True
                
        return highs
    
    def _find_swing_lows(self, data: pd.DataFrame) -> np.ndarray:
        """Find swing low points"""
        lows = np.zeros(len(data), dtype=bool)
        
        for i in range(self.config.window, len(data)-self.config.window):
            window = data.iloc[i-self.config.window:i+self.config.window+1]
            
            # Price conditions
            is_lowest = data['Low'].iloc[i] == window['Low'].min()
            
            # Volume confirmation
            vol_increase = (data['Volume'].iloc[i] > 
                          data['Volume'].iloc[i-self.config.window:i].mean() * 
                          self.config.volume_factor)
            
            # Trend strength
            down_moves = sum(1 for j in range(i-self.config.window, i) 
                           if data['Close'].iloc[j] > data['Close'].iloc[j+1])
            trend_strength = down_moves / self.config.window
            
            if is_lowest and vol_increase and trend_strength >= self.config.trend_strength:
                lows[i] = True
                
        return lows
    
    def _build_swing_high(self, data: pd.DataFrame, idx: int) -> DetectionResult:
        """Create swing high detection result"""
        try:
            return DetectionResult(
                pattern_type="SWING_HIGH",
                timestamp=data.index[idx],
                entry_price=data['High'].iloc[idx],
                stop_loss=data['Low'].iloc[idx-1:idx+2].min(),
                take_profit=data['High'].iloc[idx] * 1.01,  # 1% above swing high
                confidence=self._calculate_confidence(data, idx, is_high=True),
                metadata={
                    'swing_strength': self._calculate_swing_strength(data).iloc[idx],
                    'volume_ratio': (data['Volume'].iloc[idx] / 
                                   data['Volume'].iloc[idx-self.config.window:idx].mean())
                }
            )
        except Exception as e:
            print(f"Error building swing high: {str(e)}")
            return None
            
    def _build_swing_low(self, data: pd.DataFrame, idx: int) -> DetectionResult:
        """Create swing low detection result"""
        try:
            return DetectionResult(
                pattern_type="SWING_LOW",
                timestamp=data.index[idx],
                entry_price=data['Low'].iloc[idx],
                stop_loss=data['High'].iloc[idx-1:idx+2].max(),
                take_profit=data['Low'].iloc[idx] * 0.99,  # 1% below swing low
                confidence=self._calculate_confidence(data, idx, is_high=False),
                metadata={
                    'swing_strength': self._calculate_swing_strength(data).iloc[idx],
                    'volume_ratio': (data['Volume'].iloc[idx] / 
                                   data['Volume'].iloc[idx-self.config.window:idx].mean())
                }
            )
        except Exception as e:
            print(f"Error building swing low: {str(e)}")
            return None
            
    def _calculate_confidence(self, data: pd.DataFrame, idx: int, is_high: bool) -> float:
        """Calculate confidence score for swing point"""
        try:
            # Price action quality (0-0.4)
            window = data.iloc[idx-self.config.window:idx+self.config.window+1]
            if is_high:
                price_score = 0.4 * (data['High'].iloc[idx] - window['High'].mean()) / window['High'].std()
            else:
                price_score = 0.4 * (window['Low'].mean() - data['Low'].iloc[idx]) / window['Low'].std()
            
            # Volume quality (0-0.3)
            volume_ratio = (data['Volume'].iloc[idx] / 
                          data['Volume'].iloc[idx-self.config.window:idx].mean())
            volume_score = 0.3 * min(volume_ratio / self.config.volume_factor, 1.0)
            
            # Trend quality (0-0.3)
            if is_high:
                up_moves = sum(1 for j in range(idx-self.config.window, idx) 
                             if data['Close'].iloc[j] < data['Close'].iloc[j+1])
                trend_score = 0.3 * (up_moves / self.config.window)
            else:
                down_moves = sum(1 for j in range(idx-self.config.window, idx) 
                               if data['Close'].iloc[j] > data['Close'].iloc[j+1])
                trend_score = 0.3 * (down_moves / self.config.window)
            
            return min(price_score + volume_score + trend_score, 1.0)
            
        except Exception as e:
            print(f"Error calculating confidence: {str(e)}")
            return 0.0 