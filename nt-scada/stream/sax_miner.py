"""
SAX Miner (Symbolic Aggregate approXimation)
===========================================
This module implements SAX for converting continuous sensor streams into 
symbolic string representations.

Technique:
1. Normalize data (Z-Score)
2. Discretize into symbols (e.g., 'a', 'b', 'c') based on Gaussian breakpoints.
3. Form words from symbols to detect patterns.
"""

import numpy as np
from collections import deque

class SAXMiner:
    def __init__(self, window_size=10, alphabet_size=3):
        """
        Initialize SAX Miner.
        
        Args:
            window_size (int): Number of data points to keep for normalization.
            alphabet_size (int): Number of symbols (3 to 5 supported).
        """
        self.window_size = window_size
        self.alphabet_size = alphabet_size
        self.buffer = deque(maxlen=window_size)
        
        # Breakpoints for standard normal distribution (approximate)
        # These define the regions for 'a', 'b', 'c', etc.
        self.breakpoints = {
            3: [-0.43, 0.43],
            4: [-0.67, 0, 0.67],
            5: [-0.84, -0.25, 0.25, 0.84]
        }
        
        if alphabet_size not in self.breakpoints:
            raise ValueError("Alphabet size must be 3, 4, or 5")

    def _get_symbol(self, normalized_value):
        """Convert a z-normalized value to a symbol."""
        cuts = self.breakpoints[self.alphabet_size]
        
        # Determine symbol index
        # 'a' is the lowest value, 'b' is next, etc.
        # ord('a') = 97
        
        for i, cut in enumerate(cuts):
            if normalized_value < cut:
                return chr(97 + i)
        
        # If larger than all cuts, it's the last symbol
        return chr(97 + len(cuts))

    def process(self, value):
        """
        Process a new value and return its symbolic representation if window is full.
        
        Returns:
            str or None: The symbol for the current value, or None if buffer not full.
        """
        self.buffer.append(value)
        
        if len(self.buffer) < self.window_size:
            return None
            
        # Calculate Z-Score for the current value based on the window
        # We use the window's mean and std to normalize the LATEST value
        # Note: In strict SAX, you normalize a whole PAA frame. 
        # Here we do a sliding window z-score for online stream.
        
        window_data = np.array(self.buffer)
        mean = np.mean(window_data)
        std = np.std(window_data)
        
        if std == 0:
            std = 1e-9 # Avoid division by zero
            
        normalized_value = (value - mean) / std
        
        return self._get_symbol(normalized_value)
