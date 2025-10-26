"""
Kafka → InfluxDB Stream Consumer
Consumes actuator messages from Kafka and writes them to InfluxDB
Handles nested JSON and converts numeric fields to float to avoid type conflicts
"""

import json
from kafka import KafkaConsumer
from influxdb_client import InfluxDBClient, Point, WritePrecision
from datetime import datetime
import os

# Kafka Configuration
KAFKA_SERVER = os.getenv("KAFKA_SERVER", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "scada.actuators")
GROUP_ID = os.getenv("KAFKA_GROUP", "actuator-to-influx")

# InfluxDB Configuration
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "nt-scada-token-secret-key-12345")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "nt-scada")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "scada_data_v2")

# Create Kafka consumer
consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=[KAFKA_SERVER],
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    group_id=GROUP_ID,
    auto_offset_reset="earliest",
    enable_auto_commit=True
)

# Create InfluxDB client
client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client.write_api(write_options=None)

print(f"✓ Connected to Kafka topic '{TOPIC}' at {KAFKA_SERVER}")
print(f"✓ Connected to InfluxDB bucket '{INFLUXDB_BUCKET}' at {INFLUXDB_URL}")

def process_message(msg):
    """
    Flatten nested metadata and convert numeric fields to float
    """
    data = msg.copy()
    
    # Flatten metadata
    metadata = data.pop("metadata", {})
    for key, value in metadata.items():
        data[key] = value
    
    # Convert numeric fields to float to avoid type conflicts
    for key in ["analog_output", "digital_output", "cycle_count"]:
        if key in data and data[key] is not None:
            data[key] = float(data[key])
    
    return data

def to_influx_point(data):
    """
    Convert a processed message into an InfluxDB Point
    """
    timestamp = data.pop("timestamp", datetime.utcnow().isoformat() + "Z")
    point = Point("actuator_data").time(timestamp, WritePrecision.NS)
    
    # Tags (categorical fields)
    for tag in ["actuator_id", "actuator_type", "state", "health", "location", "command_type"]:
        if tag in data:
            point.tag(tag, str(data[tag]))
    
    # Fields (numeric values)
    for field, value in data.items():
        if isinstance(value, (int, float)):
            point.field(field, value)
    
    return point

# Consume messages and write to InfluxDB
try:
    count = 0
    for message in consumer:
        msg = message.value
        processed = process_message(msg)
        point = to_influx_point(processed)
        
        # Write to InfluxDB
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        count += 1
        
        if count % 10 == 0:
            print(f"✓ Written {count} messages to InfluxDB. Latest: {processed.get('actuator_id')}")
except KeyboardInterrupt:
    print("⚠ Stopping consumer...")
finally:
    consumer.close()
    client.close()
    print(f"✅ Consumer stopped. Total messages written: {count}")
