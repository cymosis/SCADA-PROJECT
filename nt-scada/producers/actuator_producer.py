"""
NT-SCADA Actuator Data Producer
Reads Excel file in chunks and sends each row to Kafka as JSON.
Handles large files efficiently without loading everything into memory.
"""

import pandas as pd
import json
import os
import time
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# -----------------------------
# Configuration
# -----------------------------
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
TOPIC = 'scada.actuators_v2'
EXCEL_FILE = 'C:/scada-docker/Swat Data/Normal  Data 2023/22June2020 (1).xlsx'
STREAM_DELAY = 0.1  # seconds between messages
CHUNK_SIZE = 1000  # rows per chunk

def create_kafka_producer():
    """Create Kafka producer with retry logic"""
    max_retries = 10
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                max_request_size=10485760,  # 10MB max message size
                acks='all',
                retries=3,
                compression_type='gzip'
            )
            print(f"✓ Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except NoBrokersAvailable:
            print(f"⚠ Kafka not available (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay}s...")
            time.sleep(retry_delay)

    raise Exception("Failed to connect to Kafka after maximum retries")

def process_excel_in_chunks():
    """Read and process Excel file in chunks"""
    print("=" * 60)
    print("NT-SCADA Actuator Data Producer")
    print("=" * 60)
    print(f"Kafka Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Topic: {TOPIC}")
    print(f"Excel File: {EXCEL_FILE}")
    print(f"Chunk Size: {CHUNK_SIZE} rows")
    print("=" * 60)

    if not os.path.exists(EXCEL_FILE):
        print(f"❌ Error: Excel file not found at {EXCEL_FILE}")
        return

    # Create Kafka producer
    producer = create_kafka_producer()

    message_count = 0
    chunk_num = 0

    try:
        # Read Excel file in chunks
        for chunk in pd.read_excel(EXCEL_FILE, chunksize=CHUNK_SIZE):
            chunk_num += 1
            print(f"\n📦 Processing chunk {chunk_num} ({len(chunk)} rows)...")

            for i, row in chunk.iterrows():
                data = row.to_dict()

                # Convert NaN to None
                data = {k: (None if pd.isna(v) else v) for k, v in data.items()}

                # Convert timestamp to ISO string
                if 't_stamp' in data and data['t_stamp'] is not None:
                    data['t_stamp'] = pd.to_datetime(data['t_stamp']).isoformat()

                # Send to Kafka
                producer.send(TOPIC, value=data)
                message_count += 1

                # Log progress
                if message_count % 100 == 0:
                    print(f"✓ Sent {message_count} messages")

                # Simulate streaming delay
                time.sleep(STREAM_DELAY)

            # Flush after each chunk
            producer.flush()
            print(f"✓ Chunk {chunk_num} completed ({message_count} total messages sent)")

        print(f"\n✅ All {message_count} messages sent to Kafka topic '{TOPIC}'.")

    except KeyboardInterrupt:
        print("\n⚠ Shutting down producer...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        producer.close()
        print(f"✓ Producer stopped. Total messages sent: {message_count}")


if __name__ == "__main__":
    process_excel_in_chunks()
