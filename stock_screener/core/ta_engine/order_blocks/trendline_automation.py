 # -*- coding: utf-8 -*-
import numpy as np
from scipy.stats import linregress

def fit_trendlines_high_low(highs, lows, closes):
    """Automatically fit support/resistance trendlines using recent price action"""
    # Calculate swing points for highs and lows
    swing_highs = _find_swing_points(highs, direction=1)
    swing_lows = _find_swing_points(lows, direction=-1)
    
    # Fit support trendline using recent swing lows
    support_slope, support_intercept = _best_fit_trendline(swing_lows)
    
    # Fit resistance trendline using recent swing highs
    resistance_slope, resistance_intercept = _best_fit_trendline(swing_highs)
    
    # Detect breakouts and retests
    breakout_detector = DetectTrendlineBreakouts()
    breakout, breakout_idx = breakout_detector.detect_breakouts(
        closes, resistance_slope, resistance_intercept)
    retest = breakout_detector.detect_retests(
        closes, support_slope, support_intercept, breakout_idx) if breakout else False
    
    return {
        'support': (support_slope, support_intercept),
        'resistance': (resistance_slope, resistance_intercept),
        'breakout': {
            'detected': breakout,
            'index': breakout_idx,
            'retest_confirmed': retest,
            'threshold': 0.005  # Default threshold value
        }
    }

def _find_swing_points(prices, direction=1, lookback=3):
    """Identify swing highs/low points in price series"""
    swings = []
    for i in range(lookback, len(prices)-lookback):
        window = prices[i-lookback:i+lookback+1]
        if direction == 1 and window[lookback] == max(window):
            swings.append((i, window[lookback]))
        elif direction == -1 and window[lookback] == min(window):
            swings.append((i, window[lookback]))
    return swings[-2:]  # Return last two swings

def _best_fit_trendline(points):
    """Calculate best fit line through given points"""
    if len(points) < 2:
        return 0, np.mean([p[1] for p in points]) if points else (0, 0)
    
    x = [p[0] for p in points]
    y = [p[1] for p in points]
    slope, intercept, *_ = linregress(x, y)
    return slope, intercept

class DetectTrendlineBreakouts:
    @staticmethod
    def detect_breakouts(closes, resistance_slope, resistance_intercept, threshold=0.005):
        """Detect price closing above resistance trendline with confirmation"""
        if len(closes) < 3:
            return False, -1
        
        # Calculate trendline values for last 3 periods
        x_vals = np.array([len(closes)-3, len(closes)-2, len(closes)-1])
        trendline_vals = resistance_slope * x_vals + resistance_intercept
        
        # Check closes vs trendline
        above_trendline = closes[-3:] > trendline_vals * (1 + threshold)
        
        # Require consecutive closes above
        if np.all(above_trendline):
            return True, len(closes)-1
        return False, -1

    @staticmethod
    def detect_retests(closes, support_slope, support_intercept, breakout_idx, threshold=0.005):
        """Detect successful retest of support after breakout"""
        if len(closes) < 5 or breakout_idx < 3:
            return False
        
        # Calculate trendline values for retest window
        test_window = closes[breakout_idx-2:breakout_idx+1]
        x_vals = np.arange(len(test_window))
        trendline_vals = support_slope * x_vals + support_intercept
        
        # Check for touch + reaction
        touches = np.any(test_window <= trendline_vals * (1 + threshold))
        reaction = closes[-1] > trendline_vals[-1]
        
        return touches and reaction