from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np

from .base_detector import DetectionStrategy, DetectionResult
from .swing_detector import SwingConfig

@dataclass
class OBConfig:
    swing_config: SwingConfig = field(default_factory=SwingConfig)
    min_block_size: float = 0.01
    max_block_size: float = 0.05
    volume_threshold: float = 1.2
    min_trend_bars: int = 3
    max_mitigation_bars: int = 20
    min_confidence: float = 0.6

class OrderBlockDetector(DetectionStrategy):
    def __init__(self, config: Optional[OBConfig] = None):
        self.config = config or OBConfig()
        
    def detect(self, data: pd.DataFrame) -> List[DetectionResult]:
        results = []
        
        # Calculate ATR once
        atr = self._calculate_atr(data)
        
        for i in range(len(data)):
            try:
                # Check for bullish order block
                if self._check_bullish_ob(data, i):
                    entry = data['Low'].iloc[i]
                    stop = data['High'].iloc[i]
                    target = entry + (stop - entry) * 2
                    
                    # Validate block size
                    block_size = (stop - entry) / entry
                    if not (self.config.min_block_size <= block_size <= self.config.max_block_size):
                        continue
                    
                    results.append(DetectionResult(
                        pattern_type="BULLISH_OB",
                        timestamp=data.index[i],
                        entry_price=entry,
                        stop_loss=stop,
                        take_profit=target,
                        confidence=self._calculate_confidence(data, i, atr),
                        metadata={
                            "block_size": block_size,
                            "volume_ratio": data['Volume'].iloc[i] / data['Volume'].iloc[i-1],
                            "block_high": data['High'].iloc[i],
                            "block_low": data['Low'].iloc[i]
                        }
                    ))
                    
                # Check for bearish order block
                if self._check_bearish_ob(data, i):
                    entry = data['High'].iloc[i]
                    stop = data['Low'].iloc[i] 
                    target = entry - (entry - stop) * 2
                    
                    # Validate block size
                    block_size = (entry - stop) / entry
                    if not (self.config.min_block_size <= block_size <= self.config.max_block_size):
                        continue
                    
                    results.append(DetectionResult(
                        pattern_type="BEARISH_OB",
                        timestamp=data.index[i],
                        entry_price=entry,
                        stop_loss=stop,
                        take_profit=target,
                        confidence=self._calculate_confidence(data, i, atr),
                        metadata={
                            "block_size": block_size,
                            "volume_ratio": data['Volume'].iloc[i] / data['Volume'].iloc[i-1],
                            "block_high": data['High'].iloc[i],
                            "block_low": data['Low'].iloc[i]
                        }
                    ))
            except Exception as e:
                print(f"Error processing bar {i}: {str(e)}")
                continue
                
        return results
        
    def _check_bullish_ob(self, data: pd.DataFrame, i: int) -> bool:
        try:
            # Check if we have a bullish order block
            # Price must make a higher high after the order block
            if i < 2 or i >= len(data) - 1:
                return False
                
            # Check if current candle is bearish
            if data['Close'].iloc[i] >= data['Open'].iloc[i]:
                return False
                
            # Check if next candle is bullish and breaks above the high
            if data['High'].iloc[i+1] <= data['High'].iloc[i]:
                return False
                
            # Check volume
            if data['Volume'].iloc[i] < data['Volume'].iloc[i-1] * self.config.volume_threshold:
                return False
                
            return True
        except Exception as e:
            print(f"Error checking bullish OB: {str(e)}")
            return False
        
    def _check_bearish_ob(self, data: pd.DataFrame, i: int) -> bool:
        try:
            # Check if we have a bearish order block
            # Price must make a lower low after the order block
            if i < 2 or i >= len(data) - 1:
                return False
                
            # Check if current candle is bullish
            if data['Close'].iloc[i] <= data['Open'].iloc[i]:
                return False
                
            # Check if next candle is bearish and breaks below the low
            if data['Low'].iloc[i+1] >= data['Low'].iloc[i]:
                return False
                
            # Check volume
            if data['Volume'].iloc[i] < data['Volume'].iloc[i-1] * self.config.volume_threshold:
                return False
                
            return True
        except Exception as e:
            print(f"Error checking bearish OB: {str(e)}")
            return False
        
    def _calculate_confidence(self, data: pd.DataFrame, i: int, atr: pd.Series) -> float:
        try:
            # Calculate confidence based on:
            # 1. Block size relative to ATR
            # 2. Volume spike relative to average
            # 3. Follow through after the block
            
            # Block size score
            block_size = abs(data['High'].iloc[i] - data['Low'].iloc[i])
            size_score = min(block_size / atr.iloc[i], 1.0) if not pd.isna(atr.iloc[i]) else 0.5
            
            # Volume score
            vol_ratio = data['Volume'].iloc[i] / data['Volume'].iloc[i-1]
            vol_score = min(vol_ratio / self.config.volume_threshold, 1.0) if not pd.isna(vol_ratio) else 0.5
            
            # Follow through score
            if i < len(data) - 5:
                if data['Close'].iloc[i] > data['Open'].iloc[i]:  # Bullish
                    follow_score = sum(data['Close'].iloc[i+1:i+6] > data['Open'].iloc[i+1:i+6]) / 5
                else:  # Bearish
                    follow_score = sum(data['Close'].iloc[i+1:i+6] < data['Open'].iloc[i+1:i+6]) / 5
            else:
                follow_score = 0.5
                
            return (size_score * 0.4 + vol_score * 0.3 + follow_score * 0.3)
        except Exception as e:
            print(f"Error calculating confidence: {str(e)}")
            return 0.5  # Return neutral confidence on error 