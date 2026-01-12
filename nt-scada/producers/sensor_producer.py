"""
NT-SCADA Sensor Data Producer
Simulates real-time sensor data from industrial SCADA systems
Sends data to Kafka topic: scada.sensors
"""

import json
import time
import random
import os
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
TOPIC_SENSORS = 'scada.sensors'

# Sensor types and their normal operating ranges
SENSOR_TYPES = {
    'temperature': {'min': 15, 'max': 85, 'unit': '°C', 'anomaly_prob': 0.05},
    'pressure': {'min': 10, 'max': 90, 'unit': 'PSI', 'anomaly_prob': 0.05},
    'flow_rate': {'min': 20, 'max': 75, 'unit': 'L/min', 'anomaly_prob': 0.05},
    'vibration': {'min': 25, 'max': 70, 'unit': 'mm/s', 'anomaly_prob': 0.05},
    'voltage': {'min': 30, 'max': 80, 'unit': 'V', 'anomaly_prob': 0.05},
    'current': {'min': 18, 'max': 82, 'unit': 'A', 'anomaly_prob': 0.05},
}

# Sensor IDs (simulating multiple sensors per type)
SENSOR_IDS = [f"{sensor_type}_{i:03d}" for sensor_type in SENSOR_TYPES.keys() for i in range(1, 6)]


def create_kafka_producer():
    """Create and return Kafka producer with retry logic"""
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                # Key serialization handled explicitly in send() for partitioning control
                acks='all',
                retries=3
            )
            print(f"✓ Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except NoBrokersAvailable:
            print(f"⚠ Kafka not available (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
    
    raise Exception("Failed to connect to Kafka after maximum retries")


def generate_sensor_value(sensor_id):
    """Generate realistic sensor data with occasional anomalies"""
    sensor_type = sensor_id.rsplit('_', 1)[0]
    config = SENSOR_TYPES[sensor_type]
    
    # Determine if this reading should be anomalous
    is_anomaly = random.random() < config['anomaly_prob']
    
    if is_anomaly:
        # Generate anomalous value (outside normal range)
        if random.random() < 0.5:
            # Low anomaly (< 20)
            value = random.uniform(0, 19)
        else:
            # High anomaly (> 80)
            value = random.uniform(81, 100)
    else:
        # Normal value within operating range
        value = random.uniform(config['min'], config['max'])
    
    # Add some realistic noise
    value += random.gauss(0, 1)
    value = max(0, min(100, value))  # Clamp to [0, 100]
    
    return round(value, 2)


def generate_sensor_data(sensor_id):
    """Generate complete sensor data message"""
    sensor_type = sensor_id.rsplit('_', 1)[0]
    value = generate_sensor_value(sensor_id)
    
    # Determine status based on value
    if value < 20 or value > 80:
        status = 'ALARM'
        anomaly = True
    elif value < 25 or value > 75:
        status = 'WARNING'
        anomaly = False
    else:
        status = 'NORMAL'
        anomaly = False
    
    data = {
        'sensor_id': sensor_id,
        'sensor_type': sensor_type,
        'value': value,
        'unit': SENSOR_TYPES[sensor_type]['unit'],
        'status': status,
        'anomaly': anomaly,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'location': f"Zone-{hash(sensor_id) % 5 + 1}",
        'metadata': {
            'firmware_version': '2.1.0',
            'calibration_date': '2024-01-15'
        }
    }
    
    return data


def main():
    """Main producer loop"""
    print("=" * 60)
    print("NT-SCADA Sensor Data Producer")
    print("=" * 60)
    print(f"Kafka Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Topic: {TOPIC_SENSORS}")
    print(f"Sensors: {len(SENSOR_IDS)}")
    print("=" * 60)
    
    # Create Kafka producer
    producer = create_kafka_producer()
    
    message_count = 0
    
    try:
        while True:
            # Generate data for each sensor
            for sensor_id in SENSOR_IDS:
                sensor_data = generate_sensor_data(sensor_id)
                
                # Send to Kafka
                # Explicitly use sensor_id as key to ensure all data for a sensor 
                # goes to the same partition (Strict Ordering)
                producer.send(
                    TOPIC_SENSORS,
                    key=sensor_id.encode('utf-8'),
                    value=sensor_data
                )
                
                message_count += 1
                
                # Log every 50 messages
                if message_count % 50 == 0:
                    print(f"✓ Sent {message_count} messages | Latest: {sensor_id} = {sensor_data['value']} {sensor_data['unit']} [{sensor_data['status']}]")
            
            # Flush to ensure delivery
            producer.flush()
            
            # Wait before next batch (simulate real-time streaming)
            time.sleep(2)  # 2 seconds between batches
            
    except KeyboardInterrupt:
        print("\n⚠ Shutting down producer...")
    finally:
        producer.close()
        print(f"✓ Producer stopped. Total messages sent: {message_count}")


if __name__ == "__main__":
    main()
