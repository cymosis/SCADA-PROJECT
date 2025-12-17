"""
NT-SCADA Advanced Anomaly Detection System
Combines: Z-Score + Rule-Based + Fine-Grained Attack Classification

Detection Capabilities:
1. Binary Detection: Normal vs. Anomaly
2. Fine-Grained Classification: Specific attack types
3. Multi-sensor correlation analysis

Methods:
- Z-Score statistical analysis
- Domain rule violations
- Attack pattern recognition

MODIFIED: Works with historical data (2019-2020 timestamps)
"""

import os
import time
import pandas as pd
import numpy as np
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

# Z-Score thresholds
Z_SCORE_THRESHOLD = float(os.getenv('Z_SCORE_THRESHOLD', '3.0'))
Z_SCORE_MODERATE = 2.0
Z_SCORE_SEVERE = 4.0

# Baseline learning period - use all data since timestamps are historical
BASELINE_HOURS = int(os.getenv('BASELINE_HOURS', '999999'))  # Large number to get all data

# Attack pattern detection window
ATTACK_WINDOW_SIZE = 10  # Last 10 readings for pattern analysis

# Track last processed timestamp to avoid reprocessing
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

# -----------------------------
# Attack Pattern Definitions
# -----------------------------
class AttackPattern:
    """Define attack type patterns for fine-grained classification"""
    
    NMRI = {
        'name': 'Naive Malicious Response Injection',
        'code': 'NMRI',
        'description': 'Wrong actuator commands causing process disruption',
        'indicators': [
            'valve_wrong_state',
            'pump_state_mismatch',
            'actuator_anomaly'
        ]
    }
    
    CMRI = {
        'name': 'Complex Malicious Response Injection',
        'code': 'CMRI',
        'description': 'Coordinated multi-actuator attack',
        'indicators': [
            'multiple_actuator_anomalies',
            'coordinated_valve_changes',
            'process_state_inconsistency'
        ]
    }
    
    RECONNAISSANCE = {
        'name': 'Reconnaissance Attack',
        'code': 'RECON',
        'description': 'Attacker probing system for vulnerabilities',
        'indicators': [
            'rapid_sensor_changes',
            'unusual_query_pattern',
            'sequential_sensor_access'
        ]
    }
    
    DOS = {
        'name': 'Denial of Service',
        'code': 'DOS',
        'description': 'Resource exhaustion or service disruption',
        'indicators': [
            'sensor_flatline',
            'no_variation',
            'all_sensors_constant'
        ]
    }
    
    SSCP = {
        'name': 'Single Stage Single Point',
        'code': 'SSCP',
        'description': 'Attack on single sensor/actuator',
        'indicators': [
            'single_sensor_extreme_deviation',
            'isolated_anomaly'
        ]
    }
    
    SSMP = {
        'name': 'Single Stage Multi Point',
        'code': 'SSMP',
        'description': 'Attack on multiple points in same stage',
        'indicators': [
            'same_stage_multiple_deviations',
            'coordinated_stage_anomalies'
        ]
    }
    
    MSCP = {
        'name': 'Multi Stage Single Point',
        'code': 'MSCP',
        'description': 'Same attack across multiple stages',
        'indicators': [
            'same_sensor_type_multiple_stages',
            'cascading_anomalies'
        ]
    }
    
    MSMP = {
        'name': 'Multi Stage Multi Point',
        'code': 'MSMP',
        'description': 'Coordinated attack across system',
        'indicators': [
            'system_wide_anomalies',
            'multiple_stages_affected',
            'complex_coordination'
        ]
    }

