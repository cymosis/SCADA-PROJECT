"""
InfluxDB Sink for Flink Analytics
Writes analytics data to InfluxDB time-series database
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger(__name__)

class InfluxDBSink:
    """Custom InfluxDB sink for Flink analytics"""
    
    def __init__(self, influx_url: str, token: str, org: str, bucket: str):
        self.influx_url = influx_url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.client = None
        self.write_api = None
        self._connect()
    
    def _connect(self):
        """Connect to InfluxDB"""
        try:
            self.client = InfluxDBClient(
                url=self.influx_url,
                token=self.token,
                org=self.org
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            logger.info(f"Connected to InfluxDB at {self.influx_url}")
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
    
    def invoke(self, value: Dict[str, Any]):
        """Write analytics data to InfluxDB"""
        try:
            if not self.write_api:
                logger.error("InfluxDB write_api not initialized")
                return
            
            timestamp = datetime.fromisoformat(value.get('timestamp', datetime.now().isoformat()))
            
            if value.get('analytics_type') == 'kafka_realtime':
                self._write_analytics(value, timestamp)
            elif value.get('alert_id'):
                self._write_alert(value, timestamp)
            else:
                self._write_generic(value, timestamp)
                
        except Exception as e:
            logger.error(f"Error writing to InfluxDB: {e}")
    
    def _write_analytics(self, analytics: Dict[str, Any], timestamp: datetime):
        """Write analytics data"""
        # System analytics
        system = analytics.get('system_analytics', {})
        point = Point("system_analytics") \
            .tag("analytics_type", "kafka_realtime") \
            .time(timestamp) \
            .field("total_throughput", system.get('total_throughput', 0)) \
            .field("total_consumer_lag", system.get('total_consumer_lag', 0)) \
            .field("healthy_consumers", system.get('healthy_consumers', 0)) \
            .field("total_consumers", system.get('total_consumers', 0)) \
            .field("system_health_score", system.get('system_health_score', 0))
        
        self.write_api.write(bucket=self.bucket, record=point)
        
        # Consumer analytics
        for consumer_name, consumer_data in analytics.get('consumer_analytics', {}).items():
            point = Point("consumer_analytics") \
                .tag("consumer_name", consumer_name) \
                .tag("topic", consumer_data.get('topic', '')) \
                .tag("status", consumer_data.get('status', 'unknown')) \
                .time(timestamp) \
                .field("lag_records", consumer_data.get('lag_records', 0)) \
                .field("lag_mb", consumer_data.get('lag_mb', 0)) \
                .field("consumption_rate", consumer_data.get('consumption_rate', 0)) \
                .field("last_message_age_seconds", consumer_data.get('last_message_age_seconds', 0)) \
                .field("error_rate", consumer_data.get('error_rate', 0))
            
            self.write_api.write(bucket=self.bucket, record=point)
        
        # Producer analytics
        for producer_name, producer_data in analytics.get('producer_analytics', {}).items():
            point = Point("producer_analytics") \
                .tag("producer_name", producer_name) \
                .tag("topic", producer_data.get('topic', '')) \
                .tag("status", producer_data.get('status', 'unknown')) \
                .time(timestamp) \
                .field("messages_per_second", producer_data.get('messages_per_second', 0)) \
                .field("bytes_per_second", producer_data.get('bytes_per_second', 0)) \
                .field("error_rate", producer_data.get('error_rate', 0)) \
                .field("request_latency_ms", producer_data.get('request_latency_ms', 0)) \
                .field("compression_ratio", producer_data.get('compression_ratio', 0))
            
            self.write_api.write(bucket=self.bucket, record=point)
    
    def _write_alert(self, alert: Dict[str, Any], timestamp: datetime):
        """Write alert data"""
        point = Point("alerts") \
            .tag("alert_id", alert.get('alert_id', '')) \
            .tag("alert_type", alert.get('alert_type', '')) \
            .tag("severity", alert.get('severity', '')) \
            .tag("component", alert.get('component', '')) \
            .time(timestamp) \
            .field("value", alert.get('value', 0))
        
        if 'message' in alert:
            point.field("message", alert['message'])
        
        self.write_api.write(bucket=self.bucket, record=point)
    
    def _write_generic(self, data: Dict[str, Any], timestamp: datetime):
        """Write generic data"""
        point = Point("generic_analytics") \
            .tag("data_type", data.get('analytics_type', 'unknown')) \
            .time(timestamp)
        
        for key, value in data.items():
            if isinstance(value, (int, float)):
                point.field(key, value)
        
        self.write_api.write(bucket=self.bucket, record=point)
    
    def close(self):
        """Close InfluxDB connection"""
        if self.client:
            self.client.close()
            logger.info("InfluxDB connection closed")