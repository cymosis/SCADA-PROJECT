"""
NT-SCADA Production Configuration
Central configuration management for batch and stream processing
"""

import os
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class KafkaConfig:
    """Kafka configuration"""
    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    group_id: str = "stream-processor-production"
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    auto_commit_interval_ms: int = 5000
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 10000


@dataclass
class InfluxDBConfig:
    """InfluxDB configuration"""
    url: str = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
    token: str = os.getenv("INFLUXDB_TOKEN", "nt-scada-token-secret-key-12345")
    org: str = os.getenv("INFLUXDB_ORG", "nt-scada")
    bucket: str = os.getenv("INFLUXDB_BUCKET", "scada_data")
    measurement: str = "sensor_data"


@dataclass
class MLflowConfig:
    """MLflow configuration"""
    uri: str = os.getenv("MLFLOW_URI", "http://mlflow:5000")
    experiment_name: str = "nt-scada-models"
    artifact_path: str = "/app/models/registry"


@dataclass
class BatchProcessingConfig:
    """Batch processing configuration"""
    data_days: int = 7
    test_size: float = 0.2
    random_state: int = 42
    
    # Binary classifier
    binary_n_estimators: int = 200
    binary_max_depth: int = 15
    binary_min_samples_split: int = 5
    binary_min_samples_leaf: int = 2
    
    # Multi-class classifier
    multiclass_n_estimators: int = 150
    multiclass_learning_rate: float = 0.1
    multiclass_max_depth: int = 5
    
    # Feature engineering
    window_sizes: list = None
    
    def __post_init__(self):
        if self.window_sizes is None:
            self.window_sizes = [5, 10, 30]


@dataclass
class StreamProcessingConfig:
    """Stream processing configuration"""
    kafka: KafkaConfig = None
    mlflow: MLflowConfig = None
    input_topic: str = "scada.sensors"
    output_topics: Dict[str, str] = None
    
    # Feature extraction
    feature_window_size: int = 4
    
    # Processing
    enable_ml_detection: bool = True
    use_rule_based_fallback: bool = True
    
    # Metrics
    metrics_log_interval: int = 100
    
    def __post_init__(self):
        if self.kafka is None:
            self.kafka = KafkaConfig()
        if self.mlflow is None:
            self.mlflow = MLflowConfig()
        if self.output_topics is None:
            self.output_topics = {
                "processed": "scada.processed",
                "anomalies": "scada.anomalies",
                "errors": "scada.errors"
            }


class ProductionConfig:
    """Master configuration container"""
    
    def __init__(self):
        self.kafka = KafkaConfig()
        self.influxdb = InfluxDBConfig()
        self.mlflow = MLflowConfig()
        self.batch = BatchProcessingConfig()
        self.stream = StreamProcessingConfig()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "kafka": vars(self.kafka),
            "influxdb": vars(self.influxdb),
            "mlflow": vars(self.mlflow),
            "batch": vars(self.batch),
            "stream": vars(self.stream),
        }
    
    def validate(self) -> bool:
        """Validate all configurations"""
        try:
            assert self.kafka.bootstrap_servers, "Kafka bootstrap servers required"
            assert self.influxdb.url, "InfluxDB URL required"
            assert self.mlflow.uri, "MLflow URI required"
            return True
        except AssertionError as e:
            raise ValueError(f"Configuration validation failed: {e}")


def get_config() -> ProductionConfig:
    """Get singleton configuration instance"""
    return ProductionConfig()


def get_batch_config() -> BatchProcessingConfig:
    """Get batch processing configuration"""
    return get_config().batch


def get_stream_config() -> StreamProcessingConfig:
    """Get stream processing configuration"""
    return get_config().stream


def get_influxdb_config() -> InfluxDBConfig:
    """Get InfluxDB configuration"""
    return get_config().influxdb


def get_mlflow_config() -> MLflowConfig:
    """Get MLflow configuration"""
    return get_config().mlflow
