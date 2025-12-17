"""
Enhanced Streaming Consumer for Normal Data
Docker-compatible version with streaming algorithms
"""

import json
import os
import time
from datetime import datetime
from kafka import KafkaConsumer
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from collections import defaultdict, deque
import math

# ========================================
# STREAMING ALGORITHMS (Embedded)
# ========================================

class WelfordOnlineStats:
    """Welford's online algorithm for mean/variance"""
    def __init__(self):
        self.count = 0
        self.mean = 0.0
        self.M2 = 0.0
        self.min_val = float('inf')
        self.max_val = float('-inf')
    
    def update(self, value):
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.M2 += delta * delta2
        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)
    
    def get_stats(self):
        std = math.sqrt(self.M2 / self.count) if self.count > 1 else 0.0
        return {
            'count': self.count,
            'mean': self.mean if self.count > 0 else 0.0,
            'std': std,
            'min': self.min_val,
            'max': self.max_val
        }


class ADWIN:
    """Adaptive Windowing for drift detection"""
    def __init__(self, delta=0.002):
        self.delta = delta
        self.window = deque()
        self.total = 0.0
        self.width = 0
    
    def add_element(self, value):
        self.window.append(value)
        self.width += 1
        self.total += value
        
        if self.width < 10:
            return False
        
        # Simple drift detection
        split_point = self.width // 2
        recent = list(self.window)[-split_point:]
        old = list(self.window)[:split_point]
        
        if len(recent) == 0 or len(old) == 0:
            return False
        
        mean_recent = sum(recent) / len(recent)
        mean_old = sum(old) / len(old)
        
        epsilon = math.sqrt((1.0 / (2.0 * self.width)) * math.log(1.0 / self.delta))
        
        if abs(mean_recent - mean_old) > epsilon:
            self.window = deque(recent)
            self.width = len(recent)
            self.total = sum(recent)
            return True
        
        return False


class OnlineZScore:
    """Real-time Z-score computation"""
    def __init__(self, warmup_period=30):
        self.welford = WelfordOnlineStats()
        self.warmup_period = warmup_period
        self.is_warm = False
    
    def update_and_score(self, value):
        if self.welford.count >= self.warmup_period:
            self.is_warm = True
        
        z_score = None
        if self.is_warm:
            stats = self.welford.get_stats()
            std = stats['std']
            if std > 0:
                z_score = (value - stats['mean']) / std
        
        self.welford.update(value)
        return z_score
    
    def get_stats(self):
        return self.welford.get_stats()


class StreamingStatsTracker:
    """Tracks streaming statistics for all sensors"""
    def __init__(self, sensors):
        self.online_stats = {sensor: WelfordOnlineStats() for sensor in sensors}
        self.drift_detectors = {sensor: ADWIN(delta=0.002) for sensor in sensors}
        self.zscore_detectors = {sensor: OnlineZScore(warmup_period=30) for sensor in sensors}
        self.drift_events = {sensor: 0 for sensor in sensors}
        self.anomaly_events = {sensor: 0 for sensor in sensors}
    
    def update(self, sensor, value):
        if sensor not in self.online_stats:
            return None
        
        self.online_stats[sensor].update(value)
        
        drift_detected = self.drift_detectors[sensor].add_element(value)
        if drift_detected:
            self.drift_events[sensor] += 1
            print(f"🔴 DRIFT: {sensor}")
            self.zscore_detectors[sensor] = OnlineZScore(warmup_period=30)
        
        z_score = self.zscore_detectors[sensor].update_and_score(value)
        is_anomaly = False
        if z_score is not None and abs(z_score) > 3.0:
            is_anomaly = True
            self.anomaly_events[sensor] += 1
        
        return {
            'z_score': z_score,
            'is_anomaly': is_anomaly,
            'drift_detected': drift_detected,
            'stats': self.online_stats[sensor].get_stats()
        }
    
    def get_stats(self, sensor):
        if sensor not in self.online_stats:
            return None
        return {
            **self.online_stats[sensor].get_stats(),
            'drift_events': self.drift_events[sensor],
            'anomaly_events': self.anomaly_events[sensor]
        }

# ========================================
# CONFIGURATION
# ========================================

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
KAFKA_TOPIC = 'scada.normal'
KAFKA_GROUP_ID = 'normal-streaming-consumer'
INFLUXDB_URL = os.getenv('INFLUX_URL', 'http://influxdb:8086')
INFLUXDB_TOKEN = os.getenv('INFLUX_TOKEN', 'mytoken')
INFLUXDB_ORG = os.getenv('INFLUX_ORG', 'scada')
INFLUXDB_BUCKET = os.getenv('INFLUX_BUCKET', 'normal_data')
STATS_BUCKET = 'streaming_stats'
TAG_KEYS = ["P1_STATE", "P2_STATE", "P3_STATE", "P4_STATE", "P5_STATE", "P6_STATE"]

SENSOR_COLUMNS = [
    'LIT 101', 'LIT 301', 'LIT 401',
    'FIT 101', 'FIT 201', 'FIT 301', 'FIT 401', 'FIT 501', 'FIT 502',
    'AIT 201', 'AIT 202', 'AIT 203', 'AIT 301', 'AIT 302', 'AIT 303',
    'AIT 401', 'AIT 402', 'AIT 501', 'AIT 502', 'AIT 503', 'AIT 504',
    'DPIT 301'
]

# ========================================
# HELPER FUNCTIONS
# ========================================

def parse_timestamp(ts_value):
    """Convert timestamp STRING to DATETIME object"""
    if isinstance(ts_value, datetime):
        return ts_value
    if isinstance(ts_value, str):
        try:
            iso_str = ts_value.replace(' ', 'T').split('+')[0].rstrip('Z')
            return datetime.fromisoformat(iso_str)
        except:
            return datetime.utcnow()
    return datetime.utcnow()


