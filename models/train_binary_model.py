"""
Batch Processing 1: Train Binary Classification Model

This script trains a binary classifier to detect anomalies in sensor data.
Classification: Normal (0) vs Attack/Anomaly (1)
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
import os
from datetime import datetime

# Configuration
DATASET_PATH = r'..\data\swat\Normal Data 2023\22June2020 (1).xlsx'
ATTACK_DATASET_PATH = r'..\data\swat\Attack Data 2019\SWaT_dataset_Jul 19 v2.xlsx'
MODEL_OUTPUT_PATH = '../models/binary_classifier.pkl'
SCALER_OUTPUT_PATH = '../models/scaler.pkl'
REPORT_OUTPUT_PATH = '../models/binary_classification_report.txt'


def load_and_prepare_data():
    """Load and prepare the SWaT dataset for binary classification."""
    
    print("📂 Loading datasets...")
    
    # Load normal data
    try:
        normal_df = pd.read_excel(DATASET_PATH)  # Adjust delimiter if needed
        print(f"✅ Loaded normal data: {normal_df.shape}")
        normal_df['label'] = 0  # Normal
    except FileNotFoundError:
        print(f"⚠️  Normal dataset not found at {DATASET_PATH}")
        print("Using synthetic data for demonstration...")
        normal_df = generate_synthetic_data(n_samples=1000, is_normal=True)
        normal_df['label'] = 0
    
    # Load attack data
    try:
        attack_df = pd.read_excel(ATTACK_DATASET_PATH)
        print(f"✅ Loaded attack data: {attack_df.shape}")
        attack_df['label'] = 1  # Attack
    except FileNotFoundError:
        print(f"⚠️  Attack dataset not found at {ATTACK_DATASET_PATH}")
        print("Using synthetic data for demonstration...")
        attack_df = generate_synthetic_data(n_samples=200, is_normal=False)
        attack_df['label'] = 1
    
    # Combine datasets
    df = pd.concat([normal_df, attack_df], ignore_index=True)
    print(f"📊 Combined dataset: {df.shape}")
    
    # Remove timestamp and non-numeric columns
    exclude_cols = ['Timestamp', 't_stamp', 'Date', 'Time', 'label', 'Normal/Attack', 'Label']
    
    # Get common features between both datasets
    normal_features = set([col for col in normal_df.columns if col not in exclude_cols])
    attack_features = set([col for col in attack_df.columns if col not in exclude_cols])
    
    # Use only common features that exist in both datasets
    feature_columns = sorted(list(normal_features.intersection(attack_features)))
    
    print(f"📊 Common features found: {len(feature_columns)}")
    print(f"📋 Feature names: {feature_columns[:10]}...")
    X = df[feature_columns]
    y = df['label']
    
    # Convert to numeric
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce')
    

    # Handle missing values with mean
    X = X.fillna(X.mean(numeric_only=True))
    X = X.fillna(0) # Fill any remaining NaN with 0
    
    print(f"✅ Features: {X.shape[1]}")
    print(f"✅ Samples: {X.shape[0]}")
    print(f"📊 Class distribution: {y.value_counts().to_dict()}")
    
    return X, y, feature_columns


def generate_synthetic_data(n_samples=1000, is_normal=True):
    """Generate synthetic sensor data for testing when real data is unavailable."""
    
    sensor_names = [
        'FIT-101', 'LIT-101', 'MV-101', 'P-101', 'P-102',
        'AIT-201', 'AIT-202', 'AIT-203', 'FIT-201', 'FIT-301',
        'LIT-301', 'MV-301', 'P-301', 'P-302', 'AIT-401'
    ]
    
    data = {}
    
    for sensor in sensor_names:
        if is_normal:
            # Normal operating conditions
            if sensor.startswith('FIT'):  # Flow sensors
                data[sensor] = np.random.normal(2.5, 0.3, n_samples)
            elif sensor.startswith('LIT'):  # Level sensors
                data[sensor] = np.random.normal(500, 50, n_samples)
            elif sensor.startswith('P-'):  # Pumps (binary)
                data[sensor] = np.random.choice([0, 1, 2], n_samples, p=[0.1, 0.7, 0.2])
            elif sensor.startswith('AIT'):  # Analyzers
                data[sensor] = np.random.normal(300, 20, n_samples)
            elif sensor.startswith('MV'):  # Motorized valves
                data[sensor] = np.random.choice([0, 1, 2], n_samples, p=[0.2, 0.6, 0.2])
        else:
            # Attack/Anomalous conditions
            if sensor.startswith('FIT'):
                data[sensor] = np.random.normal(2.5, 1.5, n_samples)  # Higher variance
                # Add some extreme values
                anomaly_idx = np.random.choice(n_samples, size=int(n_samples * 0.1))
                data[sensor][anomaly_idx] = np.random.choice([-1, 6, 10], size=len(anomaly_idx))
            elif sensor.startswith('LIT'):
                data[sensor] = np.random.normal(500, 150, n_samples)
                anomaly_idx = np.random.choice(n_samples, size=int(n_samples * 0.1))
                data[sensor][anomaly_idx] = np.random.choice([0, 1100], size=len(anomaly_idx))
            elif sensor.startswith('P-'):
                data[sensor] = np.random.choice([0, 1, 2, 3], n_samples, p=[0.3, 0.3, 0.3, 0.1])
            elif sensor.startswith('AIT'):
                data[sensor] = np.random.normal(300, 80, n_samples)
            elif sensor.startswith('MV'):
                data[sensor] = np.random.choice([0, 1, 2, 3], n_samples, p=[0.3, 0.3, 0.3, 0.1])
    
    return pd.DataFrame(data)


def train_model(X_train, y_train):
    """Train the binary classification model."""
    
    print("\n🤖 Training Random Forest Classifier...")
    
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight='balanced'  # Handle class imbalance
    )
    
    model.fit(X_train, y_train)
    
    print("✅ Model trained successfully")
    
    return model


def evaluate_model(model, X_test, y_test, feature_names):
    """Evaluate the model and generate reports."""
    
    print("\n📊 Evaluating model...")
    
    # Predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Metrics
    print("\n📈 Classification Report:")
    report = classification_report(y_test, y_pred, target_names=['Normal', 'Attack'])
    print(report)
    
    print("\n📊 Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(cm)
    
    # ROC-AUC Score
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\n🎯 ROC-AUC Score: {roc_auc:.4f}")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n🔝 Top 10 Important Features:")
    print(feature_importance.head(10))
    
    return report, cm, roc_auc, feature_importance


def save_model_and_report(model, scaler, report, cm, roc_auc, feature_importance):
    """Save the trained model and evaluation reports."""
    
    # Create models directory if it doesn't exist
    os.makedirs(os.path.dirname(MODEL_OUTPUT_PATH), exist_ok=True)
    
    # Save model
    joblib.dump(model, MODEL_OUTPUT_PATH)
    print(f"\n💾 Model saved to: {MODEL_OUTPUT_PATH}")
    
    # Save scaler
    joblib.dump(scaler, SCALER_OUTPUT_PATH)
    print(f"💾 Scaler saved to: {SCALER_OUTPUT_PATH}")
    
    # Save report
    with open(REPORT_OUTPUT_PATH, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("NT-SCADA Binary Classification Model - Training Report\n")
        f.write("=" * 80 + "\n")
        f.write(f"Training Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Model Type: Random Forest Classifier\n")
        f.write(f"ROC-AUC Score: {roc_auc:.4f}\n")
        f.write("\n" + "=" * 80 + "\n")
        f.write("Classification Report:\n")
        f.write("=" * 80 + "\n")
        f.write(report)
        f.write("\n" + "=" * 80 + "\n")
        f.write("Confusion Matrix:\n")
        f.write("=" * 80 + "\n")
        f.write(str(cm))
        f.write("\n" + "=" * 80 + "\n")
        f.write("Feature Importance (Top 20):\n")
        f.write("=" * 80 + "\n")
        f.write(feature_importance.head(20).to_string())
        f.write("\n")
    
    print(f"📄 Report saved to: {REPORT_OUTPUT_PATH}")


def main():
    """Main function to train the binary classification model."""
    
    print("=" * 80)
    print("🎯 NT-SCADA Binary Classification Model Training (Batch 1)")
    print("=" * 80)
    
    # Load and prepare data
    X, y, feature_names = load_and_prepare_data()
    
    # Split data
    print("\n📊 Splitting data into train/test sets...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    print(f"Training set: {X_train.shape[0]} samples")
    print(f"Test set: {X_test.shape[0]} samples")
    
    # Scale features
    print("\n⚖️  Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train model
    model = train_model(X_train_scaled, y_train)
    
    # Evaluate model
    report, cm, roc_auc, feature_importance = evaluate_model(
        model, X_test_scaled, y_test, feature_names
    )
    
    # Save model and reports
    save_model_and_report(model, scaler, report, cm, roc_auc, feature_importance)
    
    print("\n" + "=" * 80)
    print("✅ Binary classification model training completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
