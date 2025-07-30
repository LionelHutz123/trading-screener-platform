import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime
import json

# Import existing strategies
from .patterns.base_detector import DetectionStrategy, DetectionResult
from .patterns.flag_pattern import FlagPatternDetector, FlagConfig
from .patterns.order_block_detector import OrderBlockDetector, OBConfig
from .patterns.fvg_detector import FVGDetector, FVGConfig
from .patterns.choch_detector import CHoCHDetector, CHoCHConfig
from .patterns.swing_detector import SwingDetector, SwingConfig
from .divergences.rsi_divergence import RSIDivergenceStrategy, DivergenceConfig
from .indicators import TechnicalIndicatorEngine, IndicatorConfig

# Import stock_screener strategies
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'stock_screener'))
from stock_screener.core.ta_engine.order_blocks.order_block_detector import OrderBlockDetector as StockScreenerOrderBlockDetector
from stock_screener.core.ta_engine.order_blocks.trendline_automation import fit_trendlines_high_low

logger = logging.getLogger(__name__)

@dataclass
class UnifiedStrategyConfig:
    """Configuration for unified strategy engine"""
    # Indicator settings
    indicator_config: IndicatorConfig = None
    
    # Pattern detection settings
    flag_config: FlagConfig = None
    order_block_config: OBConfig = None
    fvg_config: FVGConfig = None
    choch_config: CHoCHConfig = None
    swing_config: SwingConfig = None
    
    # Divergence settings
    divergence_config: DivergenceConfig = None
    
    # Stock screener settings
    stock_screener_window: int = 20
    stock_screener_n_pips: int = 5
    
    # Confluence settings
    confluence_threshold: float = 0.6
    min_signals_for_confluence: int = 2
    
    def __post_init__(self):
        if self.indicator_config is None:
            self.indicator_config = IndicatorConfig()
        if self.flag_config is None:
            self.flag_config = FlagConfig()
        if self.order_block_config is None:
            self.order_block_config = OBConfig()
        if self.fvg_config is None:
            self.fvg_config = FVGConfig()
        if self.choch_config is None:
            self.choch_config = CHoCHConfig()
        if self.swing_config is None:
            self.swing_config = SwingConfig()
        if self.divergence_config is None:
            self.divergence_config = DivergenceConfig()

@dataclass
class ConfluenceSignal:
    """Represents a confluence of multiple signals"""
    timestamp: datetime
    signal_type: str  # 'bullish', 'bearish', 'neutral'
    strength: float
    signals: List[str]  # List of contributing signals
    entry_price: float
    stop_loss: float
    take_profit: float
    metadata: Dict[str, Any]

