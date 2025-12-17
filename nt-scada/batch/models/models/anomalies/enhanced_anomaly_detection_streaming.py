"""
NT-SCADA ANOMALY DETECTION SYSTEM

1. Online Z-Score (Welford's Algorithm) - Detect anomalies
2. ADWIN Drift Detection - Automatic adaptation to changing distributions
3. Count-Min Sketch - Pattern frequency tracking
"""

import os
import time
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from collections import defaultdict, deque
from streaming_algorithms import (
    WelfordOnlineStats, ADWIN, OnlineZScore, 
    ExponentialHistogram, CountMinSketch, StreamingAnomalyDetector
)
import warnings
warnings.filterwarnings('ignore')

# Configuration
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'mytoken')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'scada')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', 'normal_data')
ANOMALY_BUCKET = os.getenv('ANOMALY_BUCKET', 'anomaly_data')
POLLING_INTERVAL = int(os.getenv('POLLING_INTERVAL', '5'))

# Model paths (for initial loading, will be updated incrementally)
BINARY_MODEL_PATH = os.getenv('BINARY_MODEL_PATH', '/app/models/binary_classifier.pkl')
FINE_GRAINED_MODEL_PATH = os.getenv('FINE_GRAINED_MODEL_PATH', '/app/models/fine_grained_classifier.pkl')

# Streaming thresholds
Z_SCORE_THRESHOLD = float(os.getenv('Z_SCORE_THRESHOLD', '3.0'))
DRIFT_SENSITIVITY = float(os.getenv('DRIFT_SENSITIVITY', '0.002'))
WARMUP_PERIOD = int(os.getenv('WARMUP_PERIOD', '30'))

# Track last processed timestamp
LAST_PROCESSED_TIME = None

# Expected sensor columns
EXPECTED_SENSOR_COLUMNS = [
    'LIT 101', 'LIT 301', 'LIT 401',
    'FIT 101', 'FIT 201', 'FIT 301', 'FIT 401', 'FIT 501', 'FIT 502', 'FIT 503', 'FIT 504', 'FIT 601',
    'AIT 201', 'AIT 202', 'AIT 203', 'AIT 301', 'AIT 302', 'AIT 303', 
    'AIT 401', 'AIT 402', 'AIT 501', 'AIT 502', 'AIT 503', 'AIT 504',
    'DPIT 301', 'PIT 501', 'PIT 502', 'PIT 503',
    'MV 101', 'MV 201', 'MV 301', 'MV 302', 'MV 303', 'MV 304', 'MV 501', 'MV 502', 'MV 503', 'MV 504',
    'P101 Status', 'P102 Status', 'P201 Status', 'P202 Status', 'P203 Status', 'P204 Status',
    'P205 Status', 'P206 Status', 'P207 Status', 'P208 Status',
    'P301 Status', 'P302 Status', 'P401 Status', 'P402 Status', 'P403 Status', 'P404 Status',
    'P501 Status', 'P502 Status', 'P601 Status', 'P602 Status', 'P603 Status',
    'LS 201', 'LS 202', 'LS 401',
    'LSH 601', 'LSH 602', 'LSH 603', 'LSL 203', 'LSL 601', 'LSL 602', 'LSL 603', 'LSLL 203',
    'UV401'
]

# Attack type mapping
ATTACK_TYPE_MAP = {
    0: 'NORMAL',
    1: 'DOS',
    2: 'NMRI',
    3: 'CMRI',
    4: 'SSCP',
    5: 'SSMP',
    6: 'MSCP',
    7: 'MSMP',
    8: 'RECON'
}


