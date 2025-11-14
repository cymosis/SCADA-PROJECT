"""
Sensor Data Producer - Streams SWaT Excel dataset to Kafka
"""

import json
import time
from datetime import datetime
from kafka import KafkaProducer
import os
import sys
import pandas as pd

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9093')
KAFKA_TOPIC = 'sensor-inputs'

# Dataset configuration
DATASET_PATH = r'..\data\swat\Attack Data 2019\SWaT_dataset_Jul 19 v2.xlsx'
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
        print(f"💡 Full path: {os.path.abspath(DATASET_PATH)}")
        return
    
    try:
        # Read Excel file
        print("📊 Loading Excel file...")
        df = pd.read_excel(DATASET_PATH)
        
        print(f"✅ Loaded dataset with {len(df)} rows and {len(df.columns)} columns")
        print(f"📊 Columns: {list(df.columns)[:10]}...")
        print(f"🚀 Starting to stream data to topic: {KAFKA_TOPIC}")
        print("-" * 80)
        
        message_count = 0
        
        for index, row in df.iterrows():
            try:
                # Get timestamp
                timestamp = str(row.get('t_stamp', datetime.utcnow().isoformat()))
                
                # Build sensor data message
                message = {
                    'timestamp': timestamp,
                    'sensors': {},
                    'label': 'Normal'
                }
                
                # Add ALL features except t_stamp
                for col in df.columns:
                    if col == 't_stamp':
                        continue
                    
                    # Convert to numeric
                    try:
                        value = pd.to_numeric(row[col], errors='coerce')
                        if pd.notna(value):
                            message['sensors'][col] = float(value)
                        else:
                            message['sensors'][col] = 0.0
                    except:
                        message['sensors'][col] = 0.0
                
                # Debug: Print feature count for first message
                if message_count == 0:
                    print(f"🔍 First message contains {len(message['sensors'])} features")
                
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


def main():
    """Main function to run the sensor data producer."""
    print("=" * 80)
    print("🌊 NT-SCADA Sensor Data Producer")
    print("=" * 80)
    
    # Create Kafka producer
    producer = create_kafka_producer()
    
    try:
        # Stream dataset
        read_and_stream_excel_dataset(producer)
            
    except KeyboardInterrupt:
        print("\n⏹️  Producer stopped by user")
    finally:
        producer.flush()
        producer.close()
        print("👋 Producer shut down gracefully")


if __name__ == "__main__":
    main()