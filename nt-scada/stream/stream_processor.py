"""
NT-SCADA Stream Processor (Python-based alternative to Flink)
Performs real-time anomaly detection and classification
Uses Kafka Streams pattern with Python
"""

import os
import json
import time
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'nt-scada-token-secret-key-12345')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'nt-scada')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', 'scada_data')


def create_kafka_consumer():
    """Create Kafka consumer with retry logic"""
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            consumer = KafkaConsumer(
                'scada.sensors',
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='stream-processor',
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            print(f"✓ Consumer connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return consumer
        except NoBrokersAvailable:
            print(f"⚠ Kafka not available (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
    
    raise Exception("Failed to connect to Kafka after maximum retries")


def create_kafka_producer():
    """Create Kafka producer with retry logic"""
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all'
            )
            print(f"✓ Producer connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except NoBrokersAvailable:
            print(f"⚠ Kafka not available (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
    
    raise Exception("Failed to connect to Kafka after maximum retries")


def detect_anomaly(sensor_value):
    """
    Binary anomaly detection
    Rule: value < 20 or > 80 is anomalous
    """
    return sensor_value < 20 or sensor_value > 80


def classify_severity(sensor_value):
    """Classify severity of reading"""
    if sensor_value < 10 or sensor_value > 90:
        return 'CRITICAL'
    elif sensor_value < 20 or sensor_value > 80:
        return 'HIGH'
    elif sensor_value < 25 or sensor_value > 75:
        return 'MEDIUM'
    else:
        return 'LOW'


def classify_category(sensor_type):
    """Classify sensor into category"""
    if sensor_type in ['temperature', 'pressure']:
        return 'THERMAL_PRESSURE'
    elif sensor_type in ['flow_rate', 'vibration']:
        return 'MECHANICAL'
    elif sensor_type in ['voltage', 'current']:
        return 'ELECTRICAL'
    else:
        return 'OTHER'


def fine_grained_classification(sensor_value):
    """
    Fine-grained multi-class classification
    Classifies into 7 operational states
    """
    if sensor_value < 10:
        return 'CRITICALLY_LOW'
    elif sensor_value < 20:
        return 'LOW'
    elif sensor_value < 30:
        return 'BELOW_OPTIMAL'
    elif sensor_value < 70:
        return 'OPTIMAL'
    elif sensor_value < 80:
        return 'ABOVE_OPTIMAL'
    elif sensor_value < 90:
        return 'HIGH'
    else:
        return 'CRITICALLY_HIGH'


def process_sensor_data(data):
    """
    Process sensor data through both pipelines:
    1. Binary anomaly detection
    2. Fine-grained classification
    """
    sensor_value = data.get('value', 50)
    sensor_type = data.get('sensor_type', 'unknown')
    
    # Pipeline 1: Binary anomaly detection
    is_anomaly = detect_anomaly(sensor_value)
    severity = classify_severity(sensor_value)
    category = classify_category(sensor_type)
    
    # Pipeline 2: Fine-grained classification
    operational_state = fine_grained_classification(sensor_value)
    
    # Add processing results
    processed_data = data.copy()
    processed_data.update({
        'anomaly_detected': is_anomaly,
        'severity': severity,
        'category': category,
        'operational_state': operational_state,
        'processed_timestamp': datetime.utcnow().isoformat() + 'Z'
    })
    
    return processed_data


def main():
    """Main stream processing loop"""
    print("=" * 60)
    print("NT-SCADA Stream Processor")
    print("=" * 60)
    print(f"Kafka Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Input Topic: scada.sensors")
    print(f"Output Topics: scada.processed, scada.anomalies")
    print("=" * 60)
    
    # Create Kafka consumer and producer
    consumer = create_kafka_consumer()
    producer = create_kafka_producer()
    
    processed_count = 0
    anomaly_count = 0
    
    try:
        print("✓ Stream processor started. Processing messages...")
        
        for message in consumer:
            try:
                # Get sensor data
                sensor_data = message.value
                
                # Process through pipelines
                processed_data = process_sensor_data(sensor_data)
                
                # Send to processed topic
                producer.send('scada.processed', value=processed_data)
                processed_count += 1
                
                # If anomaly detected, send to anomalies topic
                if processed_data['anomaly_detected']:
                    producer.send('scada.anomalies', value=processed_data)
                    anomaly_count += 1
                
                # Log progress
                if processed_count % 100 == 0:
                    print(f"✓ Processed: {processed_count} | Anomalies: {anomaly_count} | "
                          f"Latest: {processed_data['sensor_id']} = {processed_data['value']} "
                          f"[{processed_data['operational_state']}]")
                
            except Exception as e:
                print(f"⚠ Error processing message: {e}")
                continue
    
    except KeyboardInterrupt:
        print("\n⚠ Shutting down stream processor...")
    finally:
        consumer.close()
        producer.close()
        print(f"✓ Stream processor stopped. Processed: {processed_count}, Anomalies: {anomaly_count}")


if __name__ == "__main__":
    main()
