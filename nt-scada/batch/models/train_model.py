"""
NT-SCADA Batch Analytics and Model Training
Performs batch time-series analytics on historical data
Trains binary and multi-class classification models
Generates daily statistics and reports
"""

import os
import pickle
import json
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from influxdb_client import InfluxDBClient
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Configuration
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'my-super-secret-auth-token')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'nt-scada')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', 'scada_data')

MODEL_DIR = '/app/models'
REPORT_DIR = '/app/reports'

# Create directories if they don't exist
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)


def connect_influxdb():
    """Connect to InfluxDB"""
    max_retries = 5
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            client = InfluxDBClient(
                url=INFLUXDB_URL,
                token=INFLUXDB_TOKEN,
                org=INFLUXDB_ORG
            )
            health = client.health()
            if health.status == "pass":
                print(f"✓ Connected to InfluxDB at {INFLUXDB_URL}")
                return client
            else:
                raise Exception(f"InfluxDB health check failed: {health.status}")
        except Exception as e:
            print(f"⚠ InfluxDB not available (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay}s...")
                import time
                time.sleep(retry_delay)
    
    raise Exception("Failed to connect to InfluxDB")


def query_sensor_data(client, days_back=7):
    """Query sensor data from InfluxDB"""
    query_api = client.query_api()
    
    # Query for the last N days
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -{days_back}d)
      |> filter(fn: (r) => r["_measurement"] == "sensor_data")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    
    print(f"Querying sensor data for the last {days_back} days...")
    result = query_api.query(query=query)
    
    # Convert to DataFrame
    records = []
    for table in result:
        for record in table.records:
            records.append({
                'time': record.get_time(),
                'sensor_id': record.values.get('sensor_id'),
                'sensor_type': record.values.get('sensor_type'),
                'location': record.values.get('location'),
                'status': record.values.get('status'),
                'severity': record.values.get('severity'),
                'category': record.values.get('category'),
                'operational_state': record.values.get('operational_state'),
                'value': record.values.get('value'),
                'anomaly': record.values.get('anomaly', 0)
            })
    
    df = pd.DataFrame(records)
    print(f"✓ Retrieved {len(df)} sensor records")
    return df


def engineer_features(df):
    """Engineer features for ML models"""
    if df.empty:
        return df
    
    # Sort by time
    df = df.sort_values('time')
    
    # Extract time-based features
    df['hour'] = df['time'].dt.hour
    df['day_of_week'] = df['time'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    
    # Create rolling statistics per sensor
    df['value_rolling_mean_5'] = df.groupby('sensor_id')['value'].transform(
        lambda x: x.rolling(window=5, min_periods=1).mean()
    )
    df['value_rolling_std_5'] = df.groupby('sensor_id')['value'].transform(
        lambda x: x.rolling(window=5, min_periods=1).std()
    )
    
    # Fill NaN values
    df['value_rolling_std_5'] = df['value_rolling_std_5'].fillna(0)
    
    # Rate of change
    df['value_diff'] = df.groupby('sensor_id')['value'].diff().fillna(0)
    
    # Encode categorical variables
    df['sensor_type_encoded'] = pd.Categorical(df['sensor_type']).codes
    df['location_encoded'] = pd.Categorical(df['location']).codes
    
    return df


def train_binary_classifier(df):
    """
    Batch Task 1: Train binary classification model
    Predicts: Normal (0) vs Anomaly (1)
    """
    print("\n" + "=" * 60)
    print("BATCH TASK 1: Binary Classification Model Training")
    print("=" * 60)
    
    if df.empty or len(df) < 100:
        print("⚠ Insufficient data for training. Need at least 100 records.")
        return None, None
    
    # Prepare features
    feature_cols = [
        'value', 'hour', 'day_of_week', 'is_weekend',
        'value_rolling_mean_5', 'value_rolling_std_5', 'value_diff',
        'sensor_type_encoded', 'location_encoded'
    ]
    
    X = df[feature_cols].fillna(0)
    y = df['anomaly'].astype(int)
    
    # Check class distribution
    print(f"Class distribution: {y.value_counts().to_dict()}")
    
    if len(y.unique()) < 2:
        print("⚠ Only one class present. Cannot train binary classifier.")
        return None, None
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train Random Forest classifier
    print("Training Random Forest binary classifier...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced'
    )
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"\n✓ Binary Classifier Accuracy: {accuracy:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Normal', 'Anomaly']))
    
    # Save model and scaler
    model_path = os.path.join(MODEL_DIR, 'binary_classifier.pkl')
    scaler_path = os.path.join(MODEL_DIR, 'binary_scaler.pkl')
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    
    print(f"✓ Model saved to {model_path}")
    
    return model, scaler


def train_multiclass_classifier(df):
    """
    Batch Task 2: Train fine-grained multi-class classification model
    Predicts operational state: CRITICALLY_LOW, LOW, BELOW_OPTIMAL, OPTIMAL, 
                                ABOVE_OPTIMAL, HIGH, CRITICALLY_HIGH
    """
    print("\n" + "=" * 60)
    print("BATCH TASK 2: Multi-Class Classification Model Training")
    print("=" * 60)
    
    if df.empty or len(df) < 100:
        print("⚠ Insufficient data for training. Need at least 100 records.")
        return None, None
    
    # Prepare features
    feature_cols = [
        'value', 'hour', 'day_of_week', 'is_weekend',
        'value_rolling_mean_5', 'value_rolling_std_5', 'value_diff',
        'sensor_type_encoded', 'location_encoded'
    ]
    
    X = df[feature_cols].fillna(0)
    y = pd.Categorical(df['operational_state']).codes
    class_names = pd.Categorical(df['operational_state']).categories.tolist()
    
    # Check class distribution
    print(f"Number of classes: {len(np.unique(y))}")
    print(f"Class names: {class_names}")
    
    if len(np.unique(y)) < 2:
        print("⚠ Only one class present. Cannot train multi-class classifier.")
        return None, None
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train Gradient Boosting classifier
    print("Training Gradient Boosting multi-class classifier...")
    model = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        random_state=42,
        learning_rate=0.1
    )
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"\n✓ Multi-Class Classifier Accuracy: {accuracy:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=class_names))
    
    # Save model, scaler, and class names
    model_path = os.path.join(MODEL_DIR, 'multiclass_classifier.pkl')
    scaler_path = os.path.join(MODEL_DIR, 'multiclass_scaler.pkl')
    classes_path = os.path.join(MODEL_DIR, 'class_names.pkl')
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    with open(classes_path, 'wb') as f:
        pickle.dump(class_names, f)
    
    print(f"✓ Model saved to {model_path}")
    
    return model, scaler


