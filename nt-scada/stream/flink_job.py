"""
NT-SCADA Flink Stream Processing Job
Performs real-time anomaly detection, windowed aggregation, and stateful alerting.
Migrated from legacy stream_processor.py to PyFlink.
"""

import os
import json
import logging
from datetime import datetime, timezone
import time

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaSink, KafkaRecordSerializationSchema, KafkaOffsetsInitializer
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.typeinfo import Types
from pyflink.datastream.functions import MapFunction, FilterFunction, ProcessWindowFunction, KeyedProcessFunction, RuntimeContext
from pyflink.datastream.window import TumblingEventTimeWindows
from pyflink.common import WatermarkStrategy, Duration, Time
from pyflink.datastream.state import ValueStateDescriptor

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')

class JsonParserMap(MapFunction):
    """Parses JSON string to dictionary"""
    def map(self, value):
        try:
            return json.loads(value)
        except Exception as e:
            logging.error(f"JSON Parse Error: {e}")
            return None

class ValidDataFilter(FilterFunction):
    """Filters out None values and ensures sensor_id and timestamp exist"""
    def filter(self, value):
        return value is not None and 'sensor_id' in value and 'timestamp' in value

class AverageAggregateFunction(ProcessWindowFunction):
    """
    Calculates the Average value for the sensor within the window.
    Returns JSON string result.
    """
    def process(self, key, context, elements):
        count = 0
        total_value = 0.0
        sensor_id = key
        
        start_ts = context.window().start
        end_ts = context.window().end
        
        for element in elements:
            # Safely get value, default to 0 if missing (though should be filtered ideally)
            val = element.get('value', 0)
            total_value += float(val)
            count += 1
            
        average = total_value / count if count > 0 else 0.0
        
        result = {
            'sensor_id': sensor_id,
            'window_start_iso': datetime.fromtimestamp(start_ts / 1000, timezone.utc).isoformat(),
            'window_end_iso': datetime.fromtimestamp(end_ts / 1000, timezone.utc).isoformat(),
            'average_value': average,
            'reading_count': count,
            'processed_timestamp': datetime.now(timezone.utc).isoformat()
        }
        yield json.dumps(result)

class StatefulAlertFunction(KeyedProcessFunction):
    """
    Stateful alerting:
    Alert only if a sensor's value remains in CRITICAL severity (value < 10 or > 90) for 3 consecutive events.
    """
    def open(self, runtime_context: RuntimeContext):
        # State to store consecutive critical count
        descriptor = ValueStateDescriptor("critical_count_state", Types.INT())
        self.critical_count_state = runtime_context.get_state(descriptor)

    def process_element(self, value, ctx):
        sensor_value = value.get('value', 50) # Default to 50 (safe)
        
        # Check if Critical
        is_critical = sensor_value < 10 or sensor_value > 90
        
        # Get current state
        current_count = self.critical_count_state.value()
        if current_count is None:
            current_count = 0
            
        if is_critical:
            current_count += 1
            self.critical_count_state.update(current_count)
            
            # Check threshold
            if current_count >= 3:
                # Trigger Alert
                alert = {
                    'sensor_id': value['sensor_id'],
                    'alert_type': 'CRITICAL_CONDITION_PERSISTENT',
                    'severity': 'CRITICAL',
                    'message': f"Sensor {value['sensor_id']} critical for {current_count} consecutive readings.",
                    'last_value': sensor_value,
                    'consecutive_events': current_count,
                    'timestamp': value['timestamp'],
                    'generated_at': datetime.now(timezone.utc).isoformat()
                }
                yield json.dumps(alert)
                # Note: We do NOT clear state here, so it continues to alert if it stays critical.
                # If we wanted to alert only once per 3, we would reset.
                # Requirement: "Alert only if... remains... for 3 consecutive events". 
                # Implies >= 3.
        else:
            # Reset state if normal value received
            if current_count > 0:
                self.critical_count_state.clear()

