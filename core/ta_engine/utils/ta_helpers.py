from typing import List, Dict, Any
import pandas as pd
from dataclasses import dataclass
from core.ta_engine.patterns.detection_strategy import DetectionResult

@dataclass
class PivotConfig:
    lookback_left: int = 5
    lookback_right: int = 5
    range_upper: int = 60
    range_lower: int = 5

class PivotDetector:
    def __init__(self, config: PivotConfig):
        self.config = config
        
    def detect_pivot_highs(self, series: pd.Series) -> pd.Series:
        """Vectorized detection of pivot highs"""
        return (
            (series > series.shift(1).rolling(self.config.lookback_left).max()) &
            (series > series.shift(-self.config.lookback_right).rolling(self.config.lookback_right).max())
        )
    
    def detect_pivot_lows(self, series: pd.Series) -> pd.Series:
        """Vectorized detection of pivot lows"""
        return (
            (series < series.shift(1).rolling(self.config.lookback_left).min()) &
            (series < series.shift(-self.config.lookback_right).rolling(self.config.lookback_right).min())
        )

class PositionManager:
    def __init__(self, risk_percent: float = 1.0):
        self.risk_percent = risk_percent
        
    def calculate_position(
        self,
        entry_price: float,
        stop_loss: float,
        risk_capital: float
    ) -> Dict[str, Any]:
        """Calculate position size based on risk parameters"""
        risk_per_share = abs(entry_price - stop_loss)
        position_size = (risk_capital * self.risk_percent) / risk_per_share
        
        return {
            'size': round(position_size, 2),
            'risk_per_share': risk_per_share,
            'max_loss': risk_capital * self.risk_percent
        }