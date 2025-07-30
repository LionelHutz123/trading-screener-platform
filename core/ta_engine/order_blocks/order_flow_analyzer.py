from dataclasses import dataclass, field
import pandas as pd
from typing import List, Dict
from .order_block_detector import OrderBlockDetector, OrderBlockConfig
from .fvg_detector import FVGDetector, FVGConfig
from .swing_failure_detector import SwingFailureDetector, SwingFailureConfig
from ..patterns.detection_strategy import DetectionResult

@dataclass
class OrderFlowConfig:
    order_block: OrderBlockConfig = field(default_factory=lambda: OrderBlockConfig())
    fvg: FVGConfig = field(default_factory=FVGConfig)
    swing_failure: SwingFailureConfig = field(default_factory=SwingFailureConfig)
    consensus_threshold: float = 0.7  # Required overlap between signals

class OrderFlowAnalyzer:
    """Unified analysis of order flow components with confluence detection"""
    
    def __init__(self, config: OrderFlowConfig = None):
        self.config = config if config else OrderFlowConfig()
        self.config = config
        self.ob_detector = OrderBlockDetector(config.order_block)
        self.fvg_detector = FVGDetector(config.fvg)
        self.swing_detector = SwingFailureDetector(config.swing_failure)
        
    def analyze(self, data: pd.DataFrame) -> Dict:
        """Run complete order flow analysis with confluence detection"""
        results = {
            'order_blocks': self.ob_detector.detect(data),
            'fvg': self.fvg_detector.detect(data),
            'swing_failures': self.swing_detector.detect(data),
            'confluence': []
        }
        
        # Find price levels with multiple signals
        results['confluence'] = self._find_confluence_levels(results)
        results['market_bias'] = self._calculate_market_bias(results)
        results['heatmap'] = self._generate_heatmap(data, results)
        
        return results
    
    def _find_confluence_levels(self, results: Dict) -> List[DetectionResult]:
        """Identify price zones with multiple order flow signals"""
        confluence_points = []
        
        # Combine all detected events
        all_events = (results['order_blocks'] + 
                     results['fvg'] + 
                     results['swing_failures'])
        
        # Group events by price level
        price_levels = {}
        for event in all_events:
            key = round(event.price_level, 4)
            if key not in price_levels:
                price_levels[key] = {
                    'types': set(),
                    'events': [],
                    'total_strength': 0.0
                }
            price_levels[key]['types'].add(event.type)
            price_levels[key]['events'].append(event)
            price_levels[key]['total_strength'] += event.strength
        
        # Identify significant confluence zones
        for price, data in price_levels.items():
            if len(data['types']) >= 2 and data['total_strength'] >= self.config.consensus_threshold:
                confluence_points.append(
                    DetectionResult(
                        type="ORDER_FLOW_CONFLUENCE",
                        timestamp=data['events'][0].timestamp,
                        price_level=price,
                        strength=data['total_strength'],
                        metadata={
                            'event_types': list(data['types']),
                            'event_count': len(data['events']),
                            'events': [e.metadata for e in data['events']]
                        }
                    )
                )
                
        return sorted(confluence_points, key=lambda x: x.strength, reverse=True)
    
    def _calculate_market_bias(self, results: Dict) -> Dict:
        """Determine overall market bias based on order flow signals"""
        bull_signals = 0
        bear_signals = 0
        
        for event in results['order_blocks'] + results['fvg'] + results['swing_failures']:
            if 'BULLISH' in event.type:
                bull_signals += event.strength
            elif 'BEARISH' in event.type:
                bear_signals += event.strength
                
        total = bull_signals + bear_signals
        return {
            'bullish_bias': bull_signals / total if total > 0 else 0.5,
            'bearish_bias': bear_signals / total if total > 0 else 0.5
        }
    
    def _generate_heatmap(self, data: pd.DataFrame, results: Dict) -> pd.DataFrame:
        """Create order flow heatmap dataframe"""
        heatmap = data.copy()
        
        # Initialize heatmap columns
        heatmap['order_flow_score'] = 0.0
        heatmap['bullish_signals'] = 0
        heatmap['bearish_signals'] = 0
        
        # Aggregate signals
        for event in results['order_blocks'] + results['fvg'] + results['swing_failures']:
            idx = heatmap.index.get_loc(event.timestamp)
            heatmap.at[heatmap.index[idx], 'order_flow_score'] += event.strength
            if 'BULLISH' in event.type:
                heatmap.at[heatmap.index[idx], 'bullish_signals'] += 1
            elif 'BEARISH' in event.type:
                heatmap.at[heatmap.index[idx], 'bearish_signals'] += 1
                
        return heatmap[['order_flow_score', 'bullish_signals', 'bearish_signals']]

    def get_required_columns(self) -> List[str]:
        return list(set(
            self.ob_detector.get_required_columns() +
            self.fvg_detector.get_required_columns() +
            self.swing_detector.get_required_columns()
        ))

# Example usage:
# analyzer = OrderFlowAnalyzer()
# results = analyzer.analyze(price_data)
# print(results['confluence'])  # Shows strongest confluence zones