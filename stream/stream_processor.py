"""
Stream Processor - Real-time Anomaly Detection with ML
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

# Model paths
BINARY_MODEL_PATH = '/app/binary_classifier.pkl'
SCALER_PATH = '/app/scaler.pkl'
FEATURE_NAMES_PATH = '/app/feature_names.json'

# Global feature names
FEATURE_NAMES = None


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
    """Load pre-trained ML models and scaler."""
    global FEATURE_NAMES
    
    models = {
        'binary': None,
        'scaler': None
    }
    
    try:
        import joblib
        
        # Load binary classifier
        if os.path.exists(BINARY_MODEL_PATH):
            models['binary'] = joblib.load(BINARY_MODEL_PATH)
            print(f"✅ Loaded binary classifier from {BINARY_MODEL_PATH}")
            print(f"   Model expects {models['binary'].n_features_in_} features")
        else:
            print(f"⚠️  Binary classifier not found at {BINARY_MODEL_PATH}")
            print("ℹ️  Will use rule-based anomaly detection")
        
        # Load scaler
        if os.path.exists(SCALER_PATH):
            models['scaler'] = joblib.load(SCALER_PATH)
            print(f"✅ Loaded scaler from {SCALER_PATH}")
        else:
            print(f"⚠️  Scaler not found at {SCALER_PATH}")
        
        # Load feature names
        if os.path.exists(FEATURE_NAMES_PATH):
            with open(FEATURE_NAMES_PATH, 'r') as f:
                FEATURE_NAMES = json.load(f)
            print(f"✅ Loaded {len(FEATURE_NAMES)} feature names")
        else:
            print(f"⚠️  Feature names not found at {FEATURE_NAMES_PATH}")
            print("ℹ️  Will use sorted sensor keys")
            
    except Exception as e:
        print(f"⚠️  Error loading models: {e}")
    
    return models


def extract_features(sensor_data):
    """Extract features from sensor data in correct order."""
    try:
        # Use saved feature names or fallback to sorted keys
        if FEATURE_NAMES:
            feature_keys = FEATURE_NAMES
        else:
            # Use sorted keys (excluding timestamp and label)
            feature_keys = sorted([k for k in sensor_data.keys() 
                                 if k not in ['timestamp', 'label']])
        
        # Extract features in correct order
        features = []
        for key in feature_keys:
            value = sensor_data.get(key, 0)
            try:
                features.append(float(value))
            except:
                features.append(0.0)
        
        return np.array(features).reshape(1, -1)
        
    except Exception as e:
        print(f"⚠️  Error extracting features: {e}")
        return None


def rule_based_anomaly_detection(sensor_data):
    """Simple rule-based anomaly detection fallback."""
    anomalies = []
    
    for sensor_name, value in sensor_data.items():
        try:
            value = float(value)
            
            # Example rules
            if sensor_name.startswith('FIT'):  # Flow sensors
                if value < 0 or value > 5:
                    anomalies.append(f"{sensor_name}: {value} out of range")
            
            elif sensor_name.startswith('LIT'):  # Level sensors
                if value < 0 or value > 1000:
                    anomalies.append(f"{sensor_name}: {value} out of range")
            
        except (ValueError, TypeError):
            continue
    
    is_anomaly = len(anomalies) > 0
    confidence = min(len(anomalies) / 10.0, 1.0)
    
    return is_anomaly, confidence


def process_message(message, models, producer):
    """Process a single sensor data message."""
    try:
        timestamp = message.get('timestamp', datetime.utcnow().isoformat())
        sensor_data = message.get('sensors', {})
        original_label = message.get('label', 'Unknown')
        
        # Initialize
        is_anomaly = False
        confidence = 0.0
        prediction_type = 'rule_based'
        
        # Try ML prediction if model available
        if models['binary'] is not None and models['scaler'] is not None:
            try:
                # Extract features
                features = extract_features(sensor_data)
                
                if features is not None:
                    # Scale features
                    features_scaled = models['scaler'].transform(features)
                    
                    # Predict
                    prediction = models['binary'].predict(features_scaled)[0]
                    confidence_scores = models['binary'].predict_proba(features_scaled)[0]
                    
                    is_anomaly = (prediction == 1)
                    confidence = confidence_scores[1] if is_anomaly else confidence_scores[0]
                    prediction_type = 'ml'
                    
            except Exception as e:
                print(f"⚠️  ML prediction failed: {e}, falling back to rules")
                is_anomaly, confidence = rule_based_anomaly_detection(sensor_data)
                prediction_type = 'rule_based'
        else:
            # Use rule-based detection
            is_anomaly, confidence = rule_based_anomaly_detection(sensor_data)
        
        # Prepare output message
        processed_message = {
            'timestamp': timestamp,
            'original_label': original_label,
            'is_anomaly': bool(is_anomaly),
            'confidence': float(confidence),
            'prediction_type': prediction_type,
            'sensor_count': len(sensor_data)
        }
        
        # Send to processed data topic
        producer.send(OUTPUT_TOPIC, value=processed_message)
        
        # If anomaly detected, also send to anomaly topic
        if is_anomaly:
            anomaly_message = {
                'timestamp': timestamp,
                'confidence': float(confidence),
                'anomaly_class': str(original_label)
            }
            producer.send(ANOMALY_TOPIC, value=anomaly_message)
            
            # Print with appropriate emoji
            if prediction_type == 'ml':
                emoji = "🚨" if confidence > 0.7 else "⚠️"
            else:
                emoji = "⚠️"
            print(f"{emoji} ANOMALY DETECTED: {original_label} (confidence: {confidence:.2f}, type: {prediction_type})")
        
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