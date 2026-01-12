"""
NT-SCADA Anomaly Detection System
==================================

This script implements hybrid anomaly detection for SCADA systems using:
1. Statistical Z-Score Detection (Hawkins, 1980; Chandola et al., 2009)
2. Rule-Based Physical Process Validation (Adepu & Mathur, 2016)

Author: NT-SCADA Project
Date: 2025-11-25
"""

import pandas as pd
import numpy as np
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "nt-scada-token-secret-key-12345"  # Replace with your actual token
INFLUXDB_ORG = "nt-scada"
INFLUXDB_BUCKET = "scada_data"
INFLUXDB_ANOMALY_BUCKET = "scada_anomalies"  # New bucket for anomaly results
client = InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)

# Statistical thresholds
Z_SCORE_THRESHOLD = 2.0  # Standard deviations from mean

# Physical process limits (based on SWaT system specifications)
# Physical process limits (based on ACTUAL observed data statistics)
# Physical process limits (BALANCED - based on μ ± 4σ)
# Physical process limits (TIGHTER - based on μ ± 2.5σ to catch attacks)
SENSOR_LIMITS = {
    'LIT101.Pv': {'min': 456, 'max': 1012, 'name': 'Raw Water Tank Level'},  # μ±2.5σ
    'FIT101.Pv': {'min': -3.3, 'max': 4.8, 'name': 'Raw Water Flow'},  # μ±2.5σ
    'AIT201.Pv': {'min': 118, 'max': 160, 'name': 'Chemical Tank 1 Level'},  # μ±2.5σ
    'AIT202.Pv': {'min': 8.8, 'max': 9.7, 'name': 'Chemical Tank 2 Level'},  # μ±2.5σ
    'AIT203.Pv': {'min': 218, 'max': 278, 'name': 'Chemical Tank 3 Level'},  # μ±2.5σ
    'FIT201.Pv': {'min': -2.0, 'max': 3.7, 'name': 'Chemical Flow'},  # μ±2.5σ
    'LIT301.Pv': {'min': 716, 'max': 1177, 'name': 'UF Feed Tank Level'},  # μ±2.5σ
    'LIT401.Pv': {'min': 728, 'max': 1044, 'name': 'RO Permeate Tank Level'},  # μ±2.5σ
    'FIT401.Pv': {'min': 0.69, 'max': 0.89, 'name': 'RO Permeate Flow'},  # μ±2.5σ (CRITICAL!)
}

# ============================================================================
# ANOMALY DETECTION ALGORITHMS
# ============================================================================

class StatisticalAnomalyDetector:
    """
    Statistical anomaly detection using Z-score method.
    
    Theory:
    -------
    Assumes normal data follows Gaussian distribution.
    Z-score measures how many standard deviations a point is from mean.
    Points with |z-score| > threshold are considered anomalies.
    
    Formula: z = (x - μ) / σ
    where:
        x = observed value
        μ = mean of normal data
        σ = standard deviation
    
    Reference:
    ----------
    Hawkins, D. M. (1980). Identification of Outliers. Chapman and Hall.
    Chandola, V., et al. (2009). Anomaly detection: A survey. ACM Computing Surveys.
    """
    
    def __init__(self, threshold=3.0):
        self.threshold = threshold
        self.baselines = {}
    
    def fit(self, data, sensor_columns):
        """
        Calculate statistical baselines from normal data.
        
        Parameters:
        -----------
        data : pd.DataFrame
            Normal operation data
        sensor_columns : list
            List of sensor column names to analyze
        """
        self.baselines = {}  # Initialize baselines dictionary
        print(f"📊 Calculating statistical baselines...")
        
        for col in sensor_columns:
            if col in data.columns:
                # Convert to numeric, coerce errors to NaN
                numeric_data = pd.to_numeric(data[col], errors='coerce')
                
                # Check if we have any valid numeric data
                if numeric_data.notna().sum() == 0:
                    print(f"  ⚠️  Skipping {col}: No valid numeric data")
                    continue
                
                # Calculate statistics only on numeric data
                self.baselines[col] = {
                    'mean': numeric_data.mean(),
                    'std': numeric_data.std(),
                    'min': numeric_data.min(),
                    'max': numeric_data.max(),
                    'median': numeric_data.median()
                }
                
                print(f"  ✓ {col}: μ={self.baselines[col]['mean']:.2f}, σ={self.baselines[col]['std']:.2f}")
    def detect(self, value, sensor_name):
        """
        Detect if a value is anomalous using Z-score.
        
        Parameters:
        -----------
        value : float
            Sensor reading to check
        sensor_name : str
            Name of the sensor
        
        Returns:
        --------
        dict : {
            'is_anomaly': bool,
            'z_score': float,
            'severity': str
        }
        """
        if sensor_name not in self.baselines:
            return {'is_anomaly': False, 'z_score': 0, 'severity': 'unknown'}
        
        stats = self.baselines[sensor_name]
        
        # Handle zero standard deviation
        if stats['std'] == 0:
            z_score = 0
        else:
            z_score = (value - stats['mean']) / stats['std']
        
        is_anomaly = abs(z_score) > self.threshold
        
        # Severity classification
        if abs(z_score) > 5:
            severity = 'critical'
        elif abs(z_score) > 4:
            severity = 'high'
        elif abs(z_score) > 3:
            severity = 'medium'
        else:
            severity = 'low'
        
        return {
            'is_anomaly': is_anomaly,
            'z_score': z_score,
            'severity': severity if is_anomaly else 'normal'
        }


