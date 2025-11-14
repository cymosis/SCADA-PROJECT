"""
Stream Processor - Real-time Anomaly Detection

This script consumes sensor data from Kafka, applies ML models for:
1. Binary classification (Normal vs Anomaly)
2. Fine-grained classification (types of anomalies)

Then publishes results to output topics.
"""

import json
import os
import sys
import time
import numpy as np
from kafka import KafkaConsumer, KafkaProducer
from datetime import datetime

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
INPUT_TOPIC = 'sensor-inputs'
OUTPUT_TOPIC = 'processed-data'
ANOMALY_TOPIC = 'anomalies'

# Model paths (will be created during batch processing phase)
BINARY_MODEL_PATH = '/app/binary_classifier.pkl'
MULTICLASS_MODEL_PATH = '/app/multiclass_classifier.pkl'


def create_kafka_consumer():
    """Create and return a Kafka consumer."""
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            consumer = KafkaConsumer(
                INPUT_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id='stream-processor-group'
            )
            print(f"✅ Connected to Kafka consumer at {KAFKA_BOOTSTRAP_SERVERS}")
            return consumer
        except Exception as e:
            print(f"❌ Attempt {attempt + 1}/{max_retries}: Failed to connect: {e}")
            if attempt < max_retries - 1:
                print(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("❌ Max retries reached. Exiting.")
                sys.exit(1)


def create_kafka_producer():
    """Create and return a Kafka producer."""
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all'
        )
        print(f"✅ Connected to Kafka producer at {KAFKA_BOOTSTRAP_SERVERS}")
        return producer
    except Exception as e:
        print(f"❌ Failed to create producer: {e}")
        sys.exit(1)


def load_models():
    """Load pre-trained ML models."""
    models = {
        'binary': None,
        'multiclass': None
    }
    
    try:
        # Try to load binary classifier
        if os.path.exists(BINARY_MODEL_PATH):
            import joblib
            models['binary'] = joblib.load(BINARY_MODEL_PATH)
            print(f"✅ Loaded binary classifier from {BINARY_MODEL_PATH}")
        else:
            print(f"⚠️  Binary classifier not found at {BINARY_MODEL_PATH}")
            print("ℹ️  Will use rule-based anomaly detection")
    
        # Try to load multiclass classifier
        if os.path.exists(MULTICLASS_MODEL_PATH):
            import joblib
            models['multiclass'] = joblib.load(MULTICLASS_MODEL_PATH)
            print(f"✅ Loaded multiclass classifier from {MULTICLASS_MODEL_PATH}")
        else:
            print(f"⚠️  Multiclass classifier not found at {MULTICLASS_MODEL_PATH}")
            
    except Exception as e:
        print(f"⚠️  Error loading models: {e}")
    
    return models


def extract_features(sensor_data):
    """Extract features from sensor data for ML models."""
    try:
        # Convert sensor readings to feature vector
        features = []
        sensor_names = sorted(sensor_data.keys())
        
        for sensor_name in sensor_names:
            value = sensor_data[sensor_name]
            features.append(float(value) if isinstance(value, (int, float)) else 0.0)
        
        return np.array(features).reshape(1, -1), sensor_names
    except Exception as e:
        print(f"⚠️  Error extracting features: {e}")
        return None, None


def rule_based_anomaly_detection(sensor_data):
    """
    Simple rule-based anomaly detection when ML models are not available.
    This is a placeholder - you should customize these rules based on
    your understanding of the SWaT dataset.
    """
    anomalies = []
    
    # Example rules (customize based on your domain knowledge)
    for sensor_name, value in sensor_data.items():
        try:
            value = float(value)
            
            # Example: Detect if values are outside normal ranges
            if sensor_name.startswith('FIT'):  # Flow sensors
                if value < 0 or value > 5:
                    anomalies.append(f"{sensor_name}: {value} out of range")
            
            elif sensor_name.startswith('LIT'):  # Level sensors
                if value < 0 or value > 1000:
                    anomalies.append(f"{sensor_name}: {value} out of range")
            
            elif sensor_name.startswith('P-'):  # Pumps (binary)
                if value not in [0, 1, 2]:
                    anomalies.append(f"{sensor_name}: {value} invalid state")
            
        except (ValueError, TypeError):
            continue
    
    is_anomaly = len(anomalies) > 0
    confidence = min(len(anomalies) / 10.0, 1.0)  # Simple confidence score
    
    return is_anomaly, confidence, anomalies


