from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime

@dataclass
class DetectionResult:
    """Base class for pattern detection results"""
    pattern_type: str
    timestamp: datetime
    confidence: float
    metadata: Dict[str, Any] 