# -----------------------------
# Advanced Anomaly Detector
# -----------------------------
class AdvancedHybridDetector:
    """
    Advanced hybrid anomaly detection with fine-grained classification
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
        
        # Counters
        self.total_anomalies = 0
        self.total_classified = 0
        self.attack_type_counts = defaultdict(int)
        self.anomaly_types = defaultdict(int)
        
        # Track last processed timestamp
        self.last_processed_time = None
        
        print(f"[LOG] AdvancedHybridDetector initialized")
        print(f"[LOG] Capabilities: Binary + Fine-Grained Classification")
        print(f"[LOG] Z-Score threshold: {Z_SCORE_THRESHOLD} sigma")
        print(f"[LOG] Pattern analysis window: {ATTACK_WINDOW_SIZE} records")
        print(f"[LOG] Mode: Historical data (2019-2020 timestamps)")
    
    def learn_baseline(self):
        """Learn normal behavior from historical data"""
        print(f"\n[BASELINE] Learning from all available data...")
        
        # MODIFIED: Use start: 0 to get ALL historical data
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
                        'std': float(values.std() + 1e-8),  # Avoid division by zero
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
        """Calculate Z-score"""
        if sensor_name not in self.baseline_stats:
            return 0.0
        
        stats = self.baseline_stats[sensor_name]
        if stats['std'] == 0:
            return 0.0
        
        return (value - stats['mean']) / stats['std']
    
    def check_rule_violations(self, sensor_data):
        """Check domain rule violations"""
        violations = []
        
        for sensor, value in sensor_data.items():
            if sensor in SCADA_RULES:
                rules = SCADA_RULES[sensor]
                
                if value < rules['min']:
                    violations.append({
                        'sensor': sensor,
                        'type': 'HARD_LIMIT_LOW',
                        'value': value,
                        'threshold': rules['min'],
                        'severity': 'CRITICAL',
                        'message': f"{sensor} below minimum: {value:.2f} < {rules['min']}"
                    })
                
                if value > rules['max']:
                    violations.append({
                        'sensor': sensor,
                        'type': 'HARD_LIMIT_HIGH',
                        'value': value,
                        'threshold': rules['max'],
                        'severity': 'CRITICAL',
                        'message': f"{sensor} above maximum: {value:.2f} > {rules['max']}"
                    })
                
                if value < rules.get('critical_low', rules['min']):
                    violations.append({
                        'sensor': sensor,
                        'type': 'CRITICAL_LOW',
                        'value': value,
                        'threshold': rules['critical_low'],
                        'severity': 'HIGH',
                        'message': f"{sensor} critically low: {value:.2f}"
                    })
                
                if value > rules.get('critical_high', rules['max']):
                    violations.append({
                        'sensor': sensor,
                        'type': 'CRITICAL_HIGH',
                        'value': value,
                        'threshold': rules['critical_high'],
                        'severity': 'HIGH',
                        'message': f"{sensor} critically high: {value:.2f}"
                    })
            
            if sensor in PUMP_STATES:
                if value not in PUMP_STATES[sensor]:
                    violations.append({
                        'sensor': sensor,
                        'type': 'INVALID_STATE',
                        'value': value,
                        'threshold': PUMP_STATES[sensor],
                        'severity': 'MEDIUM',
                        'message': f"{sensor} invalid state: {value}"
                    })
        
        return violations
    
    def classify_attack_type(self, anomalies, z_scores, sensor_data):
        """
        Fine-grained attack classification based on patterns
        """
        if not anomalies:
            return None
        
        # Extract affected sensors
        affected_sensors = [a['sensor'] for a in anomalies if a['sensor'] != 'MULTIPLE']
        actuator_anomalies = [s for s in affected_sensors if 'MV' in s or ('P' in s and 'STATE' in s)]
        sensor_anomalies = [s for s in affected_sensors if s not in actuator_anomalies]
        
        # Count severe deviations
        severe_count = sum(1 for a in anomalies if a.get('severity') == 'CRITICAL')
        high_count = sum(1 for a in anomalies if a.get('severity') == 'HIGH')
        
        # Determine attack stage scope
        stages_affected = set()
        for sensor in affected_sensors:
            if 'P1' in sensor or '101' in sensor:
                stages_affected.add('P1')
            elif 'P2' in sensor or '201' in sensor:
                stages_affected.add('P2')
            elif 'P3' in sensor or '301' in sensor:
                stages_affected.add('P3')
            elif 'P4' in sensor or '401' in sensor:
                stages_affected.add('P4')
            elif 'P5' in sensor or '501' in sensor:
                stages_affected.add('P5')
            elif 'P6' in sensor or '601' in sensor:
                stages_affected.add('P6')
        
        num_stages = len(stages_affected)
        num_affected = len(affected_sensors)
        
        # Classification logic
        attack_class = None
        confidence = 0.0
        reasoning = []
        
        # DoS - All sensors constant or flatlined
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
        
        # Multi-Stage Multi-Point (most complex)
        elif num_stages >= 3 and num_affected >= 5:
            attack_class = AttackPattern.MSMP
            confidence = 0.92
            reasoning.append(f"{num_stages} stages, {num_affected} sensors affected")
        
        # Multi-Stage Single-Point
        elif num_stages >= 2 and num_affected <= 2:
            attack_class = AttackPattern.MSCP
            confidence = 0.80
            reasoning.append(f"Same sensor type across {num_stages} stages")
        
        # Single-Stage Multi-Point
        elif num_stages == 1 and num_affected >= 3:
            attack_class = AttackPattern.SSMP
            confidence = 0.85
            reasoning.append(f"{num_affected} sensors in single stage")
        
        # Single-Stage Single-Point
        elif num_stages == 1 and num_affected <= 2:
            attack_class = AttackPattern.SSCP
            confidence = 0.75
            reasoning.append(f"Isolated anomaly in single stage")
        
        # Reconnaissance - Rapid changes
        elif self._check_recon_pattern():
            attack_class = AttackPattern.RECONNAISSANCE
            confidence = 0.70
            reasoning.append("Rapid sequential sensor access pattern")
        
        # Default to SSCP for single anomalies
        else:
            attack_class = AttackPattern.SSCP
            confidence = 0.60
            reasoning.append("Single point anomaly (default)")
        
        return {
            'attack_type': attack_class,
            'attack_name': attack_class['name'],
            'attack_code': attack_class['code'],
            'confidence': confidence,
            'affected_sensors': affected_sensors,
            'affected_stages': list(stages_affected),
            'num_stages': num_stages,
            'num_sensors': num_affected,
            'severity_critical': severe_count,
            'severity_high': high_count,
            'reasoning': reasoning
        }
    
    def _check_dos_pattern(self):
        """Check for DoS pattern (all sensors constant)"""
        if len(self.sensor_history) < 5:
            return False
        
        # Check if multiple sensors have no variation
        constant_sensors = 0
        for sensor, history in self.sensor_history.items():
            if len(history) >= 5:
                values = list(history)
                if len(set(values)) == 1:  # All same value
                    constant_sensors += 1
        
        return constant_sensors >= 5  # 5+ sensors flatlined
    
    def _check_recon_pattern(self):
        """Check for reconnaissance pattern"""
        # Check for rapid changes in recent history
        if len(self.anomaly_history) >= 5:
            recent_anomalies = list(self.anomaly_history)[-5:]
            return len(recent_anomalies) >= 3  # 3+ anomalies in last 5 readings
        return False
    
    def detect_anomalies(self, sensor_data):
        """Main detection logic"""
        anomalies = []
        z_scores = {}
        
        # Update sensor history
        for sensor, value in sensor_data.items():
            if isinstance(value, (int, float)):
                self.sensor_history[sensor].append(value)
        
        # 1. Z-Score Analysis
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
                            'message': f"{sensor} severe deviation: z={z:.2f}"
                        })
                    elif abs(z) > Z_SCORE_THRESHOLD:
                        anomalies.append({
                            'sensor': sensor,
                            'type': 'Z_SCORE_HIGH',
                            'value': value,
                            'z_score': z,
                            'severity': 'HIGH',
                            'message': f"{sensor} significant deviation: z={z:.2f}"
                        })
                    elif abs(z) > Z_SCORE_MODERATE:
                        anomalies.append({
                            'sensor': sensor,
                            'type': 'Z_SCORE_MODERATE',
                            'value': value,
                            'z_score': z,
                            'severity': 'MEDIUM',
                            'message': f"{sensor} moderate deviation: z={z:.2f}"
                        })
        
        # 2. Rule-Based Detection
        rule_violations = self.check_rule_violations(sensor_data)
        anomalies.extend(rule_violations)
        
        # 3. Multi-Sensor Correlation
        moderate_deviations = [s for s, z in z_scores.items() if Z_SCORE_MODERATE < abs(z) < Z_SCORE_THRESHOLD]
        if len(moderate_deviations) >= 3:
            anomalies.append({
                'sensor': 'MULTIPLE',
                'type': 'CORRELATED_DEVIATION',
                'value': len(moderate_deviations),
                'z_score': 0,
                'severity': 'HIGH',
                'message': f"Multiple sensors deviating: {', '.join(moderate_deviations[:5])}"
            })
        
        # Update anomaly history
        if anomalies:
            self.anomaly_history.append(len(anomalies))
        
        # 4. Fine-Grained Classification
        attack_classification = None
        if anomalies:
            attack_classification = self.classify_attack_type(anomalies, z_scores, sensor_data)
        
        return anomalies, z_scores, attack_classification
    
    def close(self):
        """Close connections"""
        if self.client:
            self.client.close()


# -----------------------------
# Main Detection Loop
# -----------------------------
def main():
    print("="*80)
    print("NT-SCADA Advanced Anomaly Detection System")
    print("Binary Detection + Fine-Grained Attack Classification")
    print("="*80)
    
    detector = AdvancedHybridDetector(
        influx_url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG,
        bucket=INFLUXDB_BUCKET
    )
    
    print("\n[INIT] Waiting for InfluxDB...")
    time.sleep(10)
    
    detector.learn_baseline()
    
    write_api = detector.client.write_api(write_options=SYNCHRONOUS)
    
    print(f"\n[START] Real-time monitoring started")
    print(f"[START] Polling interval: {POLLING_INTERVAL}s")
    print(f"[START] Processing historical data (2019-2020 timestamps)")
    print("="*80 + "\n")
    
    total_processed = 0
    last_processed_time = None
    
    try:
        while True:
            # MODIFIED: Query from last processed time or from beginning
            if last_processed_time:
                time_filter = f'start: time(v: "{last_processed_time.isoformat()}Z")'
            else:
                time_filter = 'start: 0'  # Get all data from beginning
            
            query = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
              |> range({time_filter})
              |> filter(fn: (r) => r._measurement == "sensor_data")
              |> sort(columns: ["_time"], desc: false)
              |> limit(n:10)
              |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
              |> drop(columns: ["_start","_stop","result","table","_measurement"])
            '''
            
            try:
                result = detector.query_api.query(query=query)
                records = []
                for table in result:
                    for record in table.records:
                        records.append(record.values)
                
                if not records:
                    print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] No new data. Sleeping {POLLING_INTERVAL}s...")
                    time.sleep(POLLING_INTERVAL)
                    continue
                
                for record in records:
                    total_processed += 1
                    timestamp = record.get('_time', datetime.utcnow())
                    last_processed_time = timestamp
                    
                    sensor_data = {}
                    for key, value in record.items():
                        if key.startswith('_') or key in ['table', 'result']:
                            continue
                        if isinstance(value, (int, float, str)):
                            try:
                                sensor_data[key] = float(value) if isinstance(value, (int, float)) else float(value)
                            except:
                                pass
                    
                    # Detect anomalies with classification
                    anomalies, z_scores, attack_class = detector.detect_anomalies(sensor_data)
                    
                    if anomalies:
                        critical = [a for a in anomalies if a['severity'] == 'CRITICAL']
                        high = [a for a in anomalies if a['severity'] == 'HIGH']
                        medium = [a for a in anomalies if a['severity'] == 'MEDIUM']
                        
                        detector.total_anomalies += 1
                        
                        print(f"\n{'='*80}")
                        print(f"🚨 ANOMALY DETECTED #{detector.total_anomalies}")
                        print(f"{'='*80}")
                        print(f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"Processed: {total_processed} records")
                        
                        # Show attack classification
                        if attack_class:
                            detector.total_classified += 1
                            detector.attack_type_counts[attack_class['attack_code']] += 1
                            
                            print(f"\n🎯 ATTACK CLASSIFICATION:")
                            print(f"  Type: {attack_class['attack_name']} ({attack_class['attack_code']})")
                            print(f"  Confidence: {attack_class['confidence']:.0%}")
                            print(f"  Affected: {attack_class['num_sensors']} sensors across {attack_class['num_stages']} stage(s)")
                            print(f"  Reasoning: {'; '.join(attack_class['reasoning'])}")
                        
                        print(f"\n📊 ANOMALY DETAILS:")
                        print(f"  Total Issues: {len(anomalies)} (Critical: {len(critical)}, High: {len(high)}, Medium: {len(medium)})")
                        print(f"-"*80)
                        
                        if critical:
                            print(f"\n🔴 CRITICAL ISSUES ({len(critical)}):")
                            for i, a in enumerate(critical[:5], 1):
                                print(f"  {i}. {a['message']}")
                            if len(critical) > 5:
                                print(f"  ... and {len(critical) - 5} more")
                        
                        if high:
                            print(f"\n🟠 HIGH PRIORITY ({len(high)}):")
                            for i, a in enumerate(high[:5], 1):
                                print(f"  {i}. {a['message']}")
                            if len(high) > 5:
                                print(f"  ... and {len(high) - 5} more")
                        
                        if medium:
                            print(f"\n🟡 MEDIUM PRIORITY ({len(medium)}):")
                            for i, a in enumerate(medium[:3], 1):
                                print(f"  {i}. {a['message']}")
                            if len(medium) > 3:
                                print(f"  ... and {len(medium) - 3} more")
                        
                        print(f"\n{'='*80}\n")
                        
                        # Write to InfluxDB
                        for anomaly in anomalies:
                            point = Point("anomaly_alert") \
                                .tag("anomaly_type", anomaly['type']) \
                                .tag("severity", anomaly['severity']) \
                                .tag("sensor", anomaly['sensor']) \
                                .field("value", float(anomaly['value'])) \
                                .field("z_score", float(anomaly.get('z_score', 0))) \
                                .field("message", anomaly['message']) \
                                .time(timestamp, WritePrecision.NS)
                            
                            # Add attack classification
                            if attack_class:
                                point = point.tag("attack_type", attack_class['attack_code']) \
                                       .tag("attack_name", attack_class['attack_name']) \
                                       .field("attack_confidence", attack_class['confidence']) \
                                       .field("num_stages_affected", attack_class['num_stages']) \
                                       .field("num_sensors_affected", attack_class['num_sensors'])
                            
                            write_api.write(bucket=ANOMALY_BUCKET, org=INFLUXDB_ORG, record=point)
                        
                        for anomaly in anomalies:
                            detector.anomaly_types[anomaly['type']] += 1
                    
                    else:
                        if total_processed % 100 == 0:
                            print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] ✓ Processed {total_processed} records. System normal.")
                
            except Exception as e:
                print(f"[ERROR] {e}")
                import traceback
                traceback.print_exc()
            
            time.sleep(POLLING_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n[STOP] Detection stopped by user")
    except Exception as e:
        print(f"[FATAL] {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n" + "="*80)
        print("DETECTION SUMMARY")
        print("="*80)
        print(f"Total records processed: {total_processed}")
        print(f"Total anomalies detected: {detector.total_anomalies}")
        print(f"Total attacks classified: {detector.total_classified}")
        
        if detector.attack_type_counts:
            print(f"\n🎯 Attack Type Breakdown:")
            for atype, count in sorted(detector.attack_type_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  • {atype}: {count}")
        
        print(f"\n📊 Anomaly Type Breakdown:")
        for atype, count in sorted(detector.anomaly_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {atype}: {count}")
        print("="*80)
        
        detector.close()


if __name__ == "__main__":
    main()
