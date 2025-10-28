"""
Kafka Consumer for Excel Row Data
Reads messages from Kafka and prints them to console.
"""

import json
from kafka import KafkaConsumer

# -----------------------------
# Configuration
# -----------------------------
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'  # Kafka broker
KAFKA_TOPIC = 'scada.actuators_v2'          # Kafka topic
KAFKA_GROUP_ID = 'excel-row-consumer'       # Consumer group

# -----------------------------
# Create Kafka Consumer
# -----------------------------
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    auto_offset_reset='earliest',  # start from beginning
    group_id=KAFKA_GROUP_ID,
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
)

print(f"✓ Connected to Kafka topic '{KAFKA_TOPIC}' at {KAFKA_BOOTSTRAP_SERVERS}")

# -----------------------------
# Consume Messages
# -----------------------------
try:
    for i, msg in enumerate(consumer):
        data = msg.value
        print(f"\nMessage {i+1}:")
        print(json.dumps(data, indent=2))


except KeyboardInterrupt:
    print("\n⚠ Consumer stopped by user")

finally:
    consumer.close()
    print("✓ Kafka consumer closed")
