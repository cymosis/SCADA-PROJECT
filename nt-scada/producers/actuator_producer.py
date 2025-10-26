"""
Simple Excel → Kafka Producer
Reads data from an Excel file and sends each row to a Kafka topic.
"""

import pandas as pd
import json
from kafka import KafkaProducer
from datetime import datetime
import time

# Configuration
KAFKA_SERVER = 'localhost:9092'      # Kafka broker
TOPIC = 'scada.actuators'            # Kafka topic
EXCEL_FILE = 'C:\scada-docker\Swat Data\Normal  Data 2023\22June2020 (1).xlsx'    # Path to your Excel file

# Create Kafka producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_SERVER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Load Excel file
df = pd.read_excel(EXCEL_FILE)
print(f"Loaded {len(df)} rows from {EXCEL_FILE}")

# Send each row to Kafka
for i, row in df.iterrows():
    data = row.to_dict()

    # Add a timestamp if not present
    if 'timestamp' not in data:
        data['timestamp'] = datetime.utcnow().isoformat() + 'Z'

    # Send message
    producer.send(TOPIC, value=data)
    print(f"Sent row {i+1}/{len(df)} → {data.get('actuator_id', 'unknown')}")

    # Small delay to simulate streaming
    time.sleep(1)

# Ensure all messages are sent
producer.flush()
print("✅ All messages sent successfully.")
