import pandas as pd
import json
import time
import os
from kafka import KafkaProducer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")

TOPIC = "scada.attacks"
EXCEL_FILE = "/app/data/attacks.xlsx"

CHUNK_SIZE = 200
DELAY = 0.1  # seconds between messages (MODERATE SPEED - 10 msgs/sec)

def create_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        compression_type="gzip",
    )

def send_excel_to_kafka():
    if not os.path.exists(EXCEL_FILE):
        print("Excel file not found.")
        return

    print("Loading Excel file... (this happens once)")
    df = pd.read_excel(EXCEL_FILE)

    producer = create_producer()
    total_sent = 0

    print("Starting continuous stream...\n")

    while True:  # Loop forever for simulation
        df_shuffled = df.sample(frac=1).reset_index(drop=True)  # randomize rows
        for start in range(0, len(df_shuffled), CHUNK_SIZE):
            chunk = df_shuffled.iloc[start:start + CHUNK_SIZE].where(pd.notnull(df_shuffled), None)
            records = chunk.to_dict(orient="records")

            for record in records:
                if "t_stamp" in record and record["t_stamp"]:
                    record["t_stamp"] = str(pd.to_datetime(record["t_stamp"]))

                producer.send(TOPIC, record)
                total_sent += 1
                time.sleep(DELAY)

            producer.flush()
            print(f"Sent chunk up to row {start + len(chunk)} (total {total_sent})")

if __name__ == "__main__":
    send_excel_to_kafka()
