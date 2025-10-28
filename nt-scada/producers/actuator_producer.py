"""
Excel → Kafka Producer
Reads an Excel file and sends each row to a Kafka topic as JSON.
"""

import pandas as pd
import json
from kafka import KafkaProducer
import time

# -----------------------------
# Configuration
# -----------------------------
KAFKA_SERVER = 'localhost:9092'  # Kafka broker
TOPIC = 'scada.actuators_v2'    # Kafka topic
EXCEL_FILE = 'C:/scada-docker/Swat Data/Normal  Data 2023/22June2020 (1).xlsx'
STREAM_DELAY = 1  # seconds between messages to simulate streaming

# -----------------------------
# Create Kafka Producer
# -----------------------------
producer = KafkaProducer(
    bootstrap_servers=KAFKA_SERVER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# -----------------------------
# Load Excel File
# -----------------------------
df = pd.read_excel(EXCEL_FILE)
print(f"Loaded {len(df)} rows from {EXCEL_FILE}")

# -----------------------------
# Send Each Row to Kafka
# -----------------------------
for i, row in df.iterrows():
    data = row.to_dict()

    # Convert NaN → None
    data = {k: (None if pd.isna(v) else v) for k, v in data.items()}

    # Convert 't_stamp' column to ISO string
    if 't_stamp' in data and data['t_stamp'] is not None:
        data['t_stamp'] = pd.to_datetime(data['t_stamp']).isoformat()

    # Send to Kafka
    producer.send(TOPIC, value=data)

    # Optional delay to simulate streaming
    time.sleep(STREAM_DELAY)

    # Print progress every 100 messages
    if (i + 1) % 100 == 0:
        print(f"Sent {i + 1} messages")

# -----------------------------
# Flush Producer and Finish
# -----------------------------
producer.flush()
print(f"✅ All {len(df)} messages sent to Kafka topic '{TOPIC}'.")
