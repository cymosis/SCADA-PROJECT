import pandas as pd
import json
import os
import time
from kafka import KafkaProducer
from random import shuffle

# -----------------------------
# Configuration
# -----------------------------
KAFKA_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:29092')
TOPIC = 'scada.normal'
EXCEL_FILE = "/app/data/normal.xlsx"
CHUNK_SIZE = 1000
STREAM_DELAY = 0.1  # seconds between messages (MODERATE SPEED - 10 msgs/sec)

# -----------------------------
# Kafka Producer
# -----------------------------
def create_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        compression_type='gzip'
    )

# -----------------------------
# Send Excel rows to Kafka continuously
# -----------------------------
def send_excel_to_kafka():
    if not os.path.exists(EXCEL_FILE):
        print(f"Excel file not found: {EXCEL_FILE}")
        return

    df = pd.read_excel(EXCEL_FILE)
    producer = create_producer()
    print(f"Producer connected to Kafka: {KAFKA_SERVERS}")

    total_sent = 0
    while True:  # Loop forever to simulate continuous streaming
        df_shuffled = df.sample(frac=1).reset_index(drop=True)  # Randomize order
        for start in range(0, len(df_shuffled), CHUNK_SIZE):
            chunk = df_shuffled.iloc[start:start + CHUNK_SIZE].where(pd.notnull(df_shuffled), None)
            records = chunk.to_dict(orient='records')

            for record in records:
                # Convert timestamp
                if 't_stamp' in record and record['t_stamp']:
                    record['t_stamp'] = str(pd.to_datetime(record['t_stamp']))

                producer.send(TOPIC, record)
                total_sent += 1
                time.sleep(STREAM_DELAY)

            producer.flush()
            print(f"✓ Sent chunk up to row {start + len(chunk)} (total {total_sent})")

# -----------------------------
if __name__ == "__main__":
    send_excel_to_kafka()