class RuleBasedAnomalyDetector:
    """
    Rule-based anomaly detection using physical process constraints.
    
    Theory:
    -------
    Uses domain knowledge of water treatment process to detect violations
    of physical laws and operational safety constraints.
    
    Examples:
    - Tank overflow prevention
    - Pump protection (don't run dry)
    - Flow consistency checks
    
    Reference:
    ----------
    Adepu, S., & Mathur, A. (2016). Generalized Attacker and Attack Models 
    for Cyber Physical Systems. IEEE DSN.
    """
    
    def __init__(self, sensor_limits):
        self.sensor_limits = sensor_limits
    
    def check_range_violation(self, sensor_name, value):
        """Check if value is outside physical limits."""
        if sensor_name not in self.sensor_limits:
            return None
        
        limits = self.sensor_limits[sensor_name]
        
        if value < limits['min']:
            return {
                'is_anomaly': True,
                'rule': 'BELOW_MINIMUM',
                'description': f"{limits['name']} below minimum ({limits['min']})",
                'severity': 'high'
            }
        elif value > limits['max']:
            return {
                'is_anomaly': True,
                'rule': 'ABOVE_MAXIMUM',
                'description': f"{limits['name']} above maximum ({limits['max']})",
                'severity': 'high'
            }
        
        return {'is_anomaly': False, 'rule': 'WITHIN_RANGE', 'severity': 'normal'}
    
    def check_process_logic(self, data_point):
        """
        Check for violations of process logic.
        
        Parameters:
        -----------
        data_point : dict
            Dictionary containing all sensor/actuator values at a timestamp
        
        Returns:
        --------
        list : List of detected rule violations
        """
        violations = []
        
        # Rule 1: Tank overflow prevention
        # If tank is near full (>90%) and inlet pump is ON, flag as anomaly
        if 'LIT101.Pv' in data_point and 'P101.Status' in data_point:
            if data_point['LIT101.Pv'] > 900 and data_point['P101.Status'] == 1:
                violations.append({
                    'is_anomaly': True,
                    'rule': 'TANK_OVERFLOW_RISK',
                    'description': 'Tank level >90% but inlet pump still ON',
                    'severity': 'critical',
                    'affected_sensors': ['LIT101.Pv', 'P101.Status']
                })
        
        # Rule 2: Dry pump protection
        # If tank is near empty (<10%) and outlet pump is ON, flag as anomaly
        if 'LIT101.Pv' in data_point and 'P102.Status' in data_point:
            if data_point['LIT101.Pv'] < 300 and data_point['P102.Status'] == 1:
                violations.append({
                    'is_anomaly': True,
                    'rule': 'DRY_PUMP_RISK',
                    'description': 'Tank level <30% but outlet pump still ON',
                    'severity': 'critical',
                    'affected_sensors': ['LIT101.Pv', 'P102.Status']
                })
        
        # Rule 3: Flow-pump consistency
        # If pump is ON but no flow detected (or vice versa)
        if 'P101.Status' in data_point and 'FIT101.Pv' in data_point:
            if data_point['P101.Status'] == 1 and data_point['FIT101.Pv'] < 0.1:
                violations.append({
                    'is_anomaly': True,
                    'rule': 'PUMP_FLOW_MISMATCH',
                    'description': 'Pump ON but no flow detected',
                    'severity': 'high',
                    'affected_sensors': ['P101.Status', 'FIT101.Pv']
                })
        
        # Rule 4: Chemical tank level monitoring
        for tank in ['AIT201.Pv', 'AIT202.Pv', 'AIT203.Pv']:
            if tank in data_point:
                if data_point[tank] < 5:
                    violations.append({
                        'is_anomaly': True,
                        'rule': 'CHEMICAL_LOW',
                        'description': f'{tank} critically low (<5%)',
                        'severity': 'medium',
                        'affected_sensors': [tank]
                    })
        
        return violations


