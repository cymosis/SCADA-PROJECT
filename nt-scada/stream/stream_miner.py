"""
NT-SCADA Stream Miner (Advanced Stream Analytics)
================================================
This is a "Sidecar" service that runs alongside the main processor.
It implements advanced Stream Mining techniques without affecting the main pipeline.

Techniques Implemented:
1. Concept Drift Detection (ADWIN) - Detects when sensor behavior changes over time.
2. Online Learning (Hoeffding Tree) - Learns to classify anomalies incrementally.
3. Sliding Window Statistics - Calculates rolling stats for complex event processing.

Dependencies:
- river: For online machine learning and drift detection
- kafka-python: For data ingestion
"""

import os
import json
import time
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable
import river.drift
import river.tree
import river.stats

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
INPUT_TOPIC = 'scada.sensors'
OUTPUT_TOPIC = 'scada.mining.results'

def create_kafka_consumer():
    """Create Kafka consumer with retry logic"""
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            consumer = KafkaConsumer(
                INPUT_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='stream-miner-group', # Different group ID to read same data independently
                auto_offset_reset='latest'
            )
            print(f"✓ Stream Miner connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return consumer
        except NoBrokersAvailable:
            print(f"⚠ Kafka not available (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
    
    raise Exception("Failed to connect to Kafka after maximum retries")

def create_kafka_producer():
    """Create Kafka producer for mining results"""
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        return producer
    except Exception as e:
        print(f"⚠ Failed to create producer: {e}")
        return None

class StreamMiner:
    def __init__(self):
        # 1. Concept Drift Detectors (one per sensor type or critical sensor)
        # ADWIN (ADaptive WINdowing) automatically adjusts its window size 
        # to detect changes in the data distribution.
        self.drift_detectors = {} 
        
        # 2. Online Learning Model
        # Hoeffding Tree is a decision tree that learns incrementally.
        # We will try to predict if a state is 'CRITICAL' based on value.
        self.model = river.tree.HoeffdingTreeClassifier()
        
        # 3. Rolling Statistics
        # Keep track of running variance/mean
        self.rolling_stats = {}

    def get_drift_detector(self, sensor_id):
        if sensor_id not in self.drift_detectors:
            self.drift_detectors[sensor_id] = river.drift.ADWIN(delta=0.002)
        return self.drift_detectors[sensor_id]

    def get_rolling_stat(self, sensor_id):
        if sensor_id not in self.rolling_stats:
            self.rolling_stats[sensor_id] = river.stats.Var()
        return self.rolling_stats[sensor_id]

    def process_record(self, record):
        """
        Apply stream mining techniques to a single record.
        """
        sensor_id = record.get('sensor_id', 'unknown')
        value = record.get('value', 0.0)
        timestamp = record.get('timestamp', datetime.utcnow().isoformat())
        
        mining_results = {
            'sensor_id': sensor_id,
            'timestamp': timestamp,
            'original_value': value,
            'drift_detected': False,
            'drift_info': None,
            'rolling_variance': 0.0,
            'model_prediction': None
        }

        # --- Technique 1: Concept Drift Detection ---
        # We feed the value into ADWIN. If it detects a significant change in mean,
        # it flags a drift.
        adwin = self.get_drift_detector(sensor_id)
        adwin.update(value)
        
        if adwin.drift_detected:
            mining_results['drift_detected'] = True
            mining_results['drift_info'] = f"Distribution changed. New mean approx: {adwin.estimation:.2f}"
            print(f"⚠ DRIFT DETECTED for {sensor_id}: {mining_results['drift_info']}")

        # --- Technique 2: Rolling Statistics ---
        # Update running variance
        var_stat = self.get_rolling_stat(sensor_id)
        var_stat.update(value)
        mining_results['rolling_variance'] = var_stat.get()

        # --- Technique 3: Online Learning (Supervised) ---
        # In a real scenario, we need ground truth labels to train.
        # Here, we will simulate "self-supervised" learning:
        # We assume values > 90 are 'CRITICAL' (simulating an external label arriving later)
        # and train the model to recognize this pattern incrementally.
        
        # Create a feature vector
        features = {'value': value, 'sensor_id': sensor_id}
        
        # Predict first (Test-then-Train)
        prediction = self.model.predict_one(features)
        mining_results['model_prediction'] = prediction
        
        # Generate a synthetic label for training (Simulating ground truth)
        # In production, this label would come from a human operator or delayed system log
        actual_label = 'CRITICAL' if value > 90 or value < 10 else 'NORMAL'
        
        # Train the model incrementally
        self.model.learn_one(features, actual_label)

        return mining_results

def main():
    print("=" * 60)
    print("NT-SCADA Stream Miner (Advanced Analytics Sidecar)")
    print("=" * 60)
    print(f"Listening to: {INPUT_TOPIC}")
    print(f"Writing to:   {OUTPUT_TOPIC}")
    print("Techniques:   ADWIN Drift Detection, Hoeffding Tree, Rolling Stats")
    print("=" * 60)

    consumer = create_kafka_consumer()
    producer = create_kafka_producer()
    miner = StreamMiner()

    print("✓ Stream Miner active. Waiting for data...")

    try:
        for message in consumer:
            try:
                record = message.value
                
                # Apply mining techniques
                results = miner.process_record(record)
                
                # Only publish if interesting things happen (e.g., drift or anomaly)
                # or periodically for dashboarding. For now, we publish everything 
                # that has drift or high variance, or just sample it.
                
                if results['drift_detected'] or results['model_prediction'] == 'CRITICAL':
                    if producer:
                        producer.send(OUTPUT_TOPIC, value=results)
                        # print(f"-> Published mining insight for {results['sensor_id']}")

            except Exception as e:
                print(f"Error processing record: {e}")
                continue

    except KeyboardInterrupt:
        print("\n⚠ Stopping Stream Miner...")
    finally:
        consumer.close()
        if producer:
            producer.close()

if __name__ == "__main__":
    main()
