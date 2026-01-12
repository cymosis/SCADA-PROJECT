import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stream_miner import StreamMiner

class TestStreamMiner:
    @pytest.fixture
    def miner(self):
        """Fixture to create a StreamMiner instance with mocked dependencies"""
        # We don't need to mock kafka here because StreamMiner init doesn't connect to kafka
        # It only initializes river objects
        return StreamMiner()

    def test_drift_detection(self, miner):
        """Test that ADWIN detects drift when values change significantly"""
        sensor_id = "test_sensor_1"
        
        # 1. Feed stable values (mean ~ 10)
        for _ in range(100):
            record = {'sensor_id': sensor_id, 'value': 10.0}
            result = miner.process_record(record)
            assert result['drift_detected'] is False

        # 2. Feed sudden spike (mean ~ 100)
        # ADWIN needs a few samples to confirm drift
        drift_found = False
        for _ in range(50):
            record = {'sensor_id': sensor_id, 'value': 100.0}
            result = miner.process_record(record)
            if result['drift_detected']:
                drift_found = True
                break
        
        assert drift_found is True

    def test_rolling_variance(self, miner):
        """Test that rolling variance is calculated"""
        sensor_id = "test_sensor_2"
        
        # Feed identical values -> Variance should be 0
        miner.process_record({'sensor_id': sensor_id, 'value': 5.0})
        result = miner.process_record({'sensor_id': sensor_id, 'value': 5.0})
        
        assert result['rolling_variance'] == 0.0
        
        # Feed different value -> Variance should increase
        result = miner.process_record({'sensor_id': sensor_id, 'value': 10.0})
        assert result['rolling_variance'] > 0.0

    def test_model_learning(self, miner):
        """Test that the Hoeffding Tree makes predictions and learns"""
        sensor_id = "test_sensor_3"
        record = {'sensor_id': sensor_id, 'value': 50.0}
        
        result = miner.process_record(record)
        
        # Check structure
        assert 'model_prediction' in result
        assert result['sensor_id'] == sensor_id