# ============================================================================
# DATA PROCESSING
# ============================================================================

def fetch_data_from_influxdb(start_time, stop_time, measurement="swat_attack_data"):
    """
    Fetch sensor data from InfluxDB.
    
    Parameters:
    -----------
    start_time : str
        Start time in RFC3339 format
    stop_time : str
        Stop time in RFC3339 format
    measurement : str
        Measurement name (default: "swat_attack_data" for SWaT July 19 data)
    
    Returns:
    --------
    pd.DataFrame : Sensor data with timestamps and attack labels
    """
    print(f"\n📥 Fetching data from InfluxDB...")
    print(f"   Measurement: {measurement}")
    print(f"   Time range: {start_time} to {stop_time}")
    
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = client.query_api()
    
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: {start_time}, stop: {stop_time})
      |> filter(fn: (r) => r._measurement == "{measurement}")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    
    result = query_api.query_data_frame(query)
    client.close()
    
    if result.empty:
        print("   ⚠️  No data found!")
        return pd.DataFrame()
    
    print(f"   ✓ Fetched {len(result)} data points")
    
    # Check if attack labels exist
    if 'attack_label' in result.columns:
        attack_count = result['attack_label'].sum()
        normal_count = len(result) - attack_count
        print(f"   ✓ Normal points: {normal_count}")
        print(f"   ✓ Attack points: {attack_count}")
    
    return result


def write_anomalies_to_influxdb(anomalies_df):
    """Write detected anomalies to InfluxDB"""
    print(f"\n📤 Writing {len(anomalies_df)} anomaly records to InfluxDB...")
    
    write_api = client.write_api(write_options=SYNCHRONOUS)
    batch_size = 1000
    
    for batch_num, start_idx in enumerate(range(0, len(anomalies_df), batch_size), 1):
        batch = anomalies_df.iloc[start_idx:start_idx + batch_size]
        points = []
        
        for _, row in batch.iterrows():
            point = Point("anomaly_detection") \
                .tag("sensor", str(row['sensor_name'])) \
                .tag("severity", str(row['severity'])) \
                .tag("detection_method", str(row['detection_method'])) \
                .tag("attack_type", str(row['attack_type'])) \
                .tag("affected_sensor", str(row['sensor_name'])) \
                .field("value", float(row['value'])) \
                .field("is_anomaly", 1.0) \
                .field("anomaly_score", float(row['anomaly_score'])) \
                .field("z_score", float(row['anomaly_score'])) \
                .time(row['timestamp'])
            
            points.append(point)
        
        write_api.write(bucket=INFLUXDB_ANOMALY_BUCKET, org=INFLUXDB_ORG, record=points)
        print(f"   ✓ Written batch {batch_num} ({len(batch)} records)")
    
    print("   ✓ All anomalies written successfully!")

# ============================================================================
# MAIN ANOMALY DETECTION PIPELINE
# ============================================================================

