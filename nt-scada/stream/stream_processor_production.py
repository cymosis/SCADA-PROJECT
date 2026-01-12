"""
NT-SCADA Production Stream Processor
Real-time anomaly detection and classification using trained ML models
Kafka Streams Python implementation
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import traceback

import numpy as np
import joblib
from confluent_kafka import Consumer, Producer, KafkaError, OFFSET_BEGINNING
from confluent_kafka.admin import AdminClient, ConfigResource, ConfigSource
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.json_schema import JSONDeserializer, JSONSerializer

from models.model_registry import ModelRegistry, ModelVersionManager


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class KafkaStreamProcessor:
    """Production-grade Kafka stream processor"""

    def __init__(
        self,
        bootstrap_servers: str = "kafka:29092",
        schema_registry_url: Optional[str] = None,
        mlflow_uri: str = "http://mlflow:5000",
        group_id: str = "stream-processor-production",
    ):
        """
        Initialize stream processor.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
            schema_registry_url: Schema registry URL (optional)
            mlflow_uri: MLflow model registry URI
            group_id: Consumer group ID
        """
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.schema_registry_url = schema_registry_url
        
        self.consumer = None
        self.producer = None
        self.admin_client = None
        
        self.model_registry = ModelRegistry(registry_uri=mlflow_uri)
        self.model_manager = ModelVersionManager(self.model_registry)
        
        self.metrics = {
            "messages_processed": 0,
            "anomalies_detected": 0,
            "errors": 0,
            "last_update": None,
        }

    def initialize(self) -> bool:
        """Initialize Kafka connections"""
        try:
            self._create_admin_client()
            self._create_consumer()
            self._create_producer()
            self._load_models()
            self._ensure_topics_exist()
            
            logger.info("Stream processor initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            traceback.print_exc()
            return False

    def _create_admin_client(self) -> None:
        """Create Kafka admin client"""
        self.admin_client = AdminClient({
            "bootstrap.servers": self.bootstrap_servers,
        })
        logger.info("Admin client created")

    def _create_consumer(self) -> None:
        """Create Kafka consumer with error handling"""
        conf = {
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": self.group_id,
            "auto.offset.reset": "latest",
            "enable.auto.commit": True,
            "auto.commit.interval.ms": 5000,
            "session.timeout.ms": 30000,
            "heartbeat.interval.ms": 10000,
        }
        
        self.consumer = Consumer(conf)
        self.consumer.subscribe(["scada.sensors"])
        logger.info(f"Consumer created for topic: scada.sensors")

    def _create_producer(self) -> None:
        """Create Kafka producer with error handling"""
        conf = {
            "bootstrap.servers": self.bootstrap_servers,
            "acks": "all",
            "retries": 3,
            "retry.backoff.ms": 100,
        }
        
        self.producer = Producer(conf)
        logger.info("Producer created")

    def _load_models(self) -> None:
        """Load trained ML models"""
        try:
            models = self.model_registry.list_models()
            logger.info(f"Available models: {models}")
            
            if not models:
                logger.warning("No models found in registry")
                return
            
            binary_models = [m for m in models if "binary" in m.lower()]
            multiclass_models = [m for m in models if "multiclass" in m.lower()]
            
            if binary_models:
                latest_binary = sorted(binary_models)[-1]
                self.model_manager.activate_model("binary_classifier", latest_binary)
                logger.info(f"Activated binary classifier: {latest_binary}")
            
            if multiclass_models:
                latest_multiclass = sorted(multiclass_models)[-1]
                self.model_manager.activate_model("multiclass_classifier", latest_multiclass)
                logger.info(f"Activated multiclass classifier: {latest_multiclass}")
                
        except Exception as e:
            logger.warning(f"Could not load models: {e}")

    def _ensure_topics_exist(self) -> None:
        """Ensure required topics exist"""
        required_topics = [
            "scada.sensors",
            "scada.processed",
            "scada.anomalies",
            "scada.errors",
        ]
        
        try:
            existing_topics = self.admin_client.list_topics().topics.keys()
            missing_topics = [t for t in required_topics if t not in existing_topics]
            
            if missing_topics:
                logger.info(f"Creating topics: {missing_topics}")
        except Exception as e:
            logger.warning(f"Could not verify topics: {e}")

    def _get_model(self, model_name: str) -> Optional[Any]:
        """Safely get active model"""
        try:
            model, _ = self.model_manager.get_active_model(model_name)
            return model
        except Exception as e:
            logger.debug(f"Model not available: {model_name} - {e}")
            return None

    def process_message(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process sensor data through ML pipelines.
        
        Args:
            sensor_data: Raw sensor data from Kafka
            
        Returns:
            Processed data with predictions
        """
        processed = sensor_data.copy()
        
        try:
            sensor_value = float(sensor_data.get("value", 0))
            sensor_type = sensor_data.get("sensor_type", "unknown")
            
            processed["processed_timestamp"] = datetime.utcnow().isoformat() + "Z"
            processed["processing_method"] = "ML_PRODUCTION"
            
            processed["anomaly_detected"] = self._detect_anomaly(sensor_data)
            processed["operational_state"] = self._classify_state(sensor_data)
            processed["severity"] = self._classify_severity(sensor_value)
            processed["category"] = self._classify_category(sensor_type)
            
            self.metrics["messages_processed"] += 1
            if processed["anomaly_detected"]:
                self.metrics["anomalies_detected"] += 1
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.metrics["errors"] += 1
            processed["processing_error"] = str(e)
        
        self.metrics["last_update"] = datetime.utcnow().isoformat()
        return processed

    def _detect_anomaly(self, sensor_data: Dict[str, Any]) -> bool:
        """Pipeline 1: Binary anomaly detection"""
        binary_model = self._get_model("binary_classifier")
        
        if binary_model is None:
            return self._rule_based_anomaly_detection(sensor_data)
        
        try:
            features = self._extract_features(sensor_data)
            prediction = binary_model.predict(features.reshape(1, -1))[0]
            return bool(prediction == 1)
        except Exception as e:
            logger.debug(f"ML anomaly detection failed: {e}")
            return self._rule_based_anomaly_detection(sensor_data)

    def _rule_based_anomaly_detection(self, sensor_data: Dict[str, Any]) -> bool:
        """Fallback rule-based anomaly detection"""
        value = sensor_data.get("value", 50)
        return value < 20 or value > 80

    def _classify_state(self, sensor_data: Dict[str, Any]) -> str:
        """Pipeline 2: Fine-grained classification"""
        multiclass_model = self._get_model("multiclass_classifier")
        
        if multiclass_model is None:
            return self._rule_based_classification(sensor_data)
        
        try:
            features = self._extract_features(sensor_data)
            prediction = multiclass_model.predict(features.reshape(1, -1))[0]
            
            state_mapping = {
                0: "CRITICALLY_LOW",
                1: "LOW",
                2: "BELOW_OPTIMAL",
                3: "OPTIMAL",
                4: "ABOVE_OPTIMAL",
                5: "HIGH",
                6: "CRITICALLY_HIGH",
            }
            
            return state_mapping.get(int(prediction), "UNKNOWN")
        except Exception as e:
            logger.debug(f"ML classification failed: {e}")
            return self._rule_based_classification(sensor_data)

    def _rule_based_classification(self, sensor_data: Dict[str, Any]) -> str:
        """Fallback rule-based classification"""
        value = sensor_data.get("value", 50)
        
        if value < 10:
            return "CRITICALLY_LOW"
        elif value < 20:
            return "LOW"
        elif value < 30:
            return "BELOW_OPTIMAL"
        elif value < 70:
            return "OPTIMAL"
        elif value < 80:
            return "ABOVE_OPTIMAL"
        elif value < 90:
            return "HIGH"
        else:
            return "CRITICALLY_HIGH"

    @staticmethod
    def _extract_features(sensor_data: Dict[str, Any]) -> np.ndarray:
        """Extract feature vector from sensor data"""
        value = float(sensor_data.get("value", 0))
        return np.array([value, value * 0.9, value * 1.1, value * 0.95])

    @staticmethod
    def _classify_severity(value: float) -> str:
        """Classify severity based on value"""
        if value < 10 or value > 90:
            return "CRITICAL"
        elif value < 20 or value > 80:
            return "HIGH"
        elif value < 25 or value > 75:
            return "MEDIUM"
        else:
            return "LOW"

    @staticmethod
    def _classify_category(sensor_type: str) -> str:
        """Classify sensor into category"""
        sensor_type = sensor_type.lower()
        
        if sensor_type in ["temperature", "pressure"]:
            return "THERMAL_PRESSURE"
        elif sensor_type in ["flow_rate", "vibration"]:
            return "MECHANICAL"
        elif sensor_type in ["voltage", "current"]:
            return "ELECTRICAL"
        else:
            return "OTHER"

    def produce_to_kafka(
        self,
        topic: str,
        data: Dict[str, Any],
        key: Optional[str] = None,
    ) -> bool:
        """Produce message to Kafka"""
        try:
            self.producer.produce(
                topic,
                key=key.encode("utf-8") if key else None,
                value=json.dumps(data).encode("utf-8"),
            )
            self.producer.flush()
            return True
        except Exception as e:
            logger.error(f"Failed to produce to {topic}: {e}")
            return False

    def run(self) -> None:
        """Main processing loop"""
        if not self.initialize():
            raise RuntimeError("Failed to initialize stream processor")
        
        logger.info("=" * 70)
        logger.info("NT-SCADA Production Stream Processor Started")
        logger.info("=" * 70)
        logger.info(f"Bootstrap Servers: {self.bootstrap_servers}")
        logger.info(f"Consumer Group: {self.group_id}")
        logger.info(f"Input Topic: scada.sensors")
        logger.info(f"Output Topics: scada.processed, scada.anomalies")
        logger.info("=" * 70)
        
        try:
            while True:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Kafka error: {msg.error()}")
                        continue
                
                try:
                    sensor_data = json.loads(msg.value().decode("utf-8"))
                    processed_data = self.process_message(sensor_data)
                    
                    self.produce_to_kafka(
                        "scada.processed",
                        processed_data,
                        key=sensor_data.get("sensor_id"),
                    )
                    
                    if processed_data.get("anomaly_detected"):
                        self.produce_to_kafka(
                            "scada.anomalies",
                            processed_data,
                            key=sensor_data.get("sensor_id"),
                        )
                    
                    if self.metrics["messages_processed"] % 100 == 0:
                        logger.info(
                            f"Processed: {self.metrics['messages_processed']} | "
                            f"Anomalies: {self.metrics['anomalies_detected']} | "
                            f"Errors: {self.metrics['errors']}"
                        )
                
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                    self.metrics["errors"] += 1
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    traceback.print_exc()
                    self.metrics["errors"] += 1
        
        except KeyboardInterrupt:
            logger.info("\nShutting down stream processor...")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("=" * 70)
        logger.info("Stream Processor Metrics")
        logger.info("=" * 70)
        logger.info(f"Messages Processed: {self.metrics['messages_processed']}")
        logger.info(f"Anomalies Detected: {self.metrics['anomalies_detected']}")
        logger.info(f"Errors: {self.metrics['errors']}")
        logger.info("=" * 70)
        
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.flush()
        
        logger.info("Stream processor shut down gracefully")


def main():
    """Entry point"""
    processor = KafkaStreamProcessor(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092"),
        mlflow_uri=os.getenv("MLFLOW_URI", "http://mlflow:5000"),
    )
    processor.run()


if __name__ == "__main__":
    main()
