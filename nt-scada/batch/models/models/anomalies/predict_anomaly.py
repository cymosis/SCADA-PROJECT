"""
NT-SCADA Real-Time Anomaly Detection Service
Uses statistical deviation from normal to explain anomalies
No external dependencies beyond your current stack
"""

import os
import time
import pandas as pd
import numpy as np
from datetime import datetime
import joblib
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# -----------------------------
# Configuration
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "binary_classifier.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")

INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'mytoken')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'scada')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', 'normal_data')
ANOMALY_BUCKET = os.getenv('ANOMALY_BUCKET', 'anomaly_data')
POLLING_INTERVAL = int(os.getenv('POLLING_INTERVAL', '5'))
ANOMALY_THRESHOLD = float(os.getenv('ANOMALY_THRESHOLD', '0.07'))

# -----------------------------
# Anomaly Detector Class (with Deviation-Based Explanation)
# -----------------------------
class AnomalyDetector:
    """Detect anomalies + explain using deviation from learned normal behavior"""

    def __init__(self, model_path, scaler_path):
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        
        # Extract feature names and statistics from scaler
        self.feature_columns = getattr(self.scaler, "feature_names_in_", None)
        if self.feature_columns is None:
            raise ValueError("Scaler must have feature_names_in_ (use sklearn >= 0.24 and fit with DataFrame)")
        
        self.mean_ = self.scaler.mean_
        self.scale_ = np.sqrt(self.scaler.var_) + 1e-8  # Avoid division by zero

        print(f"[LOG] Model and scaler loaded successfully")
        print(f"[LOG] Features ({len(self.feature_columns)}): {list(self.feature_columns)}")

    def predict_single(self, sensor_data, threshold=ANOMALY_THRESHOLD):
        df = pd.DataFrame([sensor_data])
        
        # Align columns exactly as during training
        for col in self.feature_columns:
            if col not in df.columns:
                df[col] = 0
        df = df[self.feature_columns]
        X_raw = df.values[0]  # Raw values (before scaling)
        X_scaled = self.scaler.transform(df)

        # Model prediction
        pred = self.model.predict(X_scaled)[0]
        proba = self.model.predict_proba(X_scaled)[0]
        anomaly_prob = proba[1] if len(proba) > 1 else proba[0]

        # === Contributing Features: Deviation from Normal (in scaled space) ===
        deviations = np.abs(X_scaled[0] - self.mean_) / self.scale_
        top_indices = np.argsort(deviations)[-5:][::-1]  # Top 5 most deviant

        top_contributors = []
        for idx in top_indices:
            feature_name = self.feature_columns[idx]
            raw_value = float(X_raw[idx])
            deviation_score = float(deviations[idx])
            z_score = float((X_scaled[0][idx] - self.mean_[idx]) / self.scale_[idx])
            top_contributors.append({
                "feature": feature_name,
                "value": raw_value,
                "deviation": deviation_score,
                "z_score": z_score
            })

        return {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'is_anomaly': bool(anomaly_prob > threshold),
            'anomaly_probability': float(anomaly_prob),
            'prediction_label': 'Attack' if pred == 1 else 'Normal',
            'top_contributors': top_contributors  # Now included!
        }


# -----------------------------
# Connect to InfluxDB
# -----------------------------
print("[LOG] Waiting for InfluxDB to start...")
time.sleep(10)

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
try:
    health = client.health()
    print(f"[LOG] InfluxDB connected - Status: {health.status}")
except Exception as e:
    print(f"[ERROR] Cannot connect to InfluxDB: {e}")
    exit(1)

query_api = client.query_api()
write_api = client.write_api(write_options=SYNCHRONOUS)

# -----------------------------
# Load Model
# -----------------------------
print("[LOG] Loading anomaly detection model...")
try:
    detector = AnomalyDetector(MODEL_PATH, SCALER_PATH)
except Exception as e:
    print(f"[ERROR] Failed to load model/scaler: {e}")
    exit(1)

# -----------------------------
# Real-Time Monitoring Loop
# -----------------------------
print("\n=== NT-SCADA Real-Time Anomaly Detection STARTED ===\n")
total_processed = 0
total_anomalies = 0

try:
    while True:
        print(f"[LOG] {datetime.utcnow().strftime('%H:%M:%S')} - Querying new records...")
        query = (
            f'from(bucket: "{INFLUXDB_BUCKET}") '
            f'|> range(start: 0) '
            f'|> filter(fn: (r) => r._measurement == "actuator_data") '
            f'|> sort(columns: ["_stop"], desc: true) '
            f'|> limit(n:5) '
            f'|> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")'
            f'|> drop(columns: ["_start","_stop","result","table","_measurement"])'
        )

        try:
            result = query_api.query(query=query)
            records = []
            for table in result:
                for record in table.records:
                    records.append(record.values)

            if not records:
                print(f"[LOG] No new data. Sleeping {POLLING_INTERVAL}s...")
                time.sleep(POLLING_INTERVAL)
                continue

            df_stream = pd.DataFrame(records)
            print(f"[LOG] Fetched {len(df_stream)} new records")

            for _, row in df_stream.iterrows():
                # Convert to numeric, fill NaN
                sensor_values = row.drop(labels=['_time'], errors='ignore')
                numeric_data = pd.to_numeric(sensor_values, errors='coerce').fillna(0)

                prediction = detector.predict_single(numeric_data.to_dict())

                total_processed += 1

                if prediction['is_anomaly']:
                    total_anomalies += 1
                    contributors = prediction['top_contributors']

                    print(f"\n[ALERT] ANOMALY DETECTED #{total_anomalies}")
                    print(f"[ALERT] Time      : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    print(f"[ALERT] Probability: {prediction['anomaly_probability']:.2%}")
                    print(f"[ALERT] Label      : {prediction['prediction_label']}")
                    print(f"[ALERT] Top Contributing Sensors (Most Deviant from Normal):")
                    for i, c in enumerate(contributors, 1):
                        direction = "high" if c['z_score'] > 0 else "low"
                        print(f"    {i}. {c['feature']}: {c['value']:.3f} (z={c['z_score']:+.2f}, {direction})")

                    # Write anomaly to dedicated bucket
                    point = Point("anomaly_alert") \
                        .tag("prediction_label", prediction['prediction_label']) \
                        .tag("source", "real_time_detector") \
                        .field("anomaly_probability", prediction['anomaly_probability']) \
                        .field("is_anomaly", 1) \
                        .time(datetime.utcnow(), WritePrecision.NS)

                    # Add top contributors as tags/fields
                    for i, c in enumerate(contributors[:3], 1):
                        point = point.tag(f"top_contributor_{i}", c['feature'])
                        point = point.field(f"contributor_{i}_value", c['value'])
                        point = point.field(f"contributor_{i}_zscore", c['z_score'])

                    # Add original sensor values
                    for col, val in numeric_data.items():
                        if col in detector.feature_columns:
                            point = point.field(col, float(val))

                    write_api.write(bucket=ANOMALY_BUCKET, org=INFLUXDB_ORG, record=point)
                    print(f"[LOG] Anomaly saved to '{ANOMALY_BUCKET}' bucket\n")

        except Exception as e:
            print(f"[ERROR] Query/Processing error: {e}")
            import traceback
            traceback.print_exc()

        time.sleep(POLLING_INTERVAL)

except KeyboardInterrupt:
    print("\n[LOG] Service stopped by user")
except Exception as e:
    print(f"[FATAL] {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
    print(f"[SUMMARY] Total Processed: {total_processed} | Anomalies Detected: {total_anomalies}")