# -*- coding: utf-8 -*-
from .perceptually_important import find_pips
from .trendline_automation import fit_trendlines_high_low
import pandas as pd
import numpy as np

class OrderBlockDetector:
    def __init__(self, window_size=20, n_pips=5):
        self.window = window_size
        self.n_pips = n_pips
        
    def detect(self, ohlc_data: pd.DataFrame):
        lows = ohlc_data.low.values[-self.window:]
        highs = ohlc_data.high.values[-self.window:]
        
        pip_x, pip_y = find_pips(lows, n_pips=self.n_pips, dist_measure=2)
        
        support_coefs, resist_coefs = fit_trendlines_high_low(
            highs,
            lows,
            ohlc_data.close.values[-self.window:]
        )
        
        return self._filter_blocks(pip_x, pip_y, support_coefs)
    
    def _filter_blocks(self, pip_x, pip_y, support_coefs):
        valid_blocks = []
        slope, intercept = support_coefs
        
        for x, y in zip(pip_x, pip_y):
            expected = slope * x + intercept
            if y >= expected - 0.0001:
                valid_blocks.append({
                    'index': x,
                    'price': y,
                    'slope': slope,
                    'intercept': intercept
                })
        return valid_blocks
