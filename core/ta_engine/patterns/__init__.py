# Make patterns directory a Python package
from .base_detector import DetectionStrategy, DetectionResult
from .flag_pattern import FlagPatternDetector, FlagConfig

__all__ = [
    'DetectionStrategy',
    'DetectionResult',
    'FlagPatternDetector',
    'FlagConfig'
]