"""
Sensor Data Producer - Streams SWaT Excel dataset to Kafka
"""

import json
import time
from datetime import datetime
from kafka import KafkaProducer
import os
import sys

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = 'sensor-inputs'

# Dataset configuration - UPDATE THIS PATH
DATASET_PATH = '/app/data/swat/Normal Data 2023/22June2020 (1).xlsx'
STREAMING_DELAY = 1.0  # seconds between messages


def create_kafka_producer():
    """Create and return a Kafka producer instance."""
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3
            )
            print(f"✅ Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except Exception as e:
            print(f"❌ Attempt {attempt + 1}/{max_retries}: Failed to connect to Kafka: {e}")
            if attempt < max_retries - 1:
                print(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("❌ Max retries reached. Exiting.")
                sys.exit(1)


def read_and_stream_excel_dataset(producer):
    """Read SWaT Excel dataset and stream to Kafka."""
    
    print(f"📂 Reading Excel dataset from: {DATASET_PATH}")
    
    if not os.path.exists(DATASET_PATH):
        print(f"❌ Dataset file not found: {DATASET_PATH}")
        print("ℹ️  Available files:")
        if os.path.exists('/app/data/swat'):
            os.system('ls -lah /app/data/swat')
        print("ℹ️  Generating synthetic data instead...")
        stream_test_data(producer)
        return
    
    try:
        import pandas as pd
        
        # Read Excel file
        print("📊 Loading Excel file...")
        df = pd.read_excel(DATASET_PATH)
        
        print(f"✅ Loaded dataset with {len(df)} rows and {len(df.columns)} columns")
        print(f"📊 Columns: {list(df.columns)}")
        print(f"🚀 Starting to stream data to topic: {KAFKA_TOPIC}")
        print("-" * 80)
        
        message_count = 0
        
        for index, row in df.iterrows():
            try:
                # Get timestamp (if available in dataset)
                timestamp = str(row.get('Timestamp', datetime.utcnow().isoformat()))
                
                # Build sensor data message
                message = {
                    'timestamp': timestamp,
                    'sensors': {}
                }
                
                # Add all sensor readings (skip timestamp and label columns)
                for col in df.columns:
                    if col not in ['Timestamp', 'Date', 'Time', 'Normal/Attack', 'Label']:
                        try:
                            value = row[col]
                            # Convert to float if possible
                            if pd.notna(value):  # Check if not NaN
                                message['sensors'][col] = float(value)
                        except (ValueError, TypeError):
                            # If can't convert, use as string
                            message['sensors'][col] = str(value) if pd.notna(value) else None
                
                # Add label if exists
                if 'Normal/Attack' in row:
                    message['label'] = str(row['Normal/Attack'])
                elif 'Label' in row:
                    message['label'] = str(row['Label'])
                else:
                    message['label'] = 'Normal'
                
                # Send to Kafka
                producer.send(KAFKA_TOPIC, value=message)
                
                message_count += 1
                
                # Print progress every 100 messages
                if message_count % 100 == 0:
                    print(f"📤 Sent {message_count} messages...")
                
                # Simulate real-time streaming
                time.sleep(STREAMING_DELAY)
                
            except Exception as e:
                print(f"⚠️  Error processing row {index + 1}: {e}")
                continue
        
        print("-" * 80)
        print(f"✅ Finished streaming {message_count} messages")
        
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        print("ℹ️  Make sure pandas and openpyxl are installed")
        print("ℹ️  Generating synthetic data instead...")
        stream_test_data(producer)


def stream_test_data(producer):
    """Stream test data if dataset is not available."""
    print("🧪 Streaming synthetic test data...")
    
    test_sensors = [
        'FIT-101', 'LIT-101', 'MV-101', 'P-101', 'P-102',
        'AIT-201', 'AIT-202', 'AIT-203', 'FIT-201'
    ]
    
    message_count = 0
    
    try:
        while True:
            timestamp = datetime.utcnow().isoformat()
            
            message = {
                'timestamp': timestamp,
                'sensors': {},
                'label': 'Normal'
            }
            
            # Generate random sensor values
            import random
            for sensor in test_sensors:
                message['sensors'][sensor] = round(random.uniform(0, 100), 2)
            
            producer.send(KAFKA_TOPIC, value=message)
            message_count += 1
            
            if message_count % 100 == 0:
                print(f"📤 Sent {message_count} test messages...")
            
            time.sleep(STREAMING_DELAY)
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Stopped after {message_count} messages")


def main():
    """Main function to run the sensor data producer."""
    print("=" * 80)
    print("🌊 NT-SCADA Sensor Data Producer (Excel Support)")
    print("=" * 80)
    
    # Create Kafka producer
    producer = create_kafka_producer()
    
    try:
        # Try to stream actual dataset
        read_and_stream_excel_dataset(producer)
            
    except KeyboardInterrupt:
        print("\n⏹️  Producer stopped by user")
    finally:
        producer.flush()
        producer.close()
        print("👋 Producer shut down gracefully")


if __name__ == "__main__":
    main()