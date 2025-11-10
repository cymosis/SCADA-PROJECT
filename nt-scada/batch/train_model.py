#!/usr/bin/env python3
"""
Batch ML Model Training for NT-SCADA
Trains binary classification and fine-grained classification models
"""

import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import warnings
warnings.filterwarnings('ignore')

print("Starting NT-SCADA Batch Model Training...")

# TODO: Replace with actual data loading from InfluxDB
# For now, we'll create dummy data to test the pipeline
def create_dummy_data():
    """Create dummy sensor data for testing"""
    np.random.seed(42)
    n_samples = 1000
    
    # Simulate sensor readings (temperature, pressure, flow, etc.)
    data = {
        'timestamp': pd.date_range('2024-01-01', periods=n_samples, freq='1min'),
        'temperature': np.random.normal(50, 10, n_samples),
        'pressure': np.random.normal(100, 20, n_samples),
        'flow_rate': np.random.normal(30, 5, n_samples),
        'vibration': np.random.normal(5, 2, n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Binary classification: Normal (0) vs Anomalous (1)
    df['binary_label'] = np.random.choice([0, 1], n_samples, p=[0.9, 0.1])
    
    # Fine-grained classification: Multiple anomaly types
    conditions = [
        (df['temperature'] > 65) & (df['pressure'] > 130),
        (df['flow_rate'] < 20) & (df['vibration'] > 8),
        (df['temperature'] < 35) & (df['pressure'] < 70),
        (df['flow_rate'] > 40) & (df['vibration'] < 2)
    ]
    choices = [1, 2, 3, 4]  # Different anomaly types
    df['fine_grained_label'] = np.select(conditions, choices, default=0)
    
    return df

def train_binary_classification(df):
    """Train binary classification model (Normal vs Anomalous)"""
    print("Training Binary Classification Model...")
    
    # Features and target
    features = ['temperature', 'pressure', 'flow_rate', 'vibration']
    X = df[features]
    y = df['binary_label']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Binary Classification Accuracy: {accuracy:.4f}")
    print(classification_report(y_test, y_pred))
    
    # Save model
    joblib.dump(model, 'models/binary_classifier.pkl')
    print("Binary classification model saved to models/binary_classifier.pkl")
    
    return model

def train_fine_grained_classification(df):
    """Train fine-grained classification model"""
    print("Training Fine-Grained Classification Model...")
    
    # Features and target
    features = ['temperature', 'pressure', 'flow_rate', 'vibration']
    X = df[features]
    y = df['fine_grained_label']
    
    # Only train if we have multiple classes
    if len(y.unique()) > 1:
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train model
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Fine-Grained Classification Accuracy: {accuracy:.4f}")
        print(classification_report(y_test, y_pred))
        
        # Save model
        joblib.dump(model, 'models/fine_grained_classifier.pkl')
        print("Fine-grained classification model saved to models/fine_grained_classifier.pkl")
        
        return model
    else:
        print("Not enough classes for fine-grained classification")
        return None

def generate_daily_statistics(df):
    """Generate daily statistics report"""
    print("Generating Daily Statistics...")
    
    # Set timestamp as index
    df = df.set_index('timestamp')
    
    # Resample by day and calculate statistics
    daily_stats = df.resample('D').agg({
        'temperature': ['mean', 'min', 'max', 'std'],
        'pressure': ['mean', 'min', 'max', 'std'],
        'flow_rate': ['mean', 'min', 'max', 'std'],
        'vibration': ['mean', 'min', 'max', 'std'],
        'binary_label': 'sum'  # Count anomalies
    })
    
    # Flatten column names
    daily_stats.columns = ['_'.join(col).strip() for col in daily_stats.columns.values]
    
    # Save to CSV
    daily_stats.to_csv('reports/daily_statistics.csv')
    print("Daily statistics saved to reports/daily_statistics.csv")
    
    return daily_stats

if __name__ == "__main__":
    print("NT-SCADA Batch Processing Started")
    
    # Create dummy data (replace with actual InfluxDB query later)
    df = create_dummy_data()
    print(f"Created dataset with {len(df)} samples")
    
    # Train models
    binary_model = train_binary_classification(df)
    fine_grained_model = train_fine_grained_classification(df)
    
    # Generate statistics
    stats = generate_daily_statistics(df)
    
    print("NT-SCADA Batch Processing Completed Successfully!")