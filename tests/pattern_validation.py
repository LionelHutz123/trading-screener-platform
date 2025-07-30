import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.ta_engine.patterns.swing_detector import SwingDetector, SwingConfig
from core.ta_engine.patterns.choch_detector import CHoCHDetector, CHoCHConfig
from core.ta_engine.patterns.order_block_detector import OrderBlockDetector, OBConfig
from core.ta_engine.patterns.fvg_detector import FVGDetector, FVGConfig

def load_test_data(symbol: str) -> pd.DataFrame:
    """Load test data from CSV file"""
    try:
        df = pd.read_csv(symbol)
        df['timestamp'] = pd.to_datetime(df['timestamp'])  # Assuming timestamp column exists
        return df.set_index('timestamp')
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return None

def print_pattern_stats(name: str, results: list):
    """Print detection statistics"""
    if not results:
        print(f"\n{name} Detection: No patterns found")
        return
        
    print(f"\n{name} Detection Statistics:")
    print(f"Total patterns found: {len(results)}")
    
    # Pattern types
    pattern_types = {}
    for r in results:
        pattern_types[r.pattern_type] = pattern_types.get(r.pattern_type, 0) + 1
    print("\nPattern Types:")
    for pt, count in pattern_types.items():
        print(f"- {pt}: {count}")
    
    # Confidence stats
    confidences = [r.confidence for r in results]
    print(f"\nConfidence Levels:")
    print(f"- Average: {np.mean(confidences):.2f}")
    print(f"- Min: {min(confidences):.2f}")
    print(f"- Max: {max(confidences):.2f}")
    
    # Sample patterns
    print("\nSample Patterns:")
    for i, r in enumerate(results[:3], 1):
        print(f"\nPattern {i}:")
        print(f"- Type: {r.pattern_type}")
        print(f"- Time: {r.timestamp}")
        print(f"- Entry: {r.entry_price:.2f}")
        print(f"- Stop: {r.stop_loss:.2f}")
        print(f"- Target: {r.take_profit:.2f}")
        print(f"- Confidence: {r.confidence:.2f}")
        print("- Metadata:")
        for k, v in r.metadata.items():
            print(f"  {k}: {v}")

def main():
    # Test data - using available files
    symbols = [
        "WYNN_4h_2022-01-01_2024-09-13.csv",
        "ETSY_4h_2022-01-01_2024-09-13.csv",
        "MTCH_4h_2022-01-01_2024-09-13.csv"
    ]
    
    for symbol in symbols:
        print(f"\n{'='*50}")
        print(f"Testing {symbol}")
        print(f"{'='*50}")
        
        # Load data
        data = load_test_data(symbol)
        if data is None:
            continue
            
        print(f"\nAnalyzing {len(data)} bars...")
        
        # Initialize detectors
        swing_detector = SwingDetector()
        choch_detector = CHoCHDetector()
        ob_detector = OrderBlockDetector()
        fvg_detector = FVGDetector()
        
        # Detect patterns
        try:
            # Swing points
            swing_results = swing_detector.detect(data)
            print_pattern_stats("Swing Points", swing_results)
            
            # CHoCH patterns
            choch_results = choch_detector.detect(data)
            print_pattern_stats("Change of Character", choch_results)
            
            # Order blocks
            ob_results = ob_detector.detect(data)
            print_pattern_stats("Order Blocks", ob_results)
            
            # Fair value gaps
            fvg_results = fvg_detector.detect(data)
            print_pattern_stats("Fair Value Gaps", fvg_results)
            
        except Exception as e:
            print(f"Error during detection: {str(e)}")
            continue
            
        print("\nValidation complete!")

if __name__ == "__main__":
    main() 