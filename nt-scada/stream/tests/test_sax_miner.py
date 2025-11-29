import pytest
import sys
import os
import numpy as np

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sax_miner import SAXMiner

class TestSAXMiner:
    def test_initialization(self):
        """Test initialization with valid and invalid parameters"""
        miner = SAXMiner(window_size=10, alphabet_size=3)
        assert miner.window_size == 10
        assert miner.alphabet_size == 3
        
        with pytest.raises(ValueError):
            SAXMiner(alphabet_size=10) # Unsupported size

    def test_buffering(self):
        """Test that it waits for buffer to fill"""
        miner = SAXMiner(window_size=5, alphabet_size=3)
        
        # First 4 values should return None
        for i in range(4):
            assert miner.process(i) is None
            
        # 5th value should return a symbol
        assert miner.process(5) is not None

    def test_symbol_generation(self):
        """Test correct symbol assignment for 3-letter alphabet (a, b, c)"""
        # Breakpoints for 3: [-0.43, 0.43]
        # We need to construct a window where the Z-score lands in specific regions
        
        miner = SAXMiner(window_size=3, alphabet_size=3)
        
        # 1. Test 'b' (middle)
        # Window: [10, 10, 10] -> Mean=10, Std=0 (handled as 1e-9)
        # Value 10 -> Z=0 -> Between -0.43 and 0.43 -> 'b'
        miner.process(10)
        miner.process(10)
        symbol = miner.process(10)
        assert symbol == 'b'
        
        # 2. Test 'c' (high)
        # Window: [10, 10, 20] -> Mean=13.33, Std=4.71
        # Value 20 -> Z = (20 - 13.33) / 4.71 = 1.41 -> > 0.43 -> 'c'
        miner = SAXMiner(window_size=3, alphabet_size=3)
        miner.process(10)
        miner.process(10)
        symbol = miner.process(20)
        assert symbol == 'c'

        # 3. Test 'a' (low)
        # Window: [10, 10, 0] -> Mean=6.66, Std=4.71
        # Value 0 -> Z = (0 - 6.66) / 4.71 = -1.41 -> < -0.43 -> 'a'
        miner = SAXMiner(window_size=3, alphabet_size=3)
        miner.process(10)
        miner.process(10)
        symbol = miner.process(0)
        assert symbol == 'a'