def write_streaming_stats(write_api, stats_tracker, timestamp, org):
    """Write streaming statistics to InfluxDB"""
    for sensor in SENSOR_COLUMNS:
        stats = stats_tracker.get_stats(sensor)
        if stats and stats['count'] > 0:
            point = Point("streaming_stats") \
                .tag("sensor", sensor) \
                .time(timestamp, WritePrecision.NS) \
                .field("count", int(stats['count'])) \
                .field("mean", float(stats['mean'])) \
                .field("std", float(stats['std'])) \
                .field("min", float(stats['min'])) \
                .field("max", float(stats['max'])) \
                .field("drift_events", int(stats['drift_events'])) \
                .field("anomaly_events", int(stats['anomaly_events']))
            
            try:
                write_api.write(bucket=STATS_BUCKET, org=org, record=point)
            except Exception as e:
                # Silently handle if stats bucket doesn't exist
                pass


def ensure_stats_bucket(client, org):
    """Ensure streaming_stats bucket exists"""
    try:
        buckets_api = client.buckets_api()
        buckets = buckets_api.find_buckets().buckets
        
        if not any(b.name == STATS_BUCKET for b in buckets):
            print(f"[INIT] Creating {STATS_BUCKET} bucket...")
            buckets_api.create_bucket(bucket_name=STATS_BUCKET, org=org)
            print(f"[INIT] ✓ {STATS_BUCKET} bucket created")
        else:
            print(f"[INIT] ✓ {STATS_BUCKET} bucket exists")
    except Exception as e:
        print(f"[INIT] Warning: Could not create stats bucket: {e}")


# ========================================
# MAIN CONSUMER
# ========================================

def main():
    print(f"\n{'='*80}")
    print(f"STREAMING-ENHANCED NORMAL DATA CONSUMER")
    print(f"Features: Welford | ADWIN | Online Z-Score")
    print(f"{'='*80}\n")
    print(f"Starting Consumer...")
    time.sleep(5)
    
    # Connect to Kafka
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='earliest',
        group_id=KAFKA_GROUP_ID,
        value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )
    print(f"✓ Connected to Kafka: {KAFKA_TOPIC}")
    
    # Connect to InfluxDB
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    print(f"✓ Connected to InfluxDB")
    
    # Ensure stats bucket exists
    ensure_stats_bucket(client, INFLUXDB_ORG)
    
    # Initialize streaming tracker
    stats_tracker = StreamingStatsTracker(SENSOR_COLUMNS)
    print(f"✓ Streaming algorithms initialized for {len(SENSOR_COLUMNS)} sensors")
    print(f"\n{'='*80}\n")
    
    message_count = 0
    stats_write_interval = 100
    
    try:
        for msg in consumer:
            data = msg.value
            timestamp = parse_timestamp(data.get('t_stamp'))
            
            # Build point for sensor data
            point = Point("sensor_data")
            
            # Add tags
            for tag_key in TAG_KEYS:
                if tag_key in data:
                    point = point.tag(tag_key, str(data[tag_key]))
            
            point = point.time(timestamp, WritePrecision.NS)
            
            # Add fields and update streaming stats
            for key, value in data.items():
                if key == "t_stamp":
                    continue
                elif key not in TAG_KEYS:
                    # Try to convert to float, if fails keep as string
                    try:
                        numeric_value = float(value)
                        point = point.field(key, numeric_value)
                        
                        # UPDATE STREAMING ALGORITHMS
                        if key in SENSOR_COLUMNS:
                            result = stats_tracker.update(key, numeric_value)
                            
                            if result and result['z_score'] is not None:
                                point = point.field(f"{key}_zscore", float(result['z_score']))
                                if result['is_anomaly']:
                                    point = point.tag(f"{key}_anomaly", "true")
                    except (ValueError, TypeError):
                        # If conversion fails, store as string
                        point = point.field(key, str(value))
            
            # Write sensor data
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
            message_count += 1
            
            # Periodically write streaming statistics
            if message_count % stats_write_interval == 0:
                write_streaming_stats(write_api, stats_tracker, timestamp, INFLUXDB_ORG)
                print(f"⚡ {message_count} messages processed")
                
                # Sample stats
                sample_sensor = 'LIT 101'
                sample_stats = stats_tracker.get_stats(sample_sensor)
                if sample_stats and sample_stats['count'] > 0:
                    print(f"   {sample_sensor}: mean={sample_stats['mean']:.2f}, "
                          f"std={sample_stats['std']:.2f}, "
                          f"drifts={sample_stats['drift_events']}, "
                          f"anomalies={sample_stats['anomaly_events']}")
    
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping consumer...")
    finally:
        write_streaming_stats(write_api, stats_tracker, datetime.utcnow(), INFLUXDB_ORG)
        
        print(f"\n{'='*80}")
        print(f"FINAL STATISTICS")
        print(f"{'='*80}")
        print(f"Total messages: {message_count}")
        print(f"\nTop 5 Sensors:")
        for sensor in SENSOR_COLUMNS[:5]:
            stats = stats_tracker.get_stats(sensor)
            if stats and stats['count'] > 0:
                print(f"  {sensor}: {stats['count']} samples, "
                      f"mean={stats['mean']:.2f}, "
                      f"drifts={stats['drift_events']}, "
                      f"anomalies={stats['anomaly_events']}")
        print(f"{'='*80}\n")
        
        consumer.close()
        client.close()


if __name__ == "__main__":
    main()