def detect_anomalies(data_df, stat_detector, rule_detector):
    """
    Run anomaly detection on data using both statistical and rule-based methods.
    
    Parameters:
    -----------
    data_df : pd.DataFrame
        Sensor data to analyze
    stat_detector : StatisticalAnomalyDetector
        Trained statistical detector
    rule_detector : RuleBasedAnomalyDetector
        Rule-based detector
    
    Returns:
    --------
    pd.DataFrame : Anomaly detection results
    """
    print("\n🔍 Running anomaly detection...")
    
    anomaly_records = []
    # Get numeric sensor columns only (exclude alarm columns and text fields)
    sensor_columns = [col for col in data_df.columns 
                      if '.Pv' in col 
                      and col not in data_df.columns[data_df.dtypes == 'object']]

    # Also exclude any columns with 'Alarm', 'Status', 'STATE' in the name
    sensor_columns = [col for col in sensor_columns 
                      if 'Alarm' not in col 
                      and 'Status' not in col 
                      and 'STATE' not in col]

    print(f"   ✓ Found {len(sensor_columns)} numeric sensor columns")
    
    for idx, row in data_df.iterrows():
        # Convert row to dict for rule checking
        data_point = row.to_dict()
        
        # Statistical detection for each sensor
        for sensor in sensor_columns:
            if pd.notna(row[sensor]):
                stat_result = stat_detector.detect(row[sensor], sensor)
                
                if stat_result['is_anomaly']:
                    anomaly_records.append({
                        'timestamp': row['_time'],
                        'sensor_name': sensor,
                        'value': row[sensor],
                        'is_anomaly': True,
                        'anomaly_score': abs(stat_result['z_score']),
                        'detection_method': 'statistical',
                        'severity': stat_result['severity'],
                        'attack_type': 'statistical_outlier'
                    })
        
        # Range violation checks
        for sensor in sensor_columns:
            if pd.notna(row[sensor]):
                range_result = rule_detector.check_range_violation(sensor, row[sensor])
                
                if range_result and range_result['is_anomaly']:
                    anomaly_records.append({
                        'timestamp': row['_time'],
                        'sensor_name': sensor,
                        'value': row[sensor],
                        'is_anomaly': True,
                        'anomaly_score': 5.0,  # High score for range violations
                        'detection_method': 'rule_based_range',
                        'severity': range_result['severity'],
                        'attack_type': range_result['rule']
                    })
        
        # Process logic violations
        logic_violations = rule_detector.check_process_logic(data_point)
        for violation in logic_violations:
            anomaly_records.append({
                'timestamp': row['_time'],
                'sensor_name': ','.join(violation['affected_sensors']),
                'value': 0,  # Not applicable for logic violations
                'is_anomaly': True,
                'anomaly_score': 10.0,  # Very high score for logic violations
                'detection_method': 'rule_based_logic',
                'severity': violation['severity'],
                'attack_type': violation['rule']
            })
    
    anomalies_df = pd.DataFrame(anomaly_records)
    
    if len(anomalies_df) > 0:
        print(f"   ✓ Detected {len(anomalies_df)} anomalies")
        print(f"\n📊 Anomaly Summary:")
        print(f"   By severity:")
        print(anomalies_df['severity'].value_counts())
        print(f"\n   By detection method:")
        print(anomalies_df['detection_method'].value_counts())
    else:
        print("   ✓ No anomalies detected (all data normal)")
    
    return anomalies_df


def calculate_metrics(anomalies_df, data_df):
    """
    Calculate detection performance metrics when ground truth labels are available.
    
    Parameters:
    -----------
    anomalies_df : pd.DataFrame
        Detected anomalies
    data_df : pd.DataFrame
        All data with attack_label column
    
    Returns:
    --------
    dict : Performance metrics
    """
    if 'attack_label' not in data_df.columns:
        print("\n⚠️  No ground truth labels available, skipping metrics calculation.")
        return None
    
    print("\n📊 Calculating Detection Performance Metrics...")
    
    # Create a set of timestamps where we detected anomalies
    detected_timestamps = set(anomalies_df['timestamp'].dt.floor('S'))  # Round to seconds
    
    # Create ground truth sets
    actual_attack_timestamps = set(data_df[data_df['attack_label'] == 1]['_time'].dt.floor('S'))
    actual_normal_timestamps = set(data_df[data_df['attack_label'] == 0]['_time'].dt.floor('S'))
    
    # Calculate confusion matrix elements
    true_positives = len(detected_timestamps & actual_attack_timestamps)  # Detected attacks that are real
    false_positives = len(detected_timestamps & actual_normal_timestamps)  # Detected attacks that are normal
    false_negatives = len(actual_attack_timestamps - detected_timestamps)  # Real attacks we missed
    true_negatives = len(actual_normal_timestamps - detected_timestamps)  # Normal points correctly not flagged
    
    # Calculate metrics
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (true_positives + true_negatives) / len(data_df) if len(data_df) > 0 else 0
    
    metrics = {
        'true_positives': true_positives,
        'false_positives': false_positives,
        'true_negatives': true_negatives,
        'false_negatives': false_negatives,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'accuracy': accuracy
    }
    
    # Print results
    print(f"\n   Confusion Matrix:")
    print(f"   ┌─────────────────────┬──────────────┬──────────────┐")
    print(f"   │                     │  Predicted   │  Predicted   │")
    print(f"   │                     │   Attack     │   Normal     │")
    print(f"   ├─────────────────────┼──────────────┼──────────────┤")
    print(f"   │ Actual Attack       │  {true_positives:8d}    │  {false_negatives:8d}    │")
    print(f"   │ Actual Normal       │  {false_positives:8d}    │  {true_negatives:8d}    │")
    print(f"   └─────────────────────┴──────────────┴──────────────┘")
    
    print(f"\n   Performance Metrics:")
    print(f"   • Precision:  {precision:.4f}  ({true_positives}/{true_positives + false_positives} detected anomalies are real)")
    print(f"   • Recall:     {recall:.4f}  ({true_positives}/{true_positives + false_negatives} real attacks detected)")
    print(f"   • F1-Score:   {f1_score:.4f}  (harmonic mean of precision & recall)")
    print(f"   • Accuracy:   {accuracy:.4f}  (overall correctness)")
    
    return metrics


