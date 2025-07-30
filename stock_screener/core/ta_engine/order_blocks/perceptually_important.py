# -*- coding: utf-8 -*-
import numpy as np

def find_pips(data, n_pips=5, dist_measure=2):
    """Identify perceptually important points using sliding window"""
    pips = []
    n = len(data)
    window_size = n // n_pips
    
    for i in range(0, n, window_size):
        window = data[i:i+window_size]
        if len(window) == 0:
            continue
        # Find most significant point in window
        if dist_measure == 2:  # Vertical distance measure
            avg = np.mean(window)
            pip_index = np.argmax(np.abs(window - avg))
        else:  # Euclidean distance measure
            pip_index = np.argmax(window)
        pips.append((i + pip_index, window[pip_index]))
    
    return zip(*pips) if pips else ([], [])