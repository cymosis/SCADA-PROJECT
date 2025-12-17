import json
import os
import time
from kafka import KafkaConsumer
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# -----------------------------
# Configuration
# -----------------------------
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
KAFKA_TOPIC = 'scada.attacks'
KAFKA_GROUP_ID = 'attack-row-consumer'

INFLUXDB_URL = os.getenv('INFLUX_URL', 'http://influxdb:8086')
INFLUXDB_TOKEN = os.getenv('INFLUX_TOKEN', 'mytoken')
INFLUXDB_ORG = os.getenv('INFLUX_ORG', 'scada')
INFLUXDB_BUCKET = os.getenv('INFLUX_BUCKET', 'attack_data')

# Define which keys are tags
TAG_KEYS = ["P1_STATE", "P2_STATE", "P3_STATE", "P4_STATE", "P5_STATE", "P6_STATE"]


def main():
    print(f"Starting Attack Data Consumer...")
    print(f"Kafka: {KAFKA_BOOTSTRAP_SERVERS} | Topic: {KAFKA_TOPIC}")
    print(f"InfluxDB: {INFLUXDB_URL} | Bucket: {INFLUXDB_BUCKET}")
    
    # Wait for services to be ready
    time.sleep(5)
    
    # Connect to Kafka
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='earliest',
        group_id=KAFKA_GROUP_ID,
        value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )
    print(f"✓ Connected to Kafka topic '{KAFKA_TOPIC}'")
    
    # Connect to InfluxDB
    client = InfluxDBClient(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG
    )
    write_api = client.write_api(write_options=SYNCHRONOUS)
    print(f"✓ Connected to InfluxDB bucket '{INFLUXDB_BUCKET}'")
    
    message_count = 0
    
    try:
        for msg in consumer:
            data = msg.value
            
            # Create InfluxDB Point
            point = Point("actuator_data")
            
            # Add tags dynamically
            for tag_key in TAG_KEYS:
                if tag_key in data:
                    point.tag(tag_key, str(data[tag_key]))
            
            # Add all other fields
            for key, value in data.items():
                if key == "t_stamp":
                    point.time(value, WritePrecision.NS)
                elif key not in TAG_KEYS:
                    if isinstance(value, (int, float)):
                        point.field(key, float(value))
                    else:
                        point.field(key, str(value))
            
            # Write to InfluxDB
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
            message_count += 1
            
            # Log progress every 100 messages
            if message_count % 100 == 0:
                print(f"⚡ {message_count} attack messages written")
    
    except KeyboardInterrupt:
        print("Shutting down consumer...")
    
    finally:
        consumer.close()
        client.close()
        print(f"✓ Consumer stopped. Total messages: {message_count}")


if __name__ == "__main__":
    main()