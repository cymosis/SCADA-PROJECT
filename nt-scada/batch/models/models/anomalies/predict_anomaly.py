"""
NT-SCADA Enhanced Anomaly Detection System - WITH TRAINED ML MODELS
Combines: Z-Score + Rule-Based + Pattern Matching + TRAINED ML MODELS

Detection Capabilities:
1. Binary Detection: Normal vs. Anomaly (Z-score + Rules + ML Model)
2. Fine-Grained Classification: Specific attack types (Pattern + ML Model)
3. Multi-sensor correlation analysis
4. ML-based validation and confidence boosting

ENHANCED VERSION: Integrates trained ML models with existing hybrid approach
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
import warnings
warnings.filterwarnings('ignore')

# Configuration
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'mytoken')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'scada')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', 'normal_data')
ANOMALY_BUCKET = os.getenv('ANOMALY_BUCKET', 'anomaly_data')
POLLING_INTERVAL = int(os.getenv('POLLING_INTERVAL', '5'))

# Model paths
BINARY_MODEL_PATH = os.getenv('BINARY_MODEL_PATH', '/app/models/binary_classifier.pkl')
FINE_GRAINED_MODEL_PATH = os.getenv('FINE_GRAINED_MODEL_PATH', '/app/models/fine_grained_classifier.pkl')

# Z-Score thresholds
Z_SCORE_THRESHOLD = float(os.getenv('Z_SCORE_THRESHOLD', '3.0'))
Z_SCORE_MODERATE = 2.0
Z_SCORE_SEVERE = 4.0

# Baseline learning period
BASELINE_HOURS = int(os.getenv('BASELINE_HOURS', '999999'))

# Attack pattern detection window
ATTACK_WINDOW_SIZE = 10

# Track last processed timestamp
LAST_PROCESSED_TIME = None

# -----------------------------
# SCADA Domain Rules
# -----------------------------
SCADA_RULES = {
    # Tank Levels
    'LIT 101': {'min': 0, 'max': 1000, 'critical_low': 200, 'critical_high': 900},
    'LIT 301': {'min': 0, 'max': 1200, 'critical_low': 200, 'critical_high': 1100},
    'LIT 401': {'min': 0, 'max': 1200, 'critical_low': 200, 'critical_high': 1100},
    
    # pH Levels
    'AIT 202': {'min': 0, 'max': 14, 'critical_low': 5, 'critical_high': 9},
    'AIT 402': {'min': 0, 'max': 14, 'critical_low': 5, 'critical_high': 9},
    
    # Flow rates
    'FIT 101': {'min': 0, 'max': 3, 'critical_low': 0.5, 'critical_high': 2.5},
    'FIT 201': {'min': 0, 'max': 3, 'critical_low': 0.5, 'critical_high': 2.5},
    'FIT 301': {'min': 0, 'max': 3, 'critical_low': 0.5, 'critical_high': 2.5},
    'FIT 401': {'min': 0, 'max': 3, 'critical_low': 0.5, 'critical_high': 2.5},
    'FIT 501': {'min': 0, 'max': 3, 'critical_low': 0.5, 'critical_high': 2.5},
    'FIT 502': {'min': 0, 'max': 3, 'critical_low': 0.5, 'critical_high': 2.5},
    
    # Pressure
    'DPIT 301': {'min': 0, 'max': 10, 'critical_low': 0.5, 'critical_high': 8},
    
    # Conductivity
    'AIT 201': {'min': 0, 'max': 2000, 'critical_low': 50, 'critical_high': 1500},
    'AIT 203': {'min': 0, 'max': 1000, 'critical_low': 100, 'critical_high': 900},
    
    # Temperature ranges
    'AIT 301': {'min': -10, 'max': 100, 'critical_low': 5, 'critical_high': 60},
    'AIT 302': {'min': -10, 'max': 100, 'critical_low': 5, 'critical_high': 60},
    'AIT 303': {'min': -10, 'max': 100, 'critical_low': 5, 'critical_high': 60},
    'AIT 401': {'min': -10, 'max': 100, 'critical_low': 5, 'critical_high': 60},
    'AIT 402': {'min': -10, 'max': 100, 'critical_low': 5, 'critical_high': 60},
    'AIT 501': {'min': -10, 'max': 100, 'critical_low': 5, 'critical_high': 60},
    'AIT 502': {'min': -10, 'max': 100, 'critical_low': 5, 'critical_high': 60},
    'AIT 503': {'min': -10, 'max': 100, 'critical_low': 5, 'critical_high': 60},
    'AIT 504': {'min': -10, 'max': 100, 'critical_low': 5, 'critical_high': 60},
}

# Pump state rules
PUMP_STATES = {
    'P1_STATE': [0, 1, 2, 3],
    'P2_STATE': [0, 1, 2, 3],
    'P3_STATE': [0, 1, 2, 3],
    'P4_STATE': [0, 1, 2, 3],
    'P5_STATE': [0, 1, 2, 3],
    'P6_STATE': [0, 1, 2, 3],
}

# Expected sensor columns (must match training data)
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

# Attack type mapping for fine-grained model
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

# -----------------------------
# Attack Pattern Definitions
# -----------------------------
class AttackPattern:
    """Define attack type patterns for fine-grained classification"""
    
    NMRI = {
        'name': 'Naive Malicious Response Injection',
        'code': 'NMRI',
        'description': 'Wrong actuator commands causing process disruption',
    }
    
    CMRI = {
        'name': 'Complex Malicious Response Injection',
        'code': 'CMRI',
        'description': 'Coordinated multi-actuator attack',
    }
    
    RECONNAISSANCE = {
        'name': 'Reconnaissance Attack',
        'code': 'RECON',
        'description': 'Attacker probing system for vulnerabilities',
    }
    
    DOS = {
        'name': 'Denial of Service',
        'code': 'DOS',
        'description': 'Resource exhaustion or service disruption',
    }
    
    SSCP = {
        'name': 'Single Stage Single Point',
        'code': 'SSCP',
        'description': 'Attack on single sensor/actuator',
    }
    
    SSMP = {
        'name': 'Single Stage Multi Point',
        'code': 'SSMP',
        'description': 'Attack on multiple points in same stage',
    }
    
    MSCP = {
        'name': 'Multi Stage Single Point',
        'code': 'MSCP',
        'description': 'Same attack across multiple stages',
    }
    
    MSMP = {
        'name': 'Multi Stage Multi Point',
        'code': 'MSMP',
        'description': 'Coordinated attack across system',
    }

# -----------------------------
# Enhanced Hybrid Detector with ML
# -----------------------------
class EnhancedHybridDetector:
    """
    4-Layer Hybrid Anomaly Detection:
    Layer 1: Statistical (Z-Score)
    Layer 2: Rule-Based (Domain Rules)
    Layer 3: Machine Learning (Trained Models)
    Layer 4: Pattern Matching (Attack Classification)
    """
    
    def __init__(self, influx_url, token, org, bucket):
        self.influx_url = influx_url
        self.token = token
        self.org = org
        self.bucket = bucket
        
        # InfluxDB connection
        self.client = InfluxDBClient(url=influx_url, token=token, org=org)
        self.query_api = self.client.query_api()
        
        # Baseline statistics
        self.baseline_stats = {}
        self.baseline_ready = False
        
        # Historical data for pattern analysis
        self.sensor_history = defaultdict(lambda: deque(maxlen=ATTACK_WINDOW_SIZE))
        self.anomaly_history = deque(maxlen=ATTACK_WINDOW_SIZE)
        
        # Load trained ML models
        self.binary_model = None
        self.fine_grained_model = None
        self.ml_models_loaded = False
        self._load_ml_models()
        
        # Counters
        self.total_anomalies = 0
        self.total_classified = 0
        self.attack_type_counts = defaultdict(int)
        self.anomaly_types = defaultdict(int)
        self.detection_method_counts = defaultdict(int)
        
        # Track last processed timestamp
        self.last_processed_time = None
        
        print(f"[LOG] EnhancedHybridDetector initialized")
        print(f"[LOG] 4-Layer Detection: Z-Score + Rules + ML Models + Pattern Matching")
        if self.ml_models_loaded:
            print(f"[LOG] ✓ ML Models loaded successfully")
        else:
            print(f"[LOG] ⚠ ML Models not loaded - using 3-layer detection only")
        print(f"[LOG] Z-Score threshold: {Z_SCORE_THRESHOLD} sigma")
        print(f"[LOG] Pattern analysis window: {ATTACK_WINDOW_SIZE} records")
    
    def _load_ml_models(self):
        """Load trained ML models"""
        try:
            # Load binary classification model
            if os.path.exists(BINARY_MODEL_PATH):
                self.binary_model = joblib.load(BINARY_MODEL_PATH)
                print(f"[ML] ✓ Binary classifier loaded from {BINARY_MODEL_PATH}")
            else:
                print(f"[ML] ⚠ Binary model not found at {BINARY_MODEL_PATH}")
            
            # Load fine-grained classification model
            if os.path.exists(FINE_GRAINED_MODEL_PATH):
                self.fine_grained_model = joblib.load(FINE_GRAINED_MODEL_PATH)
                print(f"[ML] ✓ Fine-grained classifier loaded from {FINE_GRAINED_MODEL_PATH}")
            else:
                print(f"[ML] ⚠ Fine-grained model not found at {FINE_GRAINED_MODEL_PATH}")
            
            # Set flag if at least one model loaded
            self.ml_models_loaded = (self.binary_model is not None or 
                                     self.fine_grained_model is not None)
            
        except Exception as e:
            print(f"[ML] ✗ Error loading models: {e}")
            self.ml_models_loaded = False
    
    def _prepare_features_for_ml(self, sensor_data):
        """Prepare features in correct order for ML model"""
        features = []
        for col in EXPECTED_SENSOR_COLUMNS:
            value = sensor_data.get(col, 0)
            # Handle non-numeric values
            if not isinstance(value, (int, float)):
                value = 0
            features.append(float(value))
        return np.array(features).reshape(1, -1)
    
    def learn_baseline(self):
        """Learn normal behavior from historical data"""
        print(f"\n[BASELINE] Learning from all available data...")
        
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: 0)
          |> filter(fn: (r) => r._measurement == "sensor_data")
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> limit(n: 5000)
        '''
        
        try:
            result = self.query_api.query(query=query)
            records = []
            for table in result:
                for record in table.records:
                    records.append(record.values)
            
            if not records:
                print("[BASELINE] No historical data. Using defaults.")
                return False
            
            df = pd.DataFrame(records)
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            for col in numeric_cols:
                if col.startswith('_') or col in ['table', 'result']:
                    continue
                
                values = df[col].dropna()
                if len(values) > 10:
                    self.baseline_stats[col] = {
                        'mean': float(values.mean()),
                        'std': float(values.std() + 1e-8),
                        'min': float(values.min()),
                        'max': float(values.max()),
                        'median': float(values.median()),
                        'q25': float(values.quantile(0.25)),
                        'q75': float(values.quantile(0.75)),
                    }
            
            print(f"[BASELINE] ✓ Learned {len(self.baseline_stats)} sensors from {len(records)} records")
            self.baseline_ready = True
            return True
            
        except Exception as e:
            print(f"[BASELINE] Error: {e}")
            return False
    
    def calculate_z_score(self, sensor_name, value):
        """Calculate Z-score for statistical detection"""
        if sensor_name not in self.baseline_stats:
            return 0.0
        
        stats = self.baseline_stats[sensor_name]
        if stats['std'] == 0:
            return 0.0
        
        return (value - stats['mean']) / stats['std']
    
    def check_rule_violations(self, sensor_data):
        """Check domain rule violations (Layer 2)"""
        violations = []
        
        for sensor, value in sensor_data.items():
            if sensor in SCADA_RULES:
                rules = SCADA_RULES[sensor]
                
                # Check hard limits
                if value > rules['max']:
                    violations.append({
                        'sensor': sensor,
                        'type': 'OUT_OF_RANGE',
                        'value': value,
                        'z_score': 0,
                        'severity': 'CRITICAL',
                        'message': f"{sensor} above maximum: {value:.2f} > {rules['max']}",
                        'detection_method': 'RULE_BASED'
                    })
                elif value < rules['min']:
                    violations.append({
                        'sensor': sensor,
                        'type': 'OUT_OF_RANGE',
                        'value': value,
                        'z_score': 0,
                        'severity': 'CRITICAL',
                        'message': f"{sensor} below minimum: {value:.2f} < {rules['min']}",
                        'detection_method': 'RULE_BASED'
                    })
                # Check critical ranges
                elif 'critical_high' in rules and value > rules['critical_high']:
                    violations.append({
                        'sensor': sensor,
                        'type': 'CRITICAL_HIGH',
                        'value': value,
                        'z_score': 0,
                        'severity': 'HIGH',
                        'message': f"{sensor} critically high: {value:.2f}",
                        'detection_method': 'RULE_BASED'
                    })
                elif 'critical_low' in rules and value < rules['critical_low']:
                    violations.append({
                        'sensor': sensor,
                        'type': 'CRITICAL_LOW',
                        'value': value,
                        'z_score': 0,
                        'severity': 'HIGH',
                        'message': f"{sensor} critically low: {value:.2f}",
                        'detection_method': 'RULE_BASED'
                    })
            
            # Check pump states
            if sensor in PUMP_STATES:
                if value not in PUMP_STATES[sensor]:
                    violations.append({
                        'sensor': sensor,
                        'type': 'INVALID_STATE',
                        'value': value,
                        'z_score': 0,
                        'severity': 'CRITICAL',
                        'message': f"{sensor} invalid state: {value}",
                        'detection_method': 'RULE_BASED'
                    })
        
        return violations
    
    def detect_with_ml_binary(self, sensor_data):
        """Binary detection using ML model (Layer 3A)"""
        if not self.binary_model:
            return None
        
        try:
            # Prepare features
            features = self._prepare_features_for_ml(sensor_data)
            
            # Predict
            prediction = self.binary_model.predict(features)[0]
            probabilities = self.binary_model.predict_proba(features)[0]
            
            # prediction: 0=normal, 1=attack
            if prediction == 1:
                return {
                    'is_anomaly': True,
                    'ml_confidence': float(probabilities[1]),
                    'method': 'ML_BINARY',
                    'model_prediction': int(prediction)
                }
            else:
                return {
                    'is_anomaly': False,
                    'ml_confidence': float(probabilities[0]),
                    'method': 'ML_BINARY',
                    'model_prediction': int(prediction)
                }
        
        except Exception as e:
            print(f"[ML] Binary prediction error: {e}")
            return None
    
    def classify_with_ml_fine_grained(self, sensor_data):
        """Fine-grained classification using ML model (Layer 3B)"""
        if not self.fine_grained_model:
            return None
        
        try:
            # Prepare features
            features = self._prepare_features_for_ml(sensor_data)
            
            # Predict
            prediction = self.fine_grained_model.predict(features)[0]
            probabilities = self.fine_grained_model.predict_proba(features)[0]
            
            # Get attack type
            attack_type_code = ATTACK_TYPE_MAP.get(prediction, 'UNKNOWN')
            confidence = float(probabilities[prediction])
            
            return {
                'attack_type_code': attack_type_code,
                'ml_confidence': confidence,
                'method': 'ML_FINE_GRAINED',
                'model_prediction': int(prediction)
            }
        
        except Exception as e:
            print(f"[ML] Fine-grained prediction error: {e}")
            return None
    
    def classify_attack_pattern(self, anomalies, sensor_data):
        """Pattern-based attack classification (Layer 4)"""
        if not anomalies:
            return None
        
        affected_sensors = [a['sensor'] for a in anomalies]
        
        # Identify actuator anomalies
        actuator_keywords = ['MV', 'P', 'UV']
        actuator_anomalies = [s for s in affected_sensors 
                              if any(kw in s for kw in actuator_keywords)]
        
        # Identify affected stages
        stages_affected = set()
        for sensor in affected_sensors:
            if any(char.isdigit() for char in sensor):
                stage = ''.join(filter(str.isdigit, sensor))[0] if sensor else '0'
                stages_affected.add(stage)
        
        num_stages = len(stages_affected)
        num_affected = len(set(affected_sensors))
        
        # Count severity
        severe_count = sum(1 for a in anomalies if a['severity'] == 'CRITICAL')
        high_count = sum(1 for a in anomalies if a['severity'] == 'HIGH')
        
        # Pattern matching logic
        attack_class = None
        confidence = 0.0
        reasoning = []
        
        # DOS - All sensors constant
        if self._check_dos_pattern():
            attack_class = AttackPattern.DOS
            confidence = 0.95
            reasoning.append("All sensors showing no variation")
        
        # NMRI - Wrong actuator states
        elif len(actuator_anomalies) > 0 and len(actuator_anomalies) <= 2:
            attack_class = AttackPattern.NMRI
            confidence = 0.85
            reasoning.append(f"{len(actuator_anomalies)} actuator(s) in wrong state")
        
        # CMRI - Multiple actuators compromised
        elif len(actuator_anomalies) > 2:
            attack_class = AttackPattern.CMRI
            confidence = 0.90
            reasoning.append(f"{len(actuator_anomalies)} actuators coordinated attack")
        
        # MSMP - Multi-Stage Multi-Point
        elif num_stages >= 3 and num_affected >= 5:
            attack_class = AttackPattern.MSMP
            confidence = 0.92
            reasoning.append(f"{num_stages} stages, {num_affected} sensors affected")
        
        # MSCP - Multi-Stage Single-Point
        elif num_stages >= 2 and num_affected <= 2:
            attack_class = AttackPattern.MSCP
            confidence = 0.80
            reasoning.append(f"Same sensor type across {num_stages} stages")
        
        # SSMP - Single-Stage Multi-Point
        elif num_stages == 1 and num_affected >= 3:
            attack_class = AttackPattern.SSMP
            confidence = 0.85
            reasoning.append(f"{num_affected} sensors in single stage")
        
        # SSCP - Single-Stage Single-Point
        elif num_stages == 1 and num_affected <= 2:
            attack_class = AttackPattern.SSCP
            confidence = 0.75
            reasoning.append(f"Isolated anomaly in single stage")
        
        # RECON - Reconnaissance
        elif self._check_recon_pattern():
            attack_class = AttackPattern.RECONNAISSANCE
            confidence = 0.70
            reasoning.append("Rapid sequential sensor access pattern")
        
        # Default
        else:
            attack_class = AttackPattern.SSCP
            confidence = 0.60
            reasoning.append("Single point anomaly (default)")
        
        return {
            'attack_type': attack_class,
            'attack_name': attack_class['name'],
            'attack_code': attack_class['code'],
            'pattern_confidence': confidence,
            'affected_sensors': affected_sensors,
            'affected_stages': list(stages_affected),
            'num_stages': num_stages,
            'num_sensors': num_affected,
            'severity_critical': severe_count,
            'severity_high': high_count,
            'reasoning': reasoning,
            'detection_method': 'PATTERN_MATCHING'
        }
    
    def _check_dos_pattern(self):
        """Check for DoS pattern"""
        if len(self.sensor_history) < 5:
            return False
        
        constant_sensors = 0
        for sensor, history in self.sensor_history.items():
            if len(history) >= 5:
                values = list(history)
                if len(set(values)) == 1:
                    constant_sensors += 1
        
        return constant_sensors >= 5
    
    def _check_recon_pattern(self):
        """Check for reconnaissance pattern"""
        if len(self.anomaly_history) >= 5:
            recent_anomalies = list(self.anomaly_history)[-5:]
            return len(recent_anomalies) >= 3
        return False
    
    def detect_anomalies(self, sensor_data):
        """
        Main 4-layer detection logic:
        1. Z-Score (statistical)
        2. Rules (domain knowledge)
        3. ML Models (trained classifiers)
        4. Pattern Matching (attack taxonomy)
        """
        anomalies = []
        z_scores = {}
        
        # Update sensor history
        for sensor, value in sensor_data.items():
            if isinstance(value, (int, float)):
                self.sensor_history[sensor].append(value)
        
        # LAYER 1: Z-Score Analysis
        if self.baseline_ready:
            for sensor, value in sensor_data.items():
                if isinstance(value, (int, float)) and sensor in self.baseline_stats:
                    z = self.calculate_z_score(sensor, value)
                    z_scores[sensor] = z
                    
                    if abs(z) > Z_SCORE_SEVERE:
                        anomalies.append({
                            'sensor': sensor,
                            'type': 'Z_SCORE_SEVERE',
                            'value': value,
                            'z_score': z,
                            'severity': 'CRITICAL',
                            'message': f"{sensor} severe deviation: z={z:.2f}",
                            'detection_method': 'Z_SCORE'
                        })
                        self.detection_method_counts['Z_SCORE'] += 1
                    elif abs(z) > Z_SCORE_THRESHOLD:
                        anomalies.append({
                            'sensor': sensor,
                            'type': 'Z_SCORE_HIGH',
                            'value': value,
                            'z_score': z,
                            'severity': 'HIGH',
                            'message': f"{sensor} significant deviation: z={z:.2f}",
                            'detection_method': 'Z_SCORE'
                        })
                        self.detection_method_counts['Z_SCORE'] += 1
                    elif abs(z) > Z_SCORE_MODERATE:
                        anomalies.append({
                            'sensor': sensor,
                            'type': 'Z_SCORE_MODERATE',
                            'value': value,
                            'z_score': z,
                            'severity': 'MEDIUM',
                            'message': f"{sensor} moderate deviation: z={z:.2f}",
                            'detection_method': 'Z_SCORE'
                        })
                        self.detection_method_counts['Z_SCORE'] += 1
        
        # LAYER 2: Rule-Based Detection
        rule_violations = self.check_rule_violations(sensor_data)
        anomalies.extend(rule_violations)
        self.detection_method_counts['RULE_BASED'] += len(rule_violations)
        
        # LAYER 3: ML-Based Detection (Binary)
        ml_binary_result = self.detect_with_ml_binary(sensor_data)
        
        if ml_binary_result and ml_binary_result['is_anomaly']:
            # ML detected an anomaly
            anomalies.append({
                'sensor': 'SYSTEM',
                'type': 'ML_BINARY_DETECTION',
                'value': ml_binary_result['ml_confidence'],
                'z_score': 0,
                'severity': 'HIGH' if ml_binary_result['ml_confidence'] > 0.8 else 'MEDIUM',
                'message': f"ML binary model detected anomaly (confidence: {ml_binary_result['ml_confidence']:.2%})",
                'detection_method': 'ML_BINARY'
            })
            self.detection_method_counts['ML_BINARY'] += 1
        
        # LAYER 4A: Multi-Sensor Correlation
        moderate_deviations = [s for s, z in z_scores.items() 
                              if Z_SCORE_MODERATE < abs(z) < Z_SCORE_THRESHOLD]
        if len(moderate_deviations) >= 3:
            anomalies.append({
                'sensor': 'MULTIPLE',
                'type': 'CORRELATED_DEVIATION',
                'value': len(moderate_deviations),
                'z_score': 0,
                'severity': 'HIGH',
                'message': f"Multiple sensors deviating: {', '.join(moderate_deviations[:5])}",
                'detection_method': 'CORRELATION'
            })
            self.detection_method_counts['CORRELATION'] += 1
        
        # Update anomaly history
        if anomalies:
            self.anomaly_history.append(len(anomalies))
        
        return anomalies, ml_binary_result
    
    def create_unified_classification(self, pattern_result, ml_fine_grained_result):
        """
        Combine pattern-based and ML-based classifications
        Returns unified result with highest confidence
        """
        if not pattern_result and not ml_fine_grained_result:
            return None
        
        # If only one method available, use that
        if not ml_fine_grained_result:
            return {
                'attack_code': pattern_result['attack_code'],
                'attack_name': pattern_result['attack_name'],
                'confidence': pattern_result['pattern_confidence'],
                'method': 'PATTERN_ONLY',
                'ml_attack_code': None,
                'ml_confidence': 0.0,
                'pattern_attack_code': pattern_result['attack_code'],
                'pattern_confidence': pattern_result['pattern_confidence']
            }
        
        if not pattern_result:
            return {
                'attack_code': ml_fine_grained_result['attack_type_code'],
                'attack_name': ml_fine_grained_result['attack_type_code'],
                'confidence': ml_fine_grained_result['ml_confidence'],
                'method': 'ML_ONLY',
                'ml_attack_code': ml_fine_grained_result['attack_type_code'],
                'ml_confidence': ml_fine_grained_result['ml_confidence'],
                'pattern_attack_code': None,
                'pattern_confidence': 0.0
            }
        
        # Both available - combine intelligently
        ml_conf = ml_fine_grained_result['ml_confidence']
        pattern_conf = pattern_result['pattern_confidence']
        
        # If both agree, boost confidence
        if ml_fine_grained_result['attack_type_code'] == pattern_result['attack_code']:
            combined_confidence = (ml_conf + pattern_conf) / 2 * 1.1  # 10% boost
            combined_confidence = min(combined_confidence, 0.99)  # Cap at 99%
            
            return {
                'attack_code': pattern_result['attack_code'],
                'attack_name': pattern_result['attack_name'],
                'confidence': combined_confidence,
                'method': 'HYBRID_AGREEMENT',
                'ml_attack_code': ml_fine_grained_result['attack_type_code'],
                'ml_confidence': ml_conf,
                'pattern_attack_code': pattern_result['attack_code'],
                'pattern_confidence': pattern_conf,
                'agreement': True
            }
        else:
            # Disagree - use highest confidence
            if ml_conf > pattern_conf:
                return {
                    'attack_code': ml_fine_grained_result['attack_type_code'],
                    'attack_name': ml_fine_grained_result['attack_type_code'],
                    'confidence': ml_conf,
                    'method': 'ML_PREFERRED',
                    'ml_attack_code': ml_fine_grained_result['attack_type_code'],
                    'ml_confidence': ml_conf,
                    'pattern_attack_code': pattern_result['attack_code'],
                    'pattern_confidence': pattern_conf,
                    'agreement': False
                }
            else:
                return {
                    'attack_code': pattern_result['attack_code'],
                    'attack_name': pattern_result['attack_name'],
                    'confidence': pattern_conf,
                    'method': 'PATTERN_PREFERRED',
                    'ml_attack_code': ml_fine_grained_result['attack_type_code'],
                    'ml_confidence': ml_conf,
                    'pattern_attack_code': pattern_result['attack_code'],
                    'pattern_confidence': pattern_conf,
                    'agreement': False
                }
    
    def write_to_influxdb(self, anomalies, classification, sensor_data, timestamp, write_api, org):
        """Write detected anomalies and classification to InfluxDB"""
        if not anomalies:
            return
        
        try:
            # Write each anomaly as a separate point
            for anomaly in anomalies:
                point = Point("anomaly_alert") \
                    .tag("attack_type", classification['attack_code'] if classification else 'UNKNOWN') \
                    .tag("attack_name", classification['attack_name'] if classification else 'Unknown') \
                    .tag("severity", anomaly['severity']) \
                    .tag("sensor", anomaly['sensor']) \
                    .tag("anomaly_type", anomaly['type']) \
                    .tag("detection_method", anomaly.get('detection_method', 'UNKNOWN')) \
                    .time(timestamp, WritePrecision.NS) \
                    .field("value", float(anomaly['value'])) \
                    .field("z_score", float(anomaly['z_score'])) \
                    .field("message", anomaly['message'])
                
                # Add classification fields
                if classification:
                    point.field("attack_confidence", float(classification['confidence']))
                    point.field("classification_method", classification['method'])
                    point.field("num_sensors_affected", len(set([a['sensor'] for a in anomalies])))
                    
                    # Add ML vs Pattern comparison fields
                    if 'ml_confidence' in classification:
                        point.field("ml_confidence", float(classification['ml_confidence']))
                    if 'pattern_confidence' in classification:
                        point.field("pattern_confidence", float(classification['pattern_confidence']))
                    if 'ml_attack_code' in classification and classification['ml_attack_code']:
                        point.tag("ml_attack_type", classification['ml_attack_code'])
                    if 'pattern_attack_code' in classification and classification['pattern_attack_code']:
                        point.tag("pattern_attack_type", classification['pattern_attack_code'])
                    if 'agreement' in classification:
                        point.field("ml_pattern_agreement", classification['agreement'])
                
                write_api.write(bucket=ANOMALY_BUCKET, org=org, record=point)
            
            self.total_anomalies += 1
            
        except Exception as e:
            print(f"[ERROR] Failed to write to InfluxDB: {e}")

# Continue with main detection loop...
def main():
    """Main detection loop - reads from InfluxDB, uses 4-layer detection"""
    print(f"\n{'='*80}")
    print(f"NT-SCADA ENHANCED ANOMALY DETECTION SYSTEM")
    print(f"4-Layer Hybrid: Z-Score + Rules + ML Models + Pattern Matching")
    print(f"{'='*80}\n")
    
    # Initialize detector
    detector = EnhancedHybridDetector(
        INFLUXDB_URL,
        INFLUXDB_TOKEN,
        INFLUXDB_ORG,
        INFLUXDB_BUCKET
    )
    
    # Learn baseline
    if not detector.learn_baseline():
        print("[WARNING] Baseline learning failed. Detection may be less accurate.")
    
    # Setup InfluxDB writer
    write_api = detector.client.write_api(write_options=SYNCHRONOUS)
    
    print(f"\n[DETECTION] Starting 4-layer anomaly detection...")
    print(f"[DETECTION] Polling interval: {POLLING_INTERVAL} seconds")
    print(f"[DETECTION] Reading from: {INFLUXDB_BUCKET}")
    print(f"[DETECTION] Writing to: {ANOMALY_BUCKET}\n")
    
    detection_count = 0
    
    try:
        while True:
            # Query recent data from InfluxDB
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
                        
                        # 4-LAYER DETECTION
                        anomalies, ml_binary_result = detector.detect_anomalies(sensor_data)
                        
                        if anomalies:
                            detection_count += 1
                            
                            # Pattern-based classification (Layer 4)
                            pattern_classification = detector.classify_attack_pattern(anomalies, sensor_data)
                            
                            # ML fine-grained classification (Layer 3B)
                            ml_fine_grained = detector.classify_with_ml_fine_grained(sensor_data)
                            
                            # Combine classifications
                            unified_classification = detector.create_unified_classification(
                                pattern_classification,
                                ml_fine_grained
                            )
                            
                            # Write to InfluxDB
                            detector.write_to_influxdb(
                                anomalies,
                                unified_classification,
                                sensor_data,
                                timestamp,
                                write_api,
                                INFLUXDB_ORG
                            )
                            
                            # Log detection
                            if unified_classification:
                                print(f"[ANOMALY #{detection_count}] {timestamp}")
                                print(f"  Attack: {unified_classification['attack_code']} "
                                      f"(Confidence: {unified_classification['confidence']:.2%})")
                                print(f"  Method: {unified_classification['method']}")
                                print(f"  Sensors: {len(anomalies)} affected")
                                if 'agreement' in unified_classification:
                                    agree_str = "✓ AGREE" if unified_classification['agreement'] else "✗ DISAGREE"
                                    print(f"  ML vs Pattern: {agree_str}")
                                print()
                
            except Exception as e:
                print(f"[ERROR] Query error: {e}")
            
            # Print statistics periodically
            if detection_count > 0 and detection_count % 50 == 0:
                print(f"\n{'='*60}")
                print(f"DETECTION STATISTICS (After {detection_count} anomalies)")
                print(f"{'='*60}")
                print(f"Detection Methods:")
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
