import json
import os
from kafka import KafkaConsumer
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# -----------------------------
# Configuration
# -----------------------------
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = 'scada.actuators_v2'
KAFKA_GROUP_ID = 'excel-row-consumer'

INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'nt-scada-token-secret-key-12345')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'nt-scada')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', 'scada_data_v2')

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
# Kafka Consume & Write Loop
# -----------------------------
message_count = 0

try:
    for msg in consumer:
        data = msg.value  # JSON message

        # Create InfluxDB Point
        point = Point("normal_data")

        for key, value in data.items():
            if key == "t_stamp":
                # Use t_stamp as the point's timestamp
                point.time(value, WritePrecision.NS)
            else:
                # All other keys as tags (converted to string)
                point.tag(key, str(value))

        # Write to InfluxDB
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        message_count += 1

        if message_count % 100 == 0:
            print(f"✓ {message_count} messages written")

except KeyboardInterrupt:
    print("Shutting down consumer...")

finally:
    consumer.close()
    client.close()
    print(f"✓ Consumer stopped. Total messages written: {message_count}")