def timestamp_assigner(element, record_timestamp):
    """Extracts timestamp from Dict"""
    try:
        ts_str = element['timestamp']
        # Convert ISO string to epoch milliseconds
        # Handle 'Z' manually if needed, or use robust parser
        if ts_str.endswith('Z'):
            ts_str = ts_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(ts_str)
        return int(dt.timestamp() * 1000)
    except Exception:
        # Fallback to current time if parsing fails
        return int(time.time() * 1000)

def main():
    print("=" * 60)
    print("NT-SCADA PyFlink Stream Processing Job")
    print("Migration from legacy stream_processor.py completed.")
    print("=" * 60)

    # 1. Environment Setup
    env = StreamExecutionEnvironment.get_execution_environment()
    # Prallelism configurable via env var
    env.set_parallelism(int(os.environ.get('FLINK_PARALLELISM', '2')))
    # Ensure Kafka connector is loaded (using the path from previous file or standard path)
    env.add_jars("file:///opt/flink/lib/flink-sql-connector-kafka-1.18.0.jar")

    # 2. Define Source
    kafka_source = KafkaSource.builder() \
        .set_bootstrap_servers(KAFKA_BOOTSTRAP_SERVERS) \
        .set_topics("scada.sensors") \
        .set_group_id("scada-flink-group-v1") \
        .set_starting_offsets(KafkaOffsetsInitializer.latest()) \
        .set_value_only_deserializer(SimpleStringSchema()) \
        .build()

    stream = env.from_source(
        kafka_source,
        WatermarkStrategy.no_watermarks(), # specific strategy applied after parsing
        "Kafka Sensor Source"
    )

    # 3. Parse and Assign Watermarks
    parsed_stream = stream \
        .map(JsonParserMap()) \
        .filter(ValidDataFilter()) \
        .assign_timestamps_and_watermarks(
            WatermarkStrategy.for_bounded_out_of_orderness(Duration.of_seconds(5))
            .with_timestamp_assigner(timestamp_assigner)
        )

    # 4. Keyed Stream
    keyed_stream = parsed_stream.key_by(lambda x: x['sensor_id'])

    # 5. Logic Flow A: Windowing & Aggregation (Tumbling 60s)
    aggregated_stream = keyed_stream \
        .window(TumblingEventTimeWindows.of(Time.seconds(60))) \
        .process(AverageAggregateFunction(), output_type=Types.STRING())

    # 6. Logic Flow B: Stateful Alerting (Consecutive Criticals)
    alert_stream = keyed_stream \
        .process(StatefulAlertFunction(), output_type=Types.STRING())

    # 7. Define Sinks
    
    # Sink for Aggregates: scada.processed
    processed_sink = KafkaSink.builder() \
        .set_bootstrap_servers(KAFKA_BOOTSTRAP_SERVERS) \
        .set_record_serializer(
            KafkaRecordSerializationSchema.builder()
                .set_topic("scada.processed")
                .set_value_serialization_schema(SimpleStringSchema())
                .build()
        ) \
        .build()
    
    # Sink for Alerts: scada.anomalies
    anomalies_sink = KafkaSink.builder() \
        .set_bootstrap_servers(KAFKA_BOOTSTRAP_SERVERS) \
        .set_record_serializer(
            KafkaRecordSerializationSchema.builder()
                .set_topic("scada.anomalies")
                .set_value_serialization_schema(SimpleStringSchema())
                .build()
        ) \
        .build()

    # 8. Attach Sinks
    aggregated_stream.sink_to(processed_sink)
    alert_stream.sink_to(anomalies_sink)

    # Optional: Print for debugging
    # aggregated_stream.print()
    # alert_stream.print()

    print("Starting Flink DataStream Job...")
    env.execute("NT-SCADA Advanced Stream Processing")

if __name__ == "__main__":
    main()
