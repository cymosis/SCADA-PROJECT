#!/usr/bin/env python3
"""
Phase 3: Batch Processing & Model Training
Advanced Apache Flink-style batch jobs using scikit-learn and feature engineering
Processes historical sensor data from InfluxDB for ML model training
"""

import os
import json
import pickle
import joblib
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix
from influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import SYNCHRONOUS
import warnings
warnings.filterwarnings('ignore')


class InfluxDBDataLoader:
    """Loads historical sensor data from InfluxDB"""
    
    def __init__(self, url, token, org, bucket):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.client = None
        self.query_api = None
    
    def connect(self):
        """Connect to InfluxDB"""
        try:
            self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
            self.query_api = self.client.query_api(query_type=SYNCHRONOUS)
            print(f"✓ Connected to InfluxDB at {self.url}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to InfluxDB: {e}")
            return False
    
    def query_sensor_data(self, time_range="-7d"):
        """Query sensor data from InfluxDB"""
        try:
            query = f'''
            from(bucket: "{self.bucket}")
            |> range(start: {time_range})
            |> filter(fn: (r) => r["_measurement"] == "sensor_data")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''
            
            tables = self.query_api.query(query)
            
            data_list = []
            for table in tables:
                for record in table.records:
                    data_list.append({
                        'timestamp': record.get_time(),
                        'sensor_id': record.tags.get('sensor_id', 'unknown'),
                        'sensor_type': record.tags.get('sensor_type', 'unknown'),
                        'location': record.tags.get('location', 'unknown'),
                        'status': record.tags.get('status', 'NORMAL'),
                        'severity': record.tags.get('severity', 'LOW'),
                        'category': record.tags.get('category', 'OTHER'),
                        'operational_state': record.tags.get('operational_state', 'OPTIMAL'),
                        'value': record.values.get('value'),
                        'anomaly': record.values.get('anomaly', 0)
                    })
            
            if data_list:
                df = pd.DataFrame(data_list)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                print(f"✓ Loaded {len(df)} sensor records from InfluxDB")
                return df
            else:
                print("⚠ No sensor data found in InfluxDB")
                return None
                
        except Exception as e:
            print(f"✗ Error querying InfluxDB: {e}")
            return None
    
    def disconnect(self):
        """Disconnect from InfluxDB"""
        if self.client:
            self.client.close()


class FeatureEngineer:
    """Performs feature engineering for time-series sensor data"""
    
    @staticmethod
    def create_time_features(df):
        """Extract temporal features from timestamp"""
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['day_of_month'] = df['timestamp'].dt.day
        df['month'] = df['timestamp'].dt.month
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        return df
    
    @staticmethod
    def create_rolling_statistics(df, window=10):
        """Create rolling window statistics for each sensor"""
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        rolling_features = {}
        for col in ['value', 'anomaly']:
            if col in df.columns:
                rolling_features[f'{col}_rolling_mean'] = df[col].rolling(window=window).mean()
                rolling_features[f'{col}_rolling_std'] = df[col].rolling(window=window).std()
                rolling_features[f'{col}_rolling_min'] = df[col].rolling(window=window).min()
                rolling_features[f'{col}_rolling_max'] = df[col].rolling(window=window).max()
        
        df_rolling = pd.DataFrame(rolling_features)
        return pd.concat([df, df_rolling], axis=1).fillna(method='bfill').fillna(method='ffill')
    
    @staticmethod
    def create_lag_features(df, lags=[1, 5, 10]):
        """Create lagged features for time-series patterns"""
        for lag in lags:
            df[f'value_lag_{lag}'] = df['value'].shift(lag)
            df[f'anomaly_lag_{lag}'] = df['anomaly'].shift(lag)
        
        return df.fillna(method='bfill').fillna(method='ffill')
    
    @staticmethod
    def encode_categorical_features(df, categorical_cols):
        """Encode categorical features"""
        encoders = {}
        for col in categorical_cols:
            if col in df.columns:
                encoder = LabelEncoder()
                df[f'{col}_encoded'] = encoder.fit_transform(df[col].astype(str))
                encoders[col] = encoder
        
        return df, encoders


class ModelRegistry:
    """Manages trained model persistence and versioning"""
    
    def __init__(self, model_dir='models'):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        self.registry_file = self.model_dir / 'model_registry.json'
        self.registry = self._load_registry()
    
    def _load_registry(self):
        """Load model registry from file"""
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_registry(self):
        """Save model registry to file"""
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2, default=str)
    
    def register_model(self, model_name, model_path, model_type, metrics):
        """Register a trained model"""
        model_key = f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.registry[model_key] = {
            'name': model_name,
            'path': str(model_path),
            'type': model_type,
            'created_at': datetime.now().isoformat(),
            'metrics': metrics,
            'active': True
        }
        
        self._save_registry()
        print(f"✓ Model registered: {model_key}")
        return model_key
    
    def save_model(self, model, model_name, scaler=None):
        """Save a model and associated scaler"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_path = self.model_dir / f"{model_name}_{timestamp}.pkl"
        
        joblib.dump(model, model_path)
        print(f"✓ Model saved to {model_path}")
        
        if scaler:
            scaler_path = self.model_dir / f"{model_name}_scaler_{timestamp}.pkl"
            joblib.dump(scaler, scaler_path)
            print(f"✓ Scaler saved to {scaler_path}")
            return model_path, scaler_path
        
        return model_path, None
    
    def get_latest_model(self, model_name):
        """Get the latest version of a model"""
        matching_models = {k: v for k, v in self.registry.items() if model_name in k and v.get('active')}
        
        if not matching_models:
            return None
        
        latest = max(matching_models.items(), key=lambda x: x[1]['created_at'])
        model_path = latest[1]['path']
        
        if os.path.exists(model_path):
            return joblib.load(model_path)
        return None


class BinaryAnomalyDetectionModel:
    """Binary classification model for anomaly detection (Normal vs Anomalous)"""
    
    def __init__(self, registry):
        self.model = None
        self.scaler = None
        self.feature_columns = None
        self.registry = registry
    
    def prepare_data(self, df):
        """Prepare data for training"""
        print("Preparing data for binary classification...")
        
        df_prepared = df.copy()
        
        df_prepared = FeatureEngineer.create_time_features(df_prepared)
        df_prepared = FeatureEngineer.create_rolling_statistics(df_prepared, window=10)
        df_prepared = FeatureEngineer.create_lag_features(df_prepared, lags=[1, 5, 10])
        
        categorical_cols = ['sensor_type', 'category', 'operational_state']
        df_prepared, _ = FeatureEngineer.encode_categorical_features(df_prepared, categorical_cols)
        
        self.feature_columns = [col for col in df_prepared.columns 
                               if col not in ['timestamp', 'sensor_id', 'location', 'status', 
                                            'severity', 'anomaly'] and not col.endswith('_encoded')]
        
        X = df_prepared[self.feature_columns].fillna(0)
        y = df_prepared['anomaly'].astype(int)
        
        print(f"✓ Features prepared: {len(self.feature_columns)} features, {len(y)} samples")
        
        return X, y, df_prepared
    
    def train(self, df):
        """Train binary classification model"""
        print("\n" + "="*60)
        print("Training Binary Anomaly Detection Model")
        print("="*60)
        
        X, y, df_prepared = self.prepare_data(df)
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        self.model = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
        self.model.fit(X_train_scaled, y_train)
        
        y_pred = self.model.predict(X_test_scaled)
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0)
        }
        
        print(f"\nBinary Classification Metrics:")
        print(f"  Accuracy:  {metrics['accuracy']:.4f}")
        print(f"  Precision: {metrics['precision']:.4f}")
        print(f"  Recall:    {metrics['recall']:.4f}")
        print(f"  F1-Score:  {metrics['f1']:.4f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=['Normal', 'Anomaly']))
        
        model_path, scaler_path = self.registry.save_model(self.model, 'binary_anomaly_detector', self.scaler)
        self.registry.register_model('binary_anomaly_detector', model_path, 'RandomForest', metrics)
        
        return metrics


class FineGrainedClassificationModel:
    """Multi-class classification model for operational state classification (7 classes)"""
    
    OPERATIONAL_STATES = [
        'CRITICALLY_LOW',
        'LOW',
        'BELOW_OPTIMAL',
        'OPTIMAL',
        'ABOVE_OPTIMAL',
        'HIGH',
        'CRITICALLY_HIGH'
    ]
    
    def __init__(self, registry):
        self.model = None
        self.scaler = None
        self.feature_columns = None
        self.registry = registry
        self.label_encoder = None
    
    def create_operational_state_labels(self, df):
        """Create operational state labels from sensor values"""
        def classify_state(value):
            if value < 10:
                return 'CRITICALLY_LOW'
            elif value < 20:
                return 'LOW'
            elif value < 30:
                return 'BELOW_OPTIMAL'
            elif value < 70:
                return 'OPTIMAL'
            elif value < 80:
                return 'ABOVE_OPTIMAL'
            elif value < 90:
                return 'HIGH'
            else:
                return 'CRITICALLY_HIGH'
        
        df['operational_state_label'] = df['value'].apply(classify_state)
        return df
    
    def prepare_data(self, df):
        """Prepare data for training"""
        print("Preparing data for fine-grained classification...")
        
        df_prepared = df.copy()
        df_prepared = self.create_operational_state_labels(df_prepared)
        
        df_prepared = FeatureEngineer.create_time_features(df_prepared)
        df_prepared = FeatureEngineer.create_rolling_statistics(df_prepared, window=10)
        df_prepared = FeatureEngineer.create_lag_features(df_prepared, lags=[1, 5, 10])
        
        categorical_cols = ['sensor_type', 'category']
        df_prepared, _ = FeatureEngineer.encode_categorical_features(df_prepared, categorical_cols)
        
        self.feature_columns = [col for col in df_prepared.columns 
                               if col not in ['timestamp', 'sensor_id', 'location', 'status', 
                                            'severity', 'anomaly', 'operational_state_label'] 
                               and not col.endswith('_encoded')]
        
        X = df_prepared[self.feature_columns].fillna(0)
        y = df_prepared['operational_state_label']
        
        print(f"✓ Features prepared: {len(self.feature_columns)} features, {len(y)} samples")
        print(f"✓ Class distribution: {y.value_counts().to_dict()}")
        
        return X, y, df_prepared
    
    def train(self, df):
        """Train fine-grained classification model"""
        print("\n" + "="*60)
        print("Training Fine-Grained Classification Model")
        print("="*60)
        
        X, y, df_prepared = self.prepare_data(df)
        
        self.label_encoder = LabelEncoder()
        y_encoded = self.label_encoder.fit_transform(y)
        
        X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)
        
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        self.model = GradientBoostingClassifier(n_estimators=100, max_depth=7, learning_rate=0.1, random_state=42)
        self.model.fit(X_train_scaled, y_train)
        
        y_pred = self.model.predict(X_test_scaled)
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'macro_precision': precision_score(y_test, y_pred, average='macro', zero_division=0),
            'macro_recall': recall_score(y_test, y_pred, average='macro', zero_division=0),
            'macro_f1': f1_score(y_test, y_pred, average='macro', zero_division=0)
        }
        
        print(f"\nFine-Grained Classification Metrics:")
        print(f"  Accuracy:         {metrics['accuracy']:.4f}")
        print(f"  Macro Precision:  {metrics['macro_precision']:.4f}")
        print(f"  Macro Recall:     {metrics['macro_recall']:.4f}")
        print(f"  Macro F1-Score:   {metrics['macro_f1']:.4f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=self.label_encoder.classes_))
        
        model_path, scaler_path = self.registry.save_model(self.model, 'fine_grained_classifier', self.scaler)
        self.registry.register_model('fine_grained_classifier', model_path, 'GradientBoosting', metrics)
        
        encoder_path = self.registry.model_dir / 'class_label_encoder.pkl'
        joblib.dump(self.label_encoder, encoder_path)
        print(f"✓ Label encoder saved to {encoder_path}")
        
        return metrics


class DailyStatisticsGenerator:
    """Generates daily aggregated statistics and anomaly reports"""
    
    def __init__(self, report_dir='reports'):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True)
    
    def generate_report(self, df):
        """Generate comprehensive daily statistics report"""
        print("\n" + "="*60)
        print("Generating Daily Statistics Report")
        print("="*60)
        
        df_sorted = df.sort_values('timestamp')
        df_sorted['date'] = df_sorted['timestamp'].dt.date
        
        daily_stats = {
            'report_generated_at': datetime.now().isoformat(),
            'data_period': {
                'start': df_sorted['timestamp'].min().isoformat(),
                'end': df_sorted['timestamp'].max().isoformat()
            },
            'summary': {
                'total_records': len(df_sorted),
                'unique_sensors': df_sorted['sensor_id'].nunique(),
                'anomaly_count': int(df_sorted['anomaly'].sum()),
                'anomaly_percentage': float((df_sorted['anomaly'].sum() / len(df_sorted) * 100))
            },
            'by_sensor': {},
            'by_date': {}
        }
        
        for sensor_id in df_sorted['sensor_id'].unique():
            sensor_data = df_sorted[df_sorted['sensor_id'] == sensor_id]
            sensor_type = sensor_data['sensor_type'].iloc[0]
            
            daily_stats['by_sensor'][sensor_id] = {
                'sensor_type': sensor_type,
                'records': len(sensor_data),
                'anomalies': int(sensor_data['anomaly'].sum()),
                'anomaly_percentage': float((sensor_data['anomaly'].sum() / len(sensor_data) * 100)),
                'value_mean': float(sensor_data['value'].mean()),
                'value_min': float(sensor_data['value'].min()),
                'value_max': float(sensor_data['value'].max()),
                'value_std': float(sensor_data['value'].std())
            }
        
        for date in df_sorted['date'].unique():
            date_data = df_sorted[df_sorted['date'] == date]
            
            daily_stats['by_date'][str(date)] = {
                'records': len(date_data),
                'anomalies': int(date_data['anomaly'].sum()),
                'anomaly_percentage': float((date_data['anomaly'].sum() / len(date_data) * 100)),
                'avg_value': float(date_data['value'].mean()),
                'critical_events': int((date_data['severity'] == 'CRITICAL').sum()),
                'high_severity': int((date_data['severity'] == 'HIGH').sum())
            }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = self.report_dir / f'daily_report_{timestamp}.json'
        
        with open(report_path, 'w') as f:
            json.dump(daily_stats, f, indent=2)
        
        print(f"✓ Report saved to {report_path}")
        print(f"  Total Records: {daily_stats['summary']['total_records']}")
        print(f"  Anomalies: {daily_stats['summary']['anomaly_count']} ({daily_stats['summary']['anomaly_percentage']:.2f}%)")
        print(f"  Unique Sensors: {daily_stats['summary']['unique_sensors']}")
        
        return daily_stats


def main():
    """Main batch processing job"""
    print("\n" + "="*60)
    print("Phase 3: Batch Processing & Model Training")
    print("="*60)
    
    influxdb_url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
    influxdb_token = os.getenv('INFLUXDB_TOKEN', 'nt-scada-token-secret-key-12345')
    influxdb_org = os.getenv('INFLUXDB_ORG', 'nt-scada')
    influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'scada_data')
    
    loader = InfluxDBDataLoader(influxdb_url, influxdb_token, influxdb_org, influxdb_bucket)
    
    if not loader.connect():
        print("⚠ InfluxDB not available. Using fallback dummy data...")
        df = create_fallback_data()
    else:
        df = loader.query_sensor_data(time_range="-7d")
        if df is None:
            print("⚠ No data from InfluxDB. Using fallback dummy data...")
            df = create_fallback_data()
        loader.disconnect()
    
    if df is None or len(df) == 0:
        print("✗ No data available for training")
        return
    
    registry = ModelRegistry()
    
    binary_model = BinaryAnomalyDetectionModel(registry)
    binary_metrics = binary_model.train(df)
    
    fine_grained_model = FineGrainedClassificationModel(registry)
    fine_grained_metrics = fine_grained_model.train(df)
    
    stats_generator = DailyStatisticsGenerator()
    daily_stats = stats_generator.generate_report(df)
    
    print("\n" + "="*60)
    print("Batch Processing Completed Successfully!")
    print("="*60)
    print(f"✓ Binary Anomaly Detection: {binary_metrics['accuracy']:.4f} accuracy")
    print(f"✓ Fine-Grained Classification: {fine_grained_metrics['accuracy']:.4f} accuracy")
    print(f"✓ Daily statistics report generated")


def create_fallback_data():
    """Create fallback data for testing"""
    print("Creating fallback test data...")
    np.random.seed(42)
    n_samples = 2000
    
    data = []
    for i in range(n_samples):
        timestamp = datetime.now() - timedelta(days=7) + timedelta(minutes=i)
        sensor_id = f"sensor_{i % 30 + 1}"
        sensor_types = ['temperature', 'pressure', 'flow_rate', 'vibration', 'voltage', 'current']
        sensor_type = sensor_types[(i % 30) % 6]
        
        value = np.random.normal(50, 15)
        anomaly = 1 if (value < 20 or value > 80) else 0
        
        data.append({
            'timestamp': timestamp,
            'sensor_id': sensor_id,
            'sensor_type': sensor_type,
            'location': f"Zone-{(i % 30) // 6 + 1}",
            'status': 'NORMAL' if anomaly == 0 else 'ALARM',
            'severity': 'CRITICAL' if value < 10 or value > 90 else 'HIGH' if value < 20 or value > 80 else 'LOW',
            'category': 'THERMAL_PRESSURE' if sensor_type in ['temperature', 'pressure'] else 'MECHANICAL' if sensor_type in ['flow_rate', 'vibration'] else 'ELECTRICAL',
            'operational_state': 'OPTIMAL',
            'value': max(0, value),
            'anomaly': anomaly
        })
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    main()
