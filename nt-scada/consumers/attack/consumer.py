import json
import os
import time
from datetime import datetime
from kafka import KafkaConsumer
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
KAFKA_TOPIC = 'scada.attacks'
KAFKA_GROUP_ID = 'attack-row-consumer'
INFLUXDB_URL = os.getenv('INFLUX_URL', 'http://influxdb:8086')
INFLUXDB_TOKEN = os.getenv('INFLUX_TOKEN', 'mytoken')
INFLUXDB_ORG = os.getenv('INFLUX_ORG', 'scada')
INFLUXDB_BUCKET = os.getenv('INFLUX_BUCKET', 'attack_data')
TAG_KEYS = ["P1_STATE", "P2_STATE", "P3_STATE", "P4_STATE", "P5_STATE", "P6_STATE"]

def parse_timestamp(ts_value):
    """Fix: Convert timestamp STRING to DATETIME object"""
    if isinstance(ts_value, datetime):
        return ts_value
    if isinstance(ts_value, str):
        try:
            iso_str = ts_value.replace(' ', 'T').split('+')[0].rstrip('Z')
            return datetime.fromisoformat(iso_str)
        except:
            return datetime.utcnow()
    return datetime.utcnow()

def main():
    print(f"Starting Attack Data Consumer...")
    time.sleep(5)
    
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='earliest',
        group_id=KAFKA_GROUP_ID,
        value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )
    print(f"✓ Connected to Kafka")
    
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    print(f"✓ Connected to InfluxDB")
    
    message_count = 0
    
    try:
        for msg in consumer:
            data = msg.value
            point = Point("sensor_data")
            
            for tag_key in TAG_KEYS:
                if tag_key in data:
                    point = point.tag(tag_key, str(data[tag_key]))
            
            # CRITICAL FIX HERE
            timestamp_value = data.get('t_stamp')
            if timestamp_value:
                dt = parse_timestamp(timestamp_value)
                point = point.time(dt, WritePrecision.NS)
            
            for key, value in data.items():
                if key == "t_stamp":
                    continue
                elif key not in TAG_KEYS:
                    if isinstance(value, (int, float)):
                        point = point.field(key, float(value))
                    else:
                        point = point.field(key, str(value))
            
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
            message_count += 1
            
            if message_count % 100 == 0:
                print(f"⚡ {message_count} attack messages written")
    
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        consumer.close()
        client.close()
        print(f"✓ Total: {message_count}")

if __name__ == "__main__":
    main()
