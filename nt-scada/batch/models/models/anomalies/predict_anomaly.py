"""
NT-SCADA Real-Time Anomaly Detection Service
Continuously monitors InfluxDB and processes each record individually
"""

import os
import time
import pandas as pd
from datetime import datetime, timedelta
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
# Anomaly Detector Class
# -----------------------------
class AnomalyDetector:
    """Use trained model to detect anomalies"""

    def __init__(self, model_path, scaler_path):
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        self.feature_columns = getattr(self.scaler, "feature_names_in_", None)
        print(f"[LOG] ✓ AnomalyDetector: Model and scaler loaded successfully")
        print(f"[LOG] Model path: {model_path}")
        print(f"[LOG] Scaler path: {scaler_path}")
        print(f"[LOG] Feature columns: {self.feature_columns}")

    def predict_single(self, sensor_data, threshold=ANOMALY_THRESHOLD):
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

        print(f"[LOG] Prediction: {pred}, Probability: {anomaly_prob:.2%}")
        #contributing feature

    

        return {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'is_anomaly': bool(anomaly_prob > threshold),
            'anomaly_probability': float(anomaly_prob),
            'prediction_label': 'Attack' if pred == 1 else 'Normal'
        }

# -----------------------------
# Connect to InfluxDB
# -----------------------------
print("[LOG] Waiting for InfluxDB...")
time.sleep(10)  # wait for InfluxDB container to be ready

try:
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    health = client.health()
    print(f"[LOG] InfluxDB health: {health.status}")
except Exception as e:
    print(f"[ERROR] InfluxDB connection failed: {e}")
    exit(1)

query_api = client.query_api()
write_api = client.write_api(write_options=SYNCHRONOUS)

# -----------------------------
# Load pre-trained model
# -----------------------------
print("[LOG] Loading ML model...")
try:
    detector = AnomalyDetector(model_path=MODEL_PATH, scaler_path=SCALER_PATH)
except Exception as e:
    print(f"[ERROR] Model load failed: {e}")
    exit(1)

# -----------------------------
# Real-Time Monitoring Loop
# -----------------------------
print("\n=== NT-SCADA Real-Time Anomaly Detection Started ===")
total_processed = 0
total_anomalies = 0

try:
    while True:
        print("[LOG] Querying records ")
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

            print(f"[LOG] Fetched {len(records)} records from InfluxDB")

            if not records:
                print(f"[LOG] No new records. Sleeping {POLLING_INTERVAL}s...")
                time.sleep(POLLING_INTERVAL)
                continue

            sensor_stream = pd.DataFrame(records)
            print(f"[LOG] DataFrame shape: {sensor_stream.shape}")
            numerical_cols = detector.feature_columns

            for _, row in sensor_stream.iterrows():


                row_numeric = row[numerical_cols].apply(pd.to_numeric, errors='coerce').fillna(0)

                prediction = detector.predict_single(row_numeric)
                total_processed += 1

                if prediction['is_anomaly']:
                    total_anomalies += 1
                    print(f"[ALERT] [{datetime.utcnow().strftime('%H:%M:%S')}] "
                          f"ANOMALY #{total_anomalies} | Prob: {prediction['anomaly_probability']:.2%} | Total: {total_processed}")
                    row_time = datetime.utcnow()
                    point = Point("actuator_data")\
                        .tag("source", "real_time_detection")\
                        .tag("prediction_label", prediction['prediction_label'])\
                        .field("anomaly_probability", float(prediction['anomaly_probability']))\
                        .field("is_anomaly", 1)\
                        .time(row_time, WritePrecision.NS)

                    for col, val in row.items():
                        if col not in ['_time', '_field', '_value', '_measurement']:
                            try:
                                if pd.notna(val):
                                    point.field(col, float(val) if isinstance(val, (int, float)) else str(val))
                            except Exception as e:
                                print(f"[WARN] Failed to write field {col}: {e}")

                    try:
                        write_api.write(bucket=ANOMALY_BUCKET, org=INFLUXDB_ORG, record=point)
                        print(f"[LOG] Anomaly written to bucket '{ANOMALY_BUCKET}'")
                    except Exception as e:
                        print(f"[ERROR] Write error: {e}")



        except Exception as e:
            print(f"[ERROR] Query error: {e}")
            import traceback
            traceback.print_exc()

        time.sleep(POLLING_INTERVAL)

except KeyboardInterrupt:
    print("\n[LOG] Shutting down...")
    client.close()
    print(f"[LOG] Processed: {total_processed}, Anomalies: {total_anomalies}")
except Exception as e:
    print(f"[FATAL] {e}")
    import traceback
    traceback.print_exc()
    client.close()