def main():
    """Main execution function."""
    print("="*70)
    print("NT-SCADA ANOMALY DETECTION SYSTEM")
    print("="*70)
    
    # Step 1: Fetch data
    # For SWaT July 19, 2019 data with attacks:
    start_time = "2019-07-20T04:30:00Z"  # 12:30 PM GMT+8 = 4:30 AM UTC
    stop_time = "2019-07-20T08:40:00Z"   # 4:40 PM GMT+8 = 8:40 AM UTC
    
    data_df = fetch_data_from_influxdb(start_time, stop_time, measurement="swat_attack_data")
    
    if data_df.empty:
        print("\n❌ No data available. Exiting.")
        print("\n💡 Tip: Run 'load_attack_data.py' first to load SWaT attack data.")
        return
    
    # Step 2: Initialize detectors
    print("\n🔧 Initializing anomaly detectors...")
    stat_detector = StatisticalAnomalyDetector(threshold=Z_SCORE_THRESHOLD)
    rule_detector = RuleBasedAnomalyDetector(SENSOR_LIMITS)
    
    # Step 3: Train statistical detector on NORMAL DATA ONLY (if labels available)
    if 'attack_label' in data_df.columns:
        train_data = data_df[data_df['attack_label'] == 0]  # Use only normal data for training
        test_data = data_df  # Test on all data (both normal and attacks)
        print(f"   ✓ Training on {len(train_data)} normal data points")
        print(f"   ✓ Testing on {len(test_data)} total data points")
    else:
        # No labels - use first 50% for training
        train_size = len(data_df) // 2
        train_data = data_df.iloc[:train_size]
        test_data = data_df.iloc[train_size:]
        print(f"   ✓ Training on first 50% ({len(train_data)} points)")
        print(f"   ✓ Testing on remaining 50% ({len(test_data)} points)")
    
    sensor_columns = [col for col in data_df.columns if '.Pv' in col]
    stat_detector.fit(train_data, sensor_columns)
    
    # Step 4: Run detection on test data
    anomalies_df = detect_anomalies(test_data, stat_detector, rule_detector)
    
    # Step 5: Calculate performance metrics (if labels available)
    if 'attack_label' in data_df.columns and len(anomalies_df) > 0:
        metrics = calculate_metrics(anomalies_df, test_data)
        
        # Save metrics to file
        if metrics:
            metrics_file = 'detection_metrics.txt'
            with open(metrics_file, 'w') as f:
                f.write("NT-SCADA Anomaly Detection Performance Metrics\n")
                f.write("="*50 + "\n\n")
                f.write(f"Precision:  {metrics['precision']:.4f}\n")
                f.write(f"Recall:     {metrics['recall']:.4f}\n")
                f.write(f"F1-Score:   {metrics['f1_score']:.4f}\n")
                f.write(f"Accuracy:   {metrics['accuracy']:.4f}\n\n")
                f.write(f"True Positives:   {metrics['true_positives']}\n")
                f.write(f"False Positives:  {metrics['false_positives']}\n")
                f.write(f"True Negatives:   {metrics['true_negatives']}\n")
                f.write(f"False Negatives:  {metrics['false_negatives']}\n")
            print(f"\n💾 Metrics saved to: {metrics_file}")
    
    # Step 6: Write results to InfluxDB
    if len(anomalies_df) > 0:
        write_anomalies_to_influxdb(anomalies_df)
        
        # Save to CSV for analysis
        csv_file = 'anomaly_detection_results.csv'
        anomalies_df.to_csv(csv_file, index=False)
        print(f"\n💾 Results also saved to: {csv_file}")
    
    print("\n" + "="*70)
    print("✅ ANOMALY DETECTION COMPLETE!")
    print("="*70)


if __name__ == "__main__":
    main()
