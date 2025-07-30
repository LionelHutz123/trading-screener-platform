from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime

@dataclass
class DetectionResult:
    """Result of a pattern detection"""
    pattern_type: str
    timestamp: datetime
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    metadata: Dict[str, Any]

class DetectionStrategy(ABC):
    """Base class for all pattern detection strategies"""
    
    @abstractmethod
    def detect(self, data: pd.DataFrame) -> List[DetectionResult]:
        """Main detection method to be implemented by subclasses"""
        pass
    
    def _validate_data(self, data: pd.DataFrame, required_columns: List[str]) -> bool:
        """Validate that required columns exist in dataframe"""
        return all(col.lower() in map(str.lower, data.columns) for col in required_columns)
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high = data['High']
        low = data['Low']
        close = data['Close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        return tr.rolling(window=period).mean()
    
    def _calculate_swing_strength(self, data: pd.DataFrame, window: int = 20) -> pd.Series:
        """Calculate swing strength based on price movement and volume"""
        returns = np.log(data['Close'] / data['Close'].shift(1))
        volume_ma = data['Volume'].rolling(window=window).mean()
        relative_volume = data['Volume'] / volume_ma
        
        return returns * relative_volume

    def get_required_columns(self) -> List[str]:
        """Get required columns for detection"""
        raise NotImplementedError 