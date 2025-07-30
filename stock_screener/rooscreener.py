from typing import List, Dict
import pandas as pd
from core.ta_engine.patterns.flag_pattern import FlagPatternStrategy, PatternConfig
from core.ta_engine.divergences import RSIDivergenceStrategy, DivergenceConfig
from core.ta_engine.order_blocks.order_block_detector import OrderBlockDetector
from config import StrategyConfig

class CompositeStrategy:
    """Orchestrates multiple detection strategies"""
    
    def __init__(self, config: StrategyConfig):
        self.strategies = [
            FlagPatternStrategy(config.flag_pattern),
            RSIDivergenceStrategy(config.divergence),
            OrderBlockDetector(config.order_blocks)
        ]
        
    def run_screening(self, data: pd.DataFrame) -> Dict[str, List]:
        """Execute all strategies and return consolidated results"""
        results = {}
        
        for strategy in self.strategies:
            try:
                strategy_results = strategy.detect(data)
                results[strategy.__class__.__name__] = strategy_results
            except Exception as e:
                print(f"Error running {strategy.__class__.__name__}: {str(e)}")
                
        return results

    def get_required_columns(self) -> List[str]:
        """Get union of all required data columns"""
        columns = set()
        for strategy in self.strategies:
            columns.update(strategy.get_required_columns())
        return list(columns)