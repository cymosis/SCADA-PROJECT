import json
import os
from datetime import datetime
from kafka import KafkaConsumer
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# -----------------------------
# Configuration
# -----------------------------
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = 'scada.normal'  # Topic for normal data
KAFKA_GROUP_ID = 'normal-data-consumer'

INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'nt-scada-token-secret-key-12345')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'nt-scada')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', 'scada_data_normal')

# Keys to store as tags
TAG_KEYS = ["P1_STATE", "P2_STATE", "P3_STATE", "P4_STATE", "P5_STATE", "P6_STATE"]

# -----------------------------
# Kafka Consumer Setup
# -----------------------------
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    auto_offset_reset='earliest',
    group_id=KAFKA_GROUP_ID,
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
)
print(f"✓ Connected to Kafka topic '{KAFKA_TOPIC}' at {KAFKA_BOOTSTRAP_SERVERS}")

# -----------------------------
# InfluxDB Client Setup
# -----------------------------
client = InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)
write_api = client.write_api(write_options=SYNCHRONOUS)
print(f"✓ Connected to InfluxDB bucket '{INFLUXDB_BUCKET}' at {INFLUXDB_URL}")

# -----------------------------
# Consume and Write Loop
# -----------------------------
message_count = 0

try:
    for msg in consumer:
        data = msg.value

        # Create InfluxDB Point
        point = Point("normal_data")  # Measurement for normal data

        # Add tags dynamically
        for tag_key in TAG_KEYS:
            if tag_key in data:
                point.tag(tag_key, str(data[tag_key]))

        # Add fields
        for key, value in data.items():
            if key == "t_stamp" and value:
                if isinstance(value, str):
                    try:
                        value = datetime.fromisoformat(value)
                    except ValueError:
                        value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                point.time(value, WritePrecision.NS)
            elif key not in TAG_KEYS:
                if isinstance(value, (int, float)):
                    point.field(key, float(value))
                elif value is not None:
                    point.field(key, str(value))

        # Write point to InfluxDB
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        message_count += 1

        if message_count % 100 == 0:
            print(f"✓ {message_count} normal messages written")

except KeyboardInterrupt:
    print("Shutting down normal data consumer...")

finally:
    consumer.close()
    client.close()
    print(f"✓ Consumer stopped. Total messages written: {message_count}")