def generate_daily_statistics(df):
    """
    Batch Task 3: Analyze and visualize daily statistics
    """
    print("\n" + "=" * 60)
    print("BATCH TASK 3: Daily Statistics Analysis")
    print("=" * 60)
    
    if df.empty:
        print("⚠ No data available for statistics.")
        return
    
    # Overall statistics
    stats = {
        'timestamp': datetime.utcnow().isoformat(),
        'total_records': len(df),
        'date_range': {
            'start': df['time'].min().isoformat(),
            'end': df['time'].max().isoformat()
        },
        'sensors': {
            'total_unique': df['sensor_id'].nunique(),
            'types': df['sensor_type'].value_counts().to_dict()
        },
        'anomalies': {
            'total': int(df['anomaly'].sum()),
            'percentage': float(df['anomaly'].mean() * 100),
            'by_severity': df[df['anomaly'] == 1]['severity'].value_counts().to_dict() if df['anomaly'].sum() > 0 else {}
        },
        'operational_states': df['operational_state'].value_counts().to_dict(),
        'value_statistics': {
            'mean': float(df['value'].mean()),
            'median': float(df['value'].median()),
            'std': float(df['value'].std()),
            'min': float(df['value'].min()),
            'max': float(df['value'].max())
        }
    }
    
    # Daily aggregations
    df['date'] = df['time'].dt.date
    daily_stats = df.groupby('date').agg({
        'value': ['mean', 'min', 'max', 'std'],
        'anomaly': 'sum',
        'sensor_id': 'count'
    }).round(2)
    
    stats['daily_summary'] = daily_stats.to_dict()
    
    # Sensor-level statistics
    sensor_stats = df.groupby('sensor_id').agg({
        'value': ['mean', 'std', 'min', 'max'],
        'anomaly': 'sum'
    }).round(2)
    
    stats['top_anomalous_sensors'] = sensor_stats.nlargest(10, ('anomaly', 'sum')).to_dict()
    
    # Save report
    report_path = os.path.join(REPORT_DIR, f'daily_report_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json')
    with open(report_path, 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    
    print(f"\n✓ Daily Statistics Report:")
    print(f"  Total Records: {stats['total_records']}")
    print(f"  Unique Sensors: {stats['sensors']['total_unique']}")
    print(f"  Total Anomalies: {stats['anomalies']['total']} ({stats['anomalies']['percentage']:.2f}%)")
    print(f"  Value Range: {stats['value_statistics']['min']:.2f} - {stats['value_statistics']['max']:.2f}")
    print(f"  Mean Value: {stats['value_statistics']['mean']:.2f} ± {stats['value_statistics']['std']:.2f}")
    print(f"\n✓ Report saved to {report_path}")


def main():
    """Main batch processing pipeline"""
    print("=" * 60)
    print("NT-SCADA Batch Analytics & Model Training")
    print("=" * 60)
    print(f"InfluxDB URL: {INFLUXDB_URL}")
    print(f"Model Directory: {MODEL_DIR}")
    print(f"Report Directory: {REPORT_DIR}")
    print("=" * 60)
    
    try:
        # Connect to InfluxDB
        client = connect_influxdb()
        
        # Query data
        df = query_sensor_data(client, days_back=7)
        
        if df.empty:
            print("\n⚠ No data available. Waiting for data collection...")
            print("Run this script again after sensors have generated data.")
            return
        
        # Engineer features
        print("\nEngineering features...")
        df = engineer_features(df)
        
        # Batch Task 1: Binary classification
        binary_model, binary_scaler = train_binary_classifier(df)
        
        # Batch Task 2: Multi-class classification
        multiclass_model, multiclass_scaler = train_multiclass_classifier(df)
        
        # Batch Task 3: Daily statistics
        generate_daily_statistics(df)
        
        print("\n" + "=" * 60)
        print("✓ Batch processing completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n⚠ Error in batch processing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'client' in locals():
            client.close()


if __name__ == "__main__":
    main()
