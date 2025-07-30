from dataclasses import dataclass
import pandas as pd
from typing import List
from core.ta_engine.patterns.detection_strategy import DetectionStrategy, DetectionResult
from core.ta_engine.utils.validation import validate_dataframe
from core.ta_engine.utils.ta_helpers import PivotDetector, PivotConfig

@dataclass
class OrderBlockConfig:
    window_size: int = 20
    n_pips: int = 5
    min_strength: float = 0.5

class OrderBlockDetector(DetectionStrategy):
    """Detects order blocks using price action patterns"""
    
    def __init__(self, config: OrderBlockConfig):
        self.config = config
        
    def detect(self, data: pd.DataFrame) -> List[DetectionResult]:
        """Detects order blocks based on price action patterns"""
        results = []
        data = data.copy().reset_index()
        
        # Calculate price derivatives
        data['prev_high'] = data['High'].shift(1)
        data['prev_low'] = data['Low'].shift(1)
        data['price_derivative'] = data['Close'].diff()

        # Detect potential order blocks
        for i in range(1, len(data)):
            current = data.iloc[i]
            previous = data.iloc[i-1]
            
            # Bullish order block criteria
            if (current['Close'] > previous['High'] and
                current['High'] - current['Low'] <= self.config.n_pips and
                previous['price_derivative'] < -self.config.min_strength):
                
                results.append(DetectionResult(
                    pattern_type="BULLISH_ORDER_BLOCK",
                    timestamp=current['timestamp'],
                    entry_price=(current['High'] + current['Low'])/2,
                    stop_loss=current['Low'],
                    take_profit=current['High'] + (current['High'] - current['Low']),
                    confidence=self._calculate_strength(previous, current),
                    metadata={
                        'high': current['High'],
                        'low': current['Low'],
                        'trigger_candle': previous.to_dict()
                    }
                ))
                
            # Bearish order block criteria
            elif (current['Close'] < previous['Low'] and
                  current['High'] - current['Low'] <= self.config.n_pips and
                  previous['price_derivative'] > self.config.min_strength):
                  
                results.append(DetectionResult(
                    pattern_type="BEARISH_ORDER_BLOCK",
                    timestamp=current['timestamp'],
                    entry_price=(current['High'] + current['Low'])/2,
                    stop_loss=current['High'],
                    take_profit=current['Low'] - (current['High'] - current['Low']),
                    confidence=self._calculate_strength(previous, current),
                    metadata={
                        'high': current['High'],
                        'low': current['Low'],
                        'trigger_candle': previous.to_dict()
                    }
                ))
                
        return results
    
    def _calculate_strength(self, prev_candle, current_candle):
        """Calculate order block strength based on momentum and volume"""
        price_change = abs(prev_candle['Close'] - prev_candle['Open'])
        range_size = current_candle['High'] - current_candle['Low']
        
        # Handle zero division
        if range_size == 0:
            range_size = 0.0001  # Small non-zero value
            
        volume_ratio = prev_candle.get('Volume', 1) / current_candle.get('Volume', 1)
        if volume_ratio == 0:
            volume_ratio = 1.0
        
        return min(1.0, (price_change / range_size) * volume_ratio)
    
    def get_required_columns(self) -> List[str]:
        return ['High', 'Low', 'Close']