class UnifiedStrategyEngine:
    """Unified strategy engine that combines all detection methods"""
    
    def __init__(self, config: UnifiedStrategyConfig = None):
        self.config = config or UnifiedStrategyConfig()
        self.logger = logger
        
        # Initialize indicator engine
        self.indicator_engine = TechnicalIndicatorEngine(self.config.indicator_config)
        
        # Initialize pattern detectors
        self.flag_detector = FlagPatternDetector(self.config.flag_config)
        self.order_block_detector = OrderBlockDetector(self.config.order_block_config)
        self.fvg_detector = FVGDetector(self.config.fvg_config)
        self.choch_detector = CHoCHDetector(self.config.choch_config)
        self.swing_detector = SwingDetector(self.config.swing_config)
        
        # Initialize divergence detector
        self.divergence_detector = RSIDivergenceStrategy(self.config.divergence_config)
        
        # Initialize stock screener strategies
        self.stock_screener_ob_detector = StockScreenerOrderBlockDetector(
            window_size=self.config.stock_screener_window,
            n_pips=self.config.stock_screener_n_pips
        )
        
    def run_comprehensive_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Run comprehensive analysis with all strategies"""
        results = {
            'indicators': {},
            'patterns': {},
            'divergences': {},
            'stock_screener': {},
            'confluence': [],
            'summary': {}
        }
        
        try:
            # Calculate all technical indicators
            self.logger.info("Calculating technical indicators...")
            results['indicators'] = self.indicator_engine.calculate_all_indicators(data)
            
            # Run pattern detection strategies
            self.logger.info("Running pattern detection strategies...")
            results['patterns'] = self._run_pattern_detection(data)
            
            # Run divergence detection
            self.logger.info("Running divergence detection...")
            results['divergences'] = self._run_divergence_detection(data)
            
            # Run stock screener strategies
            self.logger.info("Running stock screener strategies...")
            results['stock_screener'] = self._run_stock_screener_strategies(data)
            
            # Find confluence signals
            self.logger.info("Finding confluence signals...")
            results['confluence'] = self._find_confluence_signals(data, results)
            
            # Generate summary
            results['summary'] = self._generate_analysis_summary(results)
            
            self.logger.info("Comprehensive analysis completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive analysis: {str(e)}")
            raise
        
        return results
    
    def _run_pattern_detection(self, data: pd.DataFrame) -> Dict[str, List[DetectionResult]]:
        """Run all pattern detection strategies"""
        patterns = {}
        
        try:
            # Flag patterns
            patterns['flag_patterns'] = self.flag_detector.detect(data)
            self.logger.debug(f"Found {len(patterns['flag_patterns'])} flag patterns")
            
            # Order blocks
            patterns['order_blocks'] = self.order_block_detector.detect(data)
            self.logger.debug(f"Found {len(patterns['order_blocks'])} order blocks")
            
            # Fair value gaps
            patterns['fvg_patterns'] = self.fvg_detector.detect(data)
            self.logger.debug(f"Found {len(patterns['fvg_patterns'])} FVG patterns")
            
            # Change of character
            patterns['choch_patterns'] = self.choch_detector.detect(data)
            self.logger.debug(f"Found {len(patterns['choch_patterns'])} CHoCH patterns")
            
            # Swing points
            patterns['swing_patterns'] = self.swing_detector.detect(data)
            self.logger.debug(f"Found {len(patterns['swing_patterns'])} swing patterns")
            
        except Exception as e:
            self.logger.error(f"Error in pattern detection: {str(e)}")
            patterns = {key: [] for key in ['flag_patterns', 'order_blocks', 'fvg_patterns', 'choch_patterns', 'swing_patterns']}
        
        return patterns
    
    def _run_divergence_detection(self, data: pd.DataFrame) -> Dict[str, List[DetectionResult]]:
        """Run divergence detection strategies"""
        divergences = {}
        
        try:
            # RSI divergence
            divergences['rsi_divergences'] = self.divergence_detector.detect(data)
            self.logger.debug(f"Found {len(divergences['rsi_divergences'])} RSI divergences")
            
        except Exception as e:
            self.logger.error(f"Error in divergence detection: {str(e)}")
            divergences = {'rsi_divergences': []}
        
        return divergences
    
    def _run_stock_screener_strategies(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Run stock screener specific strategies"""
        stock_screener_results = {}
        
        try:
            # Normalize column names to lowercase for stock screener compatibility
            ohlc_data = data.copy()
            ohlc_data.columns = ohlc_data.columns.str.lower()
            
            # Order block detection from stock screener
            stock_screener_results['order_blocks'] = self.stock_screener_ob_detector.detect(ohlc_data)
            self.logger.debug(f"Found {len(stock_screener_results['order_blocks'])} stock screener order blocks")
            
            # Trendline analysis
            if len(data) >= 20:
                highs = data['High'].values[-20:]
                lows = data['Low'].values[-20:]
                closes = data['Close'].values[-20:]
                
                trendline_results = fit_trendlines_high_low(highs, lows, closes)
                stock_screener_results['trendlines'] = trendline_results
                self.logger.debug("Trendline analysis completed")
            
        except Exception as e:
            self.logger.error(f"Error in stock screener strategies: {str(e)}")
            stock_screener_results = {'order_blocks': [], 'trendlines': {}}
        
        return stock_screener_results
    
    def _find_confluence_signals(self, data: pd.DataFrame, results: Dict[str, Any]) -> List[ConfluenceSignal]:
        """Find confluence of multiple signals"""
        confluence_signals = []
        
        try:
            # Collect all signals by timestamp
            signal_map = {}
            
            # Add pattern signals
            for pattern_type, patterns in results['patterns'].items():
                for pattern in patterns:
                    timestamp = pattern.timestamp
                    if timestamp not in signal_map:
                        signal_map[timestamp] = {'bullish': [], 'bearish': [], 'neutral': []}
                    
                    signal_type = self._classify_signal_type(pattern.pattern_type)
                    signal_map[timestamp][signal_type].append({
                        'type': pattern_type,
                        'pattern': pattern.pattern_type,
                        'confidence': pattern.confidence,
                        'entry_price': pattern.entry_price,
                        'stop_loss': pattern.stop_loss,
                        'take_profit': pattern.take_profit
                    })
            
            # Add divergence signals
            for divergence_type, divergences in results['divergences'].items():
                for divergence in divergences:
                    timestamp = divergence.timestamp
                    if timestamp not in signal_map:
                        signal_map[timestamp] = {'bullish': [], 'bearish': [], 'neutral': []}
                    
                    signal_type = self._classify_signal_type(divergence.pattern_type)
                    signal_map[timestamp][signal_type].append({
                        'type': divergence_type,
                        'pattern': divergence.pattern_type,
                        'confidence': divergence.confidence,
                        'entry_price': divergence.entry_price,
                        'stop_loss': divergence.stop_loss,
                        'take_profit': divergence.take_profit
                    })
            
            # Find confluence points
            for timestamp, signals in signal_map.items():
                for signal_type in ['bullish', 'bearish']:
                    if len(signals[signal_type]) >= self.config.min_signals_for_confluence:
                        # Calculate confluence strength
                        total_confidence = sum(s['confidence'] for s in signals[signal_type])
                        avg_confidence = total_confidence / len(signals[signal_type])
                        
                        if avg_confidence >= self.config.confluence_threshold:
                            # Calculate average entry, stop, and target
                            avg_entry = np.mean([s['entry_price'] for s in signals[signal_type]])
                            avg_stop = np.mean([s['stop_loss'] for s in signals[signal_type]])
                            avg_target = np.mean([s['take_profit'] for s in signals[signal_type]])
                            
                            confluence_signals.append(ConfluenceSignal(
                                timestamp=timestamp,
                                signal_type=signal_type,
                                strength=avg_confidence,
                                signals=[s['pattern'] for s in signals[signal_type]],
                                entry_price=avg_entry,
                                stop_loss=avg_stop,
                                take_profit=avg_target,
                                metadata={
                                    'signal_count': len(signals[signal_type]),
                                    'individual_signals': signals[signal_type]
                                }
                            ))
            
            self.logger.info(f"Found {len(confluence_signals)} confluence signals")
            
        except Exception as e:
            self.logger.error(f"Error finding confluence signals: {str(e)}")
        
        return confluence_signals
    
    def _classify_signal_type(self, pattern_type: str) -> str:
        """Classify pattern type as bullish, bearish, or neutral"""
        pattern_lower = pattern_type.lower()
        
        bullish_keywords = ['bull', 'bullish', 'long', 'buy', 'support']
        bearish_keywords = ['bear', 'bearish', 'short', 'sell', 'resistance']
        
        for keyword in bullish_keywords:
            if keyword in pattern_lower:
                return 'bullish'
        
        for keyword in bearish_keywords:
            if keyword in pattern_lower:
                return 'bearish'
        
        return 'neutral'
    
    def _generate_analysis_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for the analysis"""
        summary = {
            'total_patterns': 0,
            'total_divergences': 0,
            'total_confluence_signals': len(results['confluence']),
            'signal_distribution': {},
            'strength_distribution': {},
            'recommendations': []
        }
        
        # Count patterns
        for pattern_type, patterns in results['patterns'].items():
            summary['total_patterns'] += len(patterns)
            summary['signal_distribution'][pattern_type] = len(patterns)
        
        # Count divergences
        for divergence_type, divergences in results['divergences'].items():
            summary['total_divergences'] += len(divergences)
            summary['signal_distribution'][divergence_type] = len(divergences)
        
        # Analyze confluence signals
        if results['confluence']:
            bullish_signals = [s for s in results['confluence'] if s.signal_type == 'bullish']
            bearish_signals = [s for s in results['confluence'] if s.signal_type == 'bearish']
            
            summary['strength_distribution'] = {
                'bullish_avg_strength': np.mean([s.strength for s in bullish_signals]) if bullish_signals else 0,
                'bearish_avg_strength': np.mean([s.strength for s in bearish_signals]) if bearish_signals else 0,
                'overall_avg_strength': np.mean([s.strength for s in results['confluence']])
            }
            
            # Generate recommendations
            if bullish_signals and bearish_signals:
                if len(bullish_signals) > len(bearish_signals):
                    summary['recommendations'].append("Bullish bias detected with multiple confluence signals")
                else:
                    summary['recommendations'].append("Bearish bias detected with multiple confluence signals")
            elif bullish_signals:
                summary['recommendations'].append("Strong bullish confluence signals detected")
            elif bearish_signals:
                summary['recommendations'].append("Strong bearish confluence signals detected")
        
        return summary
    
    def get_latest_signals(self, data: pd.DataFrame, lookback_periods: int = 10) -> Dict[str, Any]:
        """Get latest signals from recent data"""
        if len(data) < lookback_periods:
            lookback_periods = len(data)
        
        recent_data = data.tail(lookback_periods)
        results = self.run_comprehensive_analysis(recent_data)
        
        # Filter for recent signals only
        latest_signals = {
            'patterns': {},
            'divergences': {},
            'confluence': []
        }
        
        for pattern_type, patterns in results['patterns'].items():
            latest_signals['patterns'][pattern_type] = [
                p for p in patterns 
                if p.timestamp >= recent_data.index[0]
            ]
        
        for divergence_type, divergences in results['divergences'].items():
            latest_signals['divergences'][divergence_type] = [
                d for d in divergences 
                if d.timestamp >= recent_data.index[0]
            ]
        
        latest_signals['confluence'] = [
            c for c in results['confluence']
            if c.timestamp >= recent_data.index[0]
        ]
        
        return latest_signals 