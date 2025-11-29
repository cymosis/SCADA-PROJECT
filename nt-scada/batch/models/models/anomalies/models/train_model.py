"""
NT-SCADA Batch Analytics and Model Training (Debug Version)
Performs batch time-series analytics on historical data
Trains binary and multi-class classification models
Generates daily statistics and reports
"""

import os
import pickle
import json
import joblib
from datetime import datetime, timedelta
import time
import numpy as np
import pandas as pd
from influxdb_client import InfluxDBClient
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore')

# -----------------------------
# InfluxDB configuration
# -----------------------------
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "mytoken")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "scada")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "normal_data")
ATTACK_BUCKET = os.getenv("ATTACK_BUCKET", "attack_data")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Models and reports folders
MODEL_DIR = os.path.join(BASE_DIR, "models")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

# Paths for files
MODEL_OUTPUT_PATH = os.path.join(MODEL_DIR, "binary_classifier.pkl")
SCALER_OUTPUT_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
REPORT_OUTPUT_PATH = os.path.join(REPORT_DIR, "binary_classification_report.txt")

# Make sure directories exist
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# Module-level InfluxDB connection moved to main() to prevent execution on import
# -----------------------------
# Connect to InfluxDB
# -----------------------------
client = InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)

health = client.health()
print("InfluxDB health:", health.status)

# -----------------------------
# Simple query: last 10 records
# -----------------------------
query_api = client.query_api()
query = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: 60)             // last 1 day
  |> filter(fn: (r) => r._measurement == "actuator_data")
  |> limit(n:10)
  |> pivot(
        rowKey: ["_time"],
        columnKey: ["_field"],
        valueColumn: "_value"
    )
|> drop(columns: ["_start","_stop","result","table","_measurement"])

'''

result = query_api.query(query=query)

# Convert to DataFrame
records = []
for table in result:
    for record in table.records:
        records.append(record.values)

normal_df = pd.DataFrame(records)
print("Query result:")
print(normal_df.shape)
#================================================
# Simple query: last 10 records
# -----------------------------

query1 = f'''
from(bucket: "{ATTACK_BUCKET}")
  |> range(start: time(v: 0))           // last 1 day
  |> filter(fn: (r) => r._measurement == "actuator_data")
  |> limit(n:10)
  |> pivot(
        rowKey: ["_time"],
        columnKey: ["_field"],
        valueColumn: "_value"
    )
|> drop(columns: ["_start","_stop","result","table","_measurement"])

