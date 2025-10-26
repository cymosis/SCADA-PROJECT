"""
NT-SCADA Flink Stream Processing Job
Performs real-time anomaly detection and classification on sensor data
Uses PyFlink for stream processing
"""

import os
import json
from datetime import datetime
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer, KafkaSink, KafkaRecordSerializationSchema
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.typeinfo import Types
from pyflink.datastream.functions import MapFunction, FilterFunction


# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'nt-scada-token-secret-key-12345')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'nt-scada')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', 'scada_data')


class AnomalyDetector(MapFunction):
    """
    Rule-based anomaly detection
    Detects anomalies when value < 20 or > 80
    """
    
    def map(self, value):
        try:
            data = json.loads(value)
            sensor_value = data.get('value', 50)
            
            # Rule-based anomaly detection
            is_anomaly = sensor_value < 20 or sensor_value > 80
            
            # Classify severity
            if sensor_value < 10 or sensor_value > 90:
                severity = 'CRITICAL'
            elif sensor_value < 20 or sensor_value > 80:
                severity = 'HIGH'
            elif sensor_value < 25 or sensor_value > 75:
                severity = 'MEDIUM'
            else:
                severity = 'LOW'
            
            # Classify sensor type category
            sensor_type = data.get('sensor_type', 'unknown')
            if sensor_type in ['temperature', 'pressure']:
                category = 'THERMAL_PRESSURE'
            elif sensor_type in ['flow_rate', 'vibration']:
                category = 'MECHANICAL'
            elif sensor_type in ['voltage', 'current']:
                category = 'ELECTRICAL'
            else:
                category = 'OTHER'
            
            # Add classification results
            data['anomaly_detected'] = is_anomaly
            data['severity'] = severity
            data['category'] = category
            data['processed_timestamp'] = datetime.utcnow().isoformat() + 'Z'
            
            return json.dumps(data)
            
        except Exception as e:
            print(f"Error processing record: {e}")
            return value


class FineGrainedClassifier(MapFunction):
    """
    Fine-grained classification of sensor data
    Classifies into multiple operational states
    """
    
    def map(self, value):
        try:
            data = json.loads(value)
            sensor_value = data.get('value', 50)
            
            # Fine-grained operational state classification
            if sensor_value < 10:
                operational_state = 'CRITICALLY_LOW'
            elif sensor_value < 20:
                operational_state = 'LOW'
            elif sensor_value < 30:
                operational_state = 'BELOW_OPTIMAL'
            elif sensor_value < 70:
                operational_state = 'OPTIMAL'
            elif sensor_value < 80:
                operational_state = 'ABOVE_OPTIMAL'
            elif sensor_value < 90:
                operational_state = 'HIGH'
            else:
                operational_state = 'CRITICALLY_HIGH'
            
            # Add fine-grained classification
            data['operational_state'] = operational_state
            
            return json.dumps(data)
            
        except Exception as e:
            print(f"Error in fine-grained classification: {e}")
            return value


class AnomalyFilter(FilterFunction):
    """Filter only anomalous records"""
    
    def filter(self, value):
        try:
            data = json.loads(value)
            return data.get('anomaly_detected', False)
        except:
            return False


def main():
    """Main Flink job"""
    print("=" * 60)
    print("NT-SCADA Flink Stream Processing Job")
    print("=" * 60)
    
    # Create execution environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(2)
    
    # Add Kafka connector JAR
    env.add_jars("file:///opt/flink/lib/flink-sql-connector-kafka-1.18.0.jar")
    
    # Configure Kafka source for sensors
    kafka_source = KafkaSource.builder() \
        .set_bootstrap_servers(KAFKA_BOOTSTRAP_SERVERS) \
        .set_topics("scada.sensors") \
        .set_group_id("flink-stream-processor") \
        .set_starting_offsets(KafkaOffsetsInitializer.latest()) \
        .set_value_only_deserializer(SimpleStringSchema()) \
        .build()
    
    # Create data stream from Kafka
    sensor_stream = env.from_source(
        kafka_source,
        watermark_strategy=None,
        source_name="Kafka Sensor Source"
    )
    
    # Pipeline 1: Binary anomaly detection
    anomaly_stream = sensor_stream.map(
        AnomalyDetector(),
        output_type=Types.STRING()
    )
    
    # Pipeline 2: Fine-grained classification
    classified_stream = anomaly_stream.map(
        FineGrainedClassifier(),
        output_type=Types.STRING()
    )
    
    # Configure Kafka sink for processed data
    kafka_sink = KafkaSink.builder() \
        .set_bootstrap_servers(KAFKA_BOOTSTRAP_SERVERS) \
        .set_record_serializer(
            KafkaRecordSerializationSchema.builder()
                .set_topic("scada.processed")
                .set_value_serialization_schema(SimpleStringSchema())
                .build()
        ) \
        .build()
    
    # Send processed data to Kafka
    classified_stream.sink_to(kafka_sink)
    
    # Filter and send only anomalies to separate topic
    anomaly_only_stream = classified_stream.filter(AnomalyFilter())
    
    anomaly_sink = KafkaSink.builder() \
        .set_bootstrap_servers(KAFKA_BOOTSTRAP_SERVERS) \
        .set_record_serializer(
            KafkaRecordSerializationSchema.builder()
                .set_topic("scada.anomalies")
                .set_value_serialization_schema(SimpleStringSchema())
                .build()
        ) \
        .build()
    
    anomaly_only_stream.sink_to(anomaly_sink)
    
    # Print to console for monitoring
    classified_stream.print()
    
    # Execute the job
    print("Starting Flink stream processing job...")
    env.execute("NT-SCADA Stream Processing")


if __name__ == "__main__":
    main()