class FullyStreamingDetector:
    """
    Complete streaming anomaly detector
    """
    
    def __init__(self, influxdb_url, token, org, bucket):
        self.client = InfluxDBClient(url=influxdb_url, token=token, org=org)
        self.query_api = self.client.query_api()
        self.bucket = bucket
        self.last_processed_time = None
        
        # Initialize streaming algorithms
        print(f"Initializing streaming algorithms for {len(EXPECTED_SENSOR_COLUMNS)} sensors...")
        self.streaming_detector = StreamingAnomalyDetector(
            sensors=EXPECTED_SENSOR_COLUMNS,
            warmup_period=WARMUP_PERIOD,
            drift_sensitivity=DRIFT_SENSITIVITY
        )
        
        # Exponential moving averages for ML confidence scores
        self.ml_confidence_ema = {}
        self.ema_alpha = 0.1
        
        # Attack pattern tracking with Count-Min Sketch
        self.pattern_sketch = CountMinSketch(width=1000, depth=5)
        
        # Sliding windows for correlation analysis
        self.correlation_windows = defaultdict(lambda: deque(maxlen=50))
        
        # Load pre-trained models
        self.binary_model = None
        self.fine_grained_model = None
        self._load_ml_models()
        
        # Statistics
        self.total_samples = 0
        self.total_anomalies = 0
        self.total_drift_events = 0
        self.detection_method_counts = defaultdict(int)
        
        print(f"Streaming detector initialized")
    
    def _load_ml_models(self):
        """Load pre-trained ML models"""
        try:
            if os.path.exists(BINARY_MODEL_PATH):
                self.binary_model = joblib.load(BINARY_MODEL_PATH)
                print(f"Binary classifier loaded")
        except Exception as e:
            print(f"No binary model: {e}")
        
        try:
            if os.path.exists(FINE_GRAINED_MODEL_PATH):
                self.fine_grained_model = joblib.load(FINE_GRAINED_MODEL_PATH)
                print(f"Fine-grained classifier loaded")
        except Exception as e:
            print(f"No fine-grained model: {e}")
    
    def detect_streaming(self, sensor_data):
        """
        Returns anomalies detected.
        """
        anomalies = []
        self.total_samples += 1
        
        # Process each sensor value with streaming algorithms
        for sensor in EXPECTED_SENSOR_COLUMNS:
            value = sensor_data.get(sensor)
            
            if value is None or not isinstance(value, (int, float)):
                continue
            
            # Update streaming detector
            result = self.streaming_detector.update(sensor, float(value))
            
            # Check for anomaly
            if result['is_anomaly']:
                severity = 'CRITICAL' if abs(result['z_score']) > 4.0 else 'HIGH' if abs(result['z_score']) > 3.5 else 'MODERATE'
                
                anomalies.append({
                    'sensor': sensor,
                    'value': value,
                    'z_score': result['z_score'],
                    'severity': severity,
                    'type': 'ONLINE_ZSCORE',
                    'detection_method': 'STREAMING',
                    'message': f"{sensor} anomaly: value={value:.2f}, z-score={result['z_score']:.2f}",
                    'stats': result['stats']
                })
                
                self.detection_method_counts['STREAMING_ZSCORE'] += 1
            
            # Track drift events
            if result['drift_detected']:
                self.total_drift_events += 1
                anomalies.append({
                    'sensor': sensor,
                    'value': value,
                    'z_score': 0.0,
                    'severity': 'WARNING',
                    'type': 'CONCEPT_DRIFT',
                    'detection_method': 'ADWIN',
                    'message': f"{sensor} concept drift detected - distribution changed",
                    'stats': result['stats']
                })
                
                self.detection_method_counts['DRIFT_DETECTION'] += 1
            
            # Update correlation windows
            self.correlation_windows[sensor].append(value)
        
        # Multi-sensor correlation analysis
        correlation_anomalies = self._detect_correlation_anomalies(sensor_data)
        anomalies.extend(correlation_anomalies)
        
        if anomalies:
            self.total_anomalies += 1
        
        return anomalies
    
    def _detect_correlation_anomalies(self, sensor_data):
        """
        Detect anomalies based on multi-sensor correlations.
        Uses sliding windows for correlation computation.
        """
        anomalies = []
        
        # Check if tank level dropping but flow rate is normal
        lit101 = sensor_data.get('LIT 101')
        fit101 = sensor_data.get('FIT 101')
        
        if lit101 is not None and fit101 is not None:
            lit101_window = list(self.correlation_windows['LIT 101'])
            fit101_window = list(self.correlation_windows['FIT 101'])
            
            # Need at least 10 samples for correlation
            if len(lit101_window) >= 10 and len(fit101_window) >= 10:
                # Check if tank is draining rapidly but flow is stable
                recent_lit_trend = lit101_window[-5:] if len(lit101_window) >= 5 else lit101_window
                if len(recent_lit_trend) >= 3:
                    lit_change = recent_lit_trend[-1] - recent_lit_trend[0]
                    fit_std = np.std(fit101_window[-10:])
                    
                    # Anomaly: tank draining quickly but flow rate stable (possible leak)
                    if lit_change < -50 and fit_std < 0.1:
                        anomalies.append({
                            'sensor': 'LIT 101 + FIT 101',
                            'value': lit101,
                            'z_score': 0.0,
                            'severity': 'HIGH',
                            'type': 'CORRELATION_ANOMALY',
                            'detection_method': 'MULTI_SENSOR',
                            'message': f"Possible leak: Tank draining ({lit_change:.2f}) but flow stable",
                            'stats': {}
                        })
                        
                        self.detection_method_counts['CORRELATION'] += 1
        
        return anomalies
    
    def classify_attack_streaming(self, anomalies, sensor_data):
        """
        Classify attack type using streaming pattern recognition.
        Uses Count-Min Sketch for pattern frequency analysis.
        """
        if not anomalies:
            return None
        
        # Create pattern signature
        affected_sensors = sorted(set([a['sensor'] for a in anomalies]))
        pattern_sig = f"{len(affected_sensors)}_{'_'.join(affected_sensors[:3])}"
        
        # Update pattern frequency
        frequency = self.streaming_detector.update_pattern(pattern_sig)
        
        # Determine attack type based on affected sensors and patterns
        attack_code = 'UNKNOWN'
        confidence = 0.5
        
        # Rule-based classification using streaming statistics
        if len(affected_sensors) == 1:
            attack_code = 'SSCP'  # Single Stage Single Point
            confidence = 0.7
        elif len(affected_sensors) > 5:
            attack_code = 'MSMP'  # Multi Stage Multi Point
            confidence = 0.8
        elif any('FIT' in s for s in affected_sensors) and any('LIT' in s for s in affected_sensors):
            attack_code = 'CMRI'  # Complex MRI
            confidence = 0.75
        elif frequency > 5:
            attack_code = 'DOS'  # Repeated pattern suggests DOS
            confidence = 0.85
        else:
            attack_code = 'NMRI'  # Naive MRI
            confidence = 0.6
        
        return {
            'attack_code': attack_code,
            'attack_name': ATTACK_TYPE_MAP.get(list(ATTACK_TYPE_MAP.keys())[list(ATTACK_TYPE_MAP.values()).index(attack_code)] if attack_code in ATTACK_TYPE_MAP.values() else 0, attack_code),
            'confidence': confidence,
            'method': 'STREAMING_PATTERN',
            'affected_sensors': affected_sensors,
            'pattern_frequency': frequency,
            'num_sensors': len(affected_sensors)
        }
    
    def hybrid_classification(self, anomalies, sensor_data):
        """
        Combine streaming classification with ML models.
        """
        # Get streaming classification
        streaming_result = self.classify_attack_streaming(anomalies, sensor_data)
        
        if streaming_result is None:
            return None
        
        # If ML models available, get their predictions
        ml_prediction = None
        if self.fine_grained_model is not None:
            try:
                features = self._extract_features(sensor_data)
                if features is not None:
                    pred = self.fine_grained_model.predict([features])[0]
                    pred_proba = self.fine_grained_model.predict_proba([features])[0]
                    
                    ml_prediction = {
                        'attack_code': ATTACK_TYPE_MAP.get(pred, 'UNKNOWN'),
                        'confidence': float(max(pred_proba))
                    }
                    
                    # Update EMA of ML confidence
                    if 'ml_confidence' not in self.ml_confidence_ema:
                        self.ml_confidence_ema['ml_confidence'] = ml_prediction['confidence']
                    else:
                        self.ml_confidence_ema['ml_confidence'] = (
                            self.ema_alpha * ml_prediction['confidence'] + 
                            (1 - self.ema_alpha) * self.ml_confidence_ema['ml_confidence']
                        )
            except Exception as e:
                pass
        
        # Combine predictions
        if ml_prediction and ml_prediction['confidence'] > streaming_result['confidence']:
            return {
                **ml_prediction,
                'method': 'ML_HYBRID',
                'streaming_attack': streaming_result['attack_code'],
                'streaming_confidence': streaming_result['confidence'],
                'affected_sensors': streaming_result['affected_sensors']
            }
        else:
            return streaming_result
    
    def _extract_features(self, sensor_data):
        """Extract feature vector from sensor data"""
        features = []
        for sensor in EXPECTED_SENSOR_COLUMNS:
            val = sensor_data.get(sensor, 0.0)
            if isinstance(val, (int, float)):
                features.append(float(val))
            else:
                features.append(0.0)
        
        return features if len(features) == len(EXPECTED_SENSOR_COLUMNS) else None
    
    def write_to_influxdb(self, anomalies, classification, sensor_data, timestamp, write_api, org):
        """Write anomalies to InfluxDB with streaming metadata"""
        if not anomalies:
            return
        
        try:
            for anomaly in anomalies:
                point = Point("streaming_anomaly") \
                    .tag("attack_type", classification['attack_code'] if classification else 'UNKNOWN') \
                    .tag("severity", anomaly['severity']) \
                    .tag("sensor", anomaly['sensor']) \
                    .tag("anomaly_type", anomaly['type']) \
                    .tag("detection_method", anomaly.get('detection_method', 'STREAMING')) \
                    .time(timestamp, WritePrecision.NS) \
                    .field("value", float(anomaly['value'])) \
                    .field("z_score", float(anomaly.get('z_score', 0.0))) \
                    .field("message", anomaly['message'])
                
                if classification:
                    point.field("attack_confidence", float(classification['confidence']))
                    point.field("classification_method", classification['method'])
                    point.field("num_sensors_affected", classification.get('num_sensors', 0))
                    
                    if 'pattern_frequency' in classification:
                        point.field("pattern_frequency", int(classification['pattern_frequency']))
                
                # Add streaming statistics
                if 'stats' in anomaly and anomaly['stats']:
                    stats = anomaly['stats']
                    if 'mean' in stats:
                        point.field("sensor_mean", float(stats['mean']))
                    if 'std' in stats:
                        point.field("sensor_std", float(stats['std']))
                    if 'drift_events' in stats:
                        point.field("drift_events", int(stats['drift_events']))
                
                write_api.write(bucket=ANOMALY_BUCKET, org=org, record=point)
        
        except Exception as e:
            print(f"[ERROR] Failed to write to InfluxDB: {e}")