'''

result1 = query_api.query(query=query1)

# Convert to DataFrame
records1 = []
for table in result1:
    for record in table.records:
        records1.append(record.values)

attack_df = pd.DataFrame(records1)
print("Attack Query result:")
print(attack_df.shape)

#=================================================================================
# -----------------------------
# Prepare data
# -----------------------------
def load_and_prepare_data():
    normal_df['Attack'] = 0
    attack_df['Attack'] = 1
    df = pd.concat([normal_df, attack_df], ignore_index=True)
    print(f"Combined dataset: {df.shape}")

    exclude_cols = ['Timestamp', 't_stamp', 'Date', 'Time', 'label', 'Attack']

    normal_features = set([col for col in normal_df.columns if col not in exclude_cols])
    attack_features = set([col for col in attack_df.columns if col not in exclude_cols])

    feature_columns = sorted(list(normal_features.intersection(attack_features)))

    print(f"Common features found: {len(feature_columns)}")
    print(f"Feature names: {feature_columns[:10]}...")
    X = df[feature_columns]
    y = df['Attack']

    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce')

    X = X.fillna(X.mean(numeric_only=True))

    print(f"Features: {X.shape[1]}, Samples: {X.shape[0]}")
    print(f"Class distribution: {y.value_counts().to_dict()}")

    return X, y, feature_columns

# -----------------------------
# Train model
# -----------------------------
def train_model(X_train, y_train):
    print("\nTraining Random Forest Classifier...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight='balanced'
    )
    model.fit(X_train, y_train)
    print("Model trained successfully")
    return model

# -----------------------------
# Evaluate model
# -----------------------------
def evaluate_model(model, X_test, y_test, feature_names):
    print("\nEvaluating model...")
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    print("\nClassification Report:")
    report = classification_report(y_test, y_pred, target_names=['Normal', 'Attack'])
    print(report)

    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(cm)

    roc_auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\nROC-AUC Score: {roc_auc:.4f}")

    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    print("\nTop 10 Important Features:")
    print(feature_importance.head(10))

    return report, cm, roc_auc, feature_importance

# -----------------------------
# Save model and report
# -----------------------------
def save_model_and_report(model, scaler, report, cm, roc_auc, feature_importance):
    joblib.dump(model, MODEL_OUTPUT_PATH)
    print(f"Model saved to: {MODEL_OUTPUT_PATH}")

    joblib.dump(scaler, SCALER_OUTPUT_PATH)
    print(f"Scaler saved to: {SCALER_OUTPUT_PATH}")

    with open(REPORT_OUTPUT_PATH, 'w') as f:
        f.write("="*80 + "\n")
        f.write("NT-SCADA Binary Classification Model - Training Report\n")
        f.write("="*80 + "\n")
        f.write(f"Training Date: {datetime.now()}\n")
        f.write(f"Model Type: Random Forest Classifier\n")
        f.write(f"ROC-AUC Score: {roc_auc:.4f}\n\n")
        f.write("Classification Report:\n")
        f.write("="*80 + "\n")
        f.write(report)
        f.write("\nConfusion Matrix:\n")
        f.write(str(cm))
        f.write("\nFeature Importance (Top 20):\n")
        f.write(feature_importance.head(20).to_string())
    print(f"Report saved to: {REPORT_OUTPUT_PATH}")

# -----------------------------
# Anomaly Detector Class
# -----------------------------
class AnomalyDetector:
    """Use trained model to detect anomalies"""

    def __init__(self, model_path="models/binary_classifier.pkl", scaler_path="models/scaler.pkl"):
        import joblib
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        self.feature_columns = getattr(self.scaler, "feature_names_in_", None)
        print("✓ AnomalyDetector: Model and scaler loaded successfully")

    def predict_single(self, sensor_data, threshold =0.07):
        df = pd.DataFrame([sensor_data])

        if self.feature_columns is not None:
            for col in self.feature_columns:
                if col not in df.columns:
                    df[col] = 0
            df = df[self.feature_columns]

        X_scaled = self.scaler.transform(df)
        pred = self.model.predict(X_scaled)[0]
        proba = self.model.predict_proba(X_scaled)[0]
        anomaly_prob = proba[1] if len(proba) > 1 else proba[0]

        return {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'is_anomaly': bool(anomaly_prob >threshold),
            'anomaly_probability': float(anomaly_prob),
            'prediction_label': 'Attack' if pred == 1 else 'Normal'
        }

    def predict_batch(self, sensor_data_list):
        df = pd.DataFrame(sensor_data_list)
        if self.feature_columns is not None:
            for col in self.feature_columns:
                if col not in df.columns:
                    df[col] = 0
            df = df[self.feature_columns]

        X_scaled = self.scaler.transform(df)
        preds = self.model.predict(X_scaled)
        probs = self.model.predict_proba(X_scaled)

        results = []
        for pred, proba in zip(preds, probs):
            anomaly_prob = proba[1] if len(proba) > 1 else proba[0]
            results.append({
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'is_anomaly': bool(pred == 1),
                'anomaly_probability': float(anomaly_prob),
                'prediction_label': 'Attack' if pred == 1 else 'Normal'
            })
        return results

# -----------------------------
# Main training pipeline
# -----------------------------
def main():
    print("="*80)
    print("NT-SCADA Binary Classification Model Training (Batch 1)")
    print("="*80)

    X, y, feature_names = load_and_prepare_data()

    print("\nSplitting data into train/test sets...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    print(f"Training set: {X_train.shape[0]} samples, Test set: {X_test.shape[0]} samples")

    print("\nScaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = train_model(X_train_scaled, y_train)

    report, cm, roc_auc, feature_importance = evaluate_model(model, X_test_scaled, y_test, feature_names)

    save_model_and_report(model, scaler, report, cm, roc_auc, feature_importance)

    print("\nBinary classification model training completed successfully!")
    print("="*80)

if __name__ == "__main__":
    main()
