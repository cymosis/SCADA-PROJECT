"""
NT-SCADA Stream Processor with ML Models
Performs real-time anomaly detection and classification using trained SWaT models
"""

import os
import json
import time
import joblib
import numpy as np
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')

# Load trained ML models
def load_ml_models():
    """Load the trained SWaT ML models"""
    try:
        # Load binary classification model (Normal vs Anomalous)
        binary_model = joblib.load('/app/models/binary_classifier_swat.pkl')
        print("✅ Binary classification model loaded")
        
        # Load fine-grained classification model
        fine_grained_model = joblib.load('/app/models/fine_grained_classifier_swat.pkl')
        print("✅ Fine-grained classification model loaded")
        
        return binary_model, fine_grained_model
    except Exception as e:
        print(f"❌ Error loading ML models: {e}")
        return None, None

# SWaT sensor mapping - map synthetic sensors to SWaT features
SWAT_SENSOR_MAPPING = {
    'temperature_001': ['P1_STATE', 50, 10],  # [feature, normal_value, std]
    'temperature_002': ['LIT101.Pv', 50, 10],
    'temperature_003': ['FIT101.Pv', 50, 10],
    'temperature_004': ['MV101.Status', 50, 10],
    'temperature_005': ['P1_STATE', 50, 10],
    'pressure_001': ['LIT101.Pv', 50, 10],
    'pressure_002': ['FIT101.Pv', 50, 10],
    'pressure_003': ['MV101.Status', 50, 10],
    'pressure_004': ['P1_STATE', 50, 10],
    'pressure_005': ['LIT101.Pv', 50, 10],
    'flow_rate_001': ['FIT101.Pv', 50, 10],
    'flow_rate_002': ['MV101.Status', 50, 10],
    'flow_rate_003': ['P1_STATE', 50, 10],
    'flow_rate_004': ['LIT101.Pv', 50, 10],
    'flow_rate_005': ['FIT101.Pv', 50, 10],
    'vibration_001': ['MV101.Status', 50, 10],
    'vibration_002': ['P1_STATE', 50, 10],
    'vibration_003': ['LIT101.Pv', 50, 10],
    'vibration_004': ['FIT101.Pv', 50, 10],
    'vibration_005': ['MV101.Status', 50, 10],
    'voltage_001': ['P1_STATE', 50, 10],
    'voltage_002': ['LIT101.Pv', 50, 10],
    'voltage_003': ['FIT101.Pv', 50, 10],
    'voltage_004': ['MV101.Status', 50, 10],
    'voltage_005': ['P1_STATE', 50, 10],
    'current_001': ['LIT101.Pv', 50, 10],
    'current_002': ['FIT101.Pv', 50, 10],
    'current_003': ['MV101.Status', 50, 10],
    'current_004': ['P1_STATE', 50, 10],
    'current_005': ['LIT101.Pv', 50, 10]
}

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
                group_id='stream-processor-ml',
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            print(f"✅ Consumer connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return consumer
        except NoBrokersAvailable:
            print(f"⚠️ Kafka not available (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay}s...")
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
            print(f"✅ Producer connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except NoBrokersAvailable:
            print(f"⚠️ Kafka not available (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay}s...")
            time.sleep(retry_delay)

    raise Exception("Failed to connect to Kafka after maximum retries")

def map_to_swat_features(sensor_data):
    """
    Map synthetic sensor data to SWaT feature space for ML model prediction
    """
    sensor_id = sensor_data.get('sensor_id', '')
    
    if sensor_id in SWAT_SENSOR_MAPPING:
        feature_name, normal_value, std = SWAT_SENSOR_MAPPING[sensor_id]
        # Create feature vector matching training data format
        features = np.array([[normal_value, normal_value, normal_value, normal_value]])  # Base features
        
        # Modify based on actual sensor value (simulate correlation)
        sensor_value = sensor_data.get('value', 50)
        deviation = (sensor_value - 50) / 50  # Normalize to -1 to 1
        
        # Apply deviation to create realistic feature patterns
        for i in range(4):
            features[0][i] += deviation * std * (i + 1)
            
        return features
    else:
        # Default feature vector
        return np.array([[50, 50, 50, 50]])

def ml_anomaly_detection(binary_model, sensor_data):
    """
    Pipeline 1: Binary anomaly detection using ML model
    """
    if binary_model is None:
        return False, 'MODEL_UNAVAILABLE'
    
    try:
        # Map sensor data to SWaT features
        features = map_to_swat_features(sensor_data)
        
        # Predict using ML model
        prediction = binary_model.predict(features)[0]
        probability = binary_model.predict_proba(features)[0]
        
        is_anomaly = bool(prediction == 1)
        confidence = max(probability)
        
        return is_anomaly, confidence
    except Exception as e:
        print(f"❌ ML anomaly detection error: {e}")
        return False, 'ERROR'

def ml_fine_grained_classification(fine_grained_model, sensor_data):
    """
    Pipeline 2: Fine-grained classification using ML model
    """
    if fine_grained_model is None:
        return 'MODEL_UNAVAILABLE'
    
    try:
        # Map sensor data to SWaT features
        features = map_to_swat_features(sensor_data)
        
        # Predict using ML model
        prediction = fine_grained_model.predict(features)[0]
        
        # Map numeric prediction to operational states
        state_mapping = {
            0: 'OPTIMAL',
            1: 'ABOVE_OPTIMAL', 
            2: 'HIGH',
            3: 'CRITICALLY_HIGH',
            4: 'BELOW_OPTIMAL',
            5: 'LOW',
            6: 'CRITICALLY_LOW'
        }
        
        return state_mapping.get(prediction, 'UNKNOWN')
    except Exception as e:
        print(f"❌ ML fine-grained classification error: {e}")
        return 'ERROR'

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

def process_sensor_data_ml(data, binary_model, fine_grained_model):
    """
    Process sensor data through ML pipelines:
    1. Binary anomaly detection (ML model)
    2. Fine-grained classification (ML model)
    """
    sensor_value = data.get('value', 50)
    sensor_type = data.get('sensor_type', 'unknown')

    # Pipeline 1: ML Binary anomaly detection
    is_anomaly, confidence = ml_anomaly_detection(binary_model, data)
    severity = classify_severity(sensor_value)
    category = classify_category(sensor_type)

    # Pipeline 2: ML Fine-grained classification
    operational_state = ml_fine_grained_classification(fine_grained_model, data)

    # Add processing results
    processed_data = data.copy()
    processed_data.update({
        'anomaly_detected': is_anomaly,
        'confidence': confidence,
        'severity': severity,
        'category': category,
        'operational_state': operational_state,
        'processing_method': 'ML_MODEL',
        'model_version': 'SWaT_v1',
        'processed_timestamp': datetime.utcnow().isoformat() + 'Z'
    })

    return processed_data

def main():
    """Main stream processing loop with ML models"""
    print("=" * 60)
    print("NT-SCADA Stream Processor with ML Models")
    print("=" * 60)
    print(f"Kafka Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Input Topic: scada.sensors")
    print(f"Output Topics: scada.processed, scada.anomalies")
    print("=" * 60)

    # Load ML models
    binary_model, fine_grained_model = load_ml_models()
    
    if binary_model is None or fine_grained_model is None:
        print("❌ Failed to load ML models. Exiting.")
        return

    # Create Kafka consumer and producer
    consumer = create_kafka_consumer()
    producer = create_kafka_producer()

    processed_count = 0
    anomaly_count = 0

    try:
        print("✅ ML Stream processor started. Processing messages...")

        for message in consumer:
            try:
                # Get sensor data
                sensor_data = message.value

                # Process through ML pipelines
                processed_data = process_sensor_data_ml(sensor_data, binary_model, fine_grained_model)

                # Send to processed topic
                producer.send('scada.processed', value=processed_data)
                processed_count += 1

                # If anomaly detected, send to anomalies topic
                if processed_data['anomaly_detected']:
                    producer.send('scada.anomalies', value=processed_data)
                    anomaly_count += 1

                # Log progress
                if processed_count % 50 == 0:
                    print(f"✅ Processed: {processed_count} | Anomalies: {anomaly_count} | "
                          f"Latest: {processed_data['sensor_id']} = {processed_data['value']} "
                          f"[{processed_data['operational_state']}] Confidence: {processed_data['confidence']:.2f}")

            except Exception as e:
                print(f"⚠️ Error processing message: {e}")
                continue

    except KeyboardInterrupt:
        print("\n⚠️ Shutting down ML stream processor...")
    finally:
        consumer.close()
        producer.close()
        print(f"✅ ML Stream processor stopped. Processed: {processed_count}, Anomalies: {anomaly_count}")

if __name__ == "__main__":
    main()