def process_message(message, models, producer):
    """Process a single sensor data message."""
    try:
        timestamp = message.get('timestamp', datetime.utcnow().isoformat())
        sensor_data = message.get('sensors', {})
        original_label = message.get('label', 'Unknown')
        
        # Extract features for ML models
        features, sensor_names = extract_features(sensor_data)
        
        # Binary classification (Normal vs Anomaly)
        is_anomaly = False
        confidence = 0.0
        anomaly_details = []
        
        if models['binary'] is not None and features is not None:
            # Use ML model
            try:
                prediction = models['binary'].predict(features)[0]
                confidence = models['binary'].predict_proba(features)[0][prediction]
                is_anomaly = (prediction == 1)  # Assuming 1 = anomaly
                prediction_type = 'ml'
            except Exception as e:
                print(f"⚠️  ML prediction failed: {e}, falling back to rules")
                is_anomaly, confidence, anomaly_details = rule_based_anomaly_detection(sensor_data)
                prediction_type = 'rule_based'
        else:
            # Use rule-based detection
            is_anomaly, confidence, anomaly_details = rule_based_anomaly_detection(sensor_data)
            prediction_type = 'rule_based'
        
        # Fine-grained classification (if anomaly detected and model available)
        anomaly_class = 'Normal'
        if is_anomaly and models['multiclass'] is not None and features is not None:
            try:
                anomaly_class = models['multiclass'].predict(features)[0]
            except Exception as e:
                anomaly_class = 'Unknown'
        
        # Prepare output message
        processed_message = {
            'timestamp': timestamp,
            'original_label': original_label,
            'is_anomaly': is_anomaly,
            'confidence': float(confidence),
            'anomaly_class': anomaly_class,
            'prediction_type': prediction_type,
            'sensor_count': len(sensor_data),
            'sensors': sensor_data
        }
        
        # Send to processed data topic
        producer.send(OUTPUT_TOPIC, value=processed_message)
        
        # If anomaly detected, also send to anomaly topic
        if is_anomaly:
            anomaly_message = {
                'timestamp': timestamp,
                'confidence': float(confidence),
                'anomaly_class': anomaly_class,
                'details': anomaly_details if anomaly_details else [],
                'sensors': sensor_data
            }
            producer.send(ANOMALY_TOPIC, value=anomaly_message)
            print(f"🚨 ANOMALY DETECTED: {anomaly_class} (confidence: {confidence:.2f})")
        
        return processed_message
        
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        return None


def main():
    """Main function to run the stream processor."""
    print("=" * 80)
    print("🔄 NT-SCADA Stream Processor - Real-time Anomaly Detection")
    print("=" * 80)
    
    # Load ML models
    models = load_models()
    
    # Create Kafka consumer and producer
    consumer = create_kafka_consumer()
    producer = create_kafka_producer()
    
    print(f"👂 Listening to topic: {INPUT_TOPIC}")
    print(f"📤 Publishing to topics: {OUTPUT_TOPIC}, {ANOMALY_TOPIC}")
    print("-" * 80)
    
    message_count = 0
    anomaly_count = 0
    
    try:
        for message in consumer:
            message_count += 1
            
            # Process the message
            result = process_message(message.value, models, producer)
            
            if result and result.get('is_anomaly'):
                anomaly_count += 1
            
            # Print statistics every 100 messages
            if message_count % 100 == 0:
                anomaly_rate = (anomaly_count / message_count) * 100
                print(f"📊 Processed: {message_count} messages | "
                      f"Anomalies: {anomaly_count} ({anomaly_rate:.1f}%)")
    
    except KeyboardInterrupt:
        print(f"\n⏹️  Stream processor stopped by user")
        print(f"📊 Final stats: {message_count} messages, {anomaly_count} anomalies detected")
    
    finally:
        producer.flush()
        producer.close()
        consumer.close()
        print("👋 Stream processor shut down gracefully")


if __name__ == "__main__":
    main()