def main():
    """Main streaming detection loop"""
    print(f"\n{'='*80}")
    print(f"NT-SCADA FULLY STREAMING ANOMALY DETECTION")
    print(f"Real-Time: Welford | ADWIN | Online Z-Score | Pattern Mining")
    print(f"{'='*80}\n")
    
    # Initialize detector
    detector = FullyStreamingDetector(
        INFLUXDB_URL,
        INFLUXDB_TOKEN,
        INFLUXDB_ORG,
        INFLUXDB_BUCKET
    )
    
    # Setup writer
    write_api = detector.client.write_api(write_options=SYNCHRONOUS)
    
    print(f"[DETECTION] Starting fully streaming detection...")
    print(f"[DETECTION] NO BATCH LEARNING - All statistics computed online!")
    print(f"[DETECTION] Polling interval: {POLLING_INTERVAL} seconds\n")
    
    detection_count = 0
    
    try:
        while True:
            # Query recent data
            query = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
              |> range(start: -{POLLING_INTERVAL * 2}s)
              |> filter(fn: (r) => r._measurement == "sensor_data")
              |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
              |> limit(n: 10)
            '''
            
            try:
                result = detector.query_api.query(query=query)
                
                for table in result:
                    for record in table.records:
                        timestamp = record.get_time()
                        
                        # Skip if already processed
                        if detector.last_processed_time and timestamp <= detector.last_processed_time:
                            continue
                        
                        detector.last_processed_time = timestamp
                        sensor_data = record.values
                        
                        # STREAMING DETECTION
                        anomalies = detector.detect_streaming(sensor_data)
                        
                        if anomalies:
                            detection_count += 1
                            
                            # Streaming classification
                            classification = detector.hybrid_classification(anomalies, sensor_data)
                            
                            # Write to InfluxDB
                            detector.write_to_influxdb(
                                anomalies,
                                classification,
                                sensor_data,
                                timestamp,
                                write_api,
                                INFLUXDB_ORG
                            )
                            
                            # Log
                            if classification:
                                print(f"[ANOMALY #{detection_count}] {timestamp}")
                                print(f"  Attack: {classification['attack_code']} "
                                      f"(Confidence: {classification['confidence']:.2%})")
                                print(f"  Method: {classification['method']}")
                                print(f"  Sensors: {len(anomalies)} affected")
                                print()
            
            except Exception as e:
                print(f"[ERROR] Query error: {e}")
            
            # Statistics
            if detection_count > 0 and detection_count % 25 == 0:
                print(f"\n{'='*60}")
                print(f"STREAMING STATISTICS (After {detection_count} anomalies)")
                print(f"{'='*60}")
                print(f"Total samples: {detector.total_samples}")
                print(f"Total anomalies: {detector.total_anomalies}")
                print(f"Total drift events: {detector.total_drift_events}")
                print(f"Detection rate: {(detector.total_anomalies/detector.total_samples*100):.2f}%")
                print(f"\nDetection Methods:")
                for method, count in detector.detection_method_counts.items():
                    print(f"  {method}: {count}")
                print(f"{'='*60}\n")
            
            time.sleep(POLLING_INTERVAL)
    
    except KeyboardInterrupt:
        print(f"\n[SHUTDOWN] Stopping detection...")
        print(f"[STATS] Total anomalies detected: {detection_count}")
        detector.client.close()


if __name__ == "__main__":
    main()
