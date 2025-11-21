# NT-SCADA Production Implementation Guide

## Overview

This guide covers the professional, production-grade implementations for batch processing and real-time stream processing in the NT-SCADA system.

## Architecture Components

### 1. Model Registry (MLflow)

**Location**: `models/model_registry.py`

Professional model management with versioning, tracking, and registry capabilities.

#### Features:
- **Model Registration**: Store trained models with metadata, metrics, and hyperparameters
- **Model Versioning**: Automatic version tracking with timestamps
- **Dual Backend**: MLflow server (preferred) or local filesystem fallback
- **Metadata Management**: Track features, metrics, parameters, and custom metadata
- **Model Activation**: Switch between model versions at runtime

#### Usage:

```python
from models import ModelRegistry, ModelVersionManager

registry = ModelRegistry(registry_uri="http://mlflow:5000")

model_id = registry.register_model(
    model=trained_model,
    model_name="binary_classifier",
    model_type="RandomForest",
    version="v1.0",
    metrics={"accuracy": 0.95, "f1": 0.92},
    params={"n_estimators": 200, "max_depth": 15},
    metadata={"description": "Production binary classifier"},
    features=feature_names
)

model, metadata = registry.load_model(model_id)
```

---

## 2. Batch Processing Pipeline

**Location**: `batch/batch_processor_flink.py`

Professional batch analytics and ML model training pipeline with Apache Flink integration.

### Architecture:

```
┌─────────────────────────────────────────────────────────┐
│           Batch Processing Pipeline                      │
├─────────────────────────────────────────────────────────┤
│  1. Data Loading (InfluxDB)                             │
│     └─> ScadaDataLoader fetches 7 days of sensor data   │
│                                                         │
│  2. Feature Engineering                                 │
│     └─> Time-based features (hour, day_of_week)        │
│     └─> Statistical features (rolling windows)          │
│     └─> Aggregated statistics per sensor               │
│                                                         │
│  3. Binary Classifier Training                          │
│     ├─> Features: temperature, pressure, flow, vibration
│     ├─> Target: anomaly (0/1)                          │
│     ├─> Algorithm: Random Forest (200 trees)           │
│     └─> Metrics: Accuracy, Precision, Recall, F1, ROCAUC
│                                                         │
│  4. Multi-class Classifier Training                     │
│     ├─> Features: same as binary                        │
│     ├─> Target: 7 operational states                   │
│     ├─> Algorithm: Gradient Boosting                   │
│     └─> Metrics: Weighted Precision, Recall, F1        │
│                                                         │
│  5. Model Registry & Persistence                        │
│     └─> Register to MLflow with metadata               │
│     └─> Save metrics and reports                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Components:

#### ScadaDataLoader
```python
loader = ScadaDataLoader(
    url="http://influxdb:8086",
    token="nt-scada-token-secret-key-12345",
    org="nt-scada",
    bucket="scada_data"
)

loader.connect()
df = loader.load_sensor_data(days=7, measurement="sensor_data")
```

#### FeatureEngineer
```python
# Time-based features
df = FeatureEngineer.create_time_based_features(df)

# Statistical rolling window features
df = FeatureEngineer.create_statistical_features(df, window_sizes=[5, 10, 30])

# Complete pipeline
df = FeatureEngineer.engineer_features(df)
```

#### Binary Classification
```python
trainer = BinaryClassifierTrainer(random_state=42)
result = trainer.train(df)

# Result contains:
# - model: Trained RandomForest classifier
# - scaler: StandardScaler for feature normalization
# - metrics: {accuracy, precision, recall, f1, roc_auc}
# - feature_names: List of input features
```

#### Multi-class Classification
```python
trainer = MultiClassifierTrainer(random_state=42)
result = trainer.train(df)

# Result contains:
# - model: Trained GradientBoosting classifier
# - scaler: StandardScaler
# - metrics: {accuracy, precision_weighted, recall_weighted, f1_weighted}
# - feature_names: List of input features
```

#### Batch Processor
```python
processor = BatchProcessor(
    influx_url="http://influxdb:8086",
    influx_token="nt-scada-token-secret-key-12345",
    mlflow_uri="http://mlflow:5000"
)

report = processor.run()
# Report structure:
# {
#     "timestamp": "2024-01-15T10:30:00",
#     "total_samples": 1234,
#     "binary_classifier": {
#         "model_id": "binary_classifier_v1.0_20240115_103000",
#         "metrics": {...}
#     },
#     "multiclass_classifier": {
#         "model_id": "multiclass_classifier_v1.0_20240115_103000",
#         "metrics": {...}
#     }
# }
```

### Running Batch Processing

```bash
# Using Docker
docker-compose up batch-analytics

# Manual execution (from nt-scada directory)
python batch/batch_processor_flink.py

# View generated reports
ls -la batch/reports/
cat batch/reports/batch_report_*.json
```

---

## 3. Real-time Stream Processing

**Location**: `stream/stream_processor_production.py`

Production-grade real-time stream processor using Kafka Streams Python with ML model integration.

### Architecture:

```
┌──────────────────────────────────────────────────────────┐
│        Real-time Stream Processing Pipeline              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Kafka Topic: scada.sensors                             │
│        │                                                │
│        ▼                                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Message Parsing & Validation                   │   │
│  └──────────────┬──────────────────────────────────┘   │
│                 │                                       │
│                 ▼                                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Pipeline 1: Binary Anomaly Detection (ML)      │   │
│  │  - Load binary_classifier model from registry   │   │
│  │  - Extract features from sensor data           │   │
│  │  - Predict: is_anomaly (0 or 1)               │   │
│  │  - Fallback to rule-based if model unavailable │   │
│  └──────────────┬──────────────────────────────────┘   │
│                 │                                       │
│                 ▼                                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Pipeline 2: Fine-grained Classification (ML)   │   │
│  │  - Load multiclass_classifier model             │   │
│  │  - Extract features                             │   │
│  │  - Predict: operational_state (7 classes)      │   │
│  │  - Fallback to rule-based if model unavailable │   │
│  └──────────────┬──────────────────────────────────┘   │
│                 │                                       │
│                 ▼                                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Severity & Category Classification             │   │
│  │  - Classify severity: CRITICAL, HIGH, MEDIUM   │   │
│  │  - Classify category: THERMAL, MECHANICAL,     │   │
│  │                       ELECTRICAL                │   │
│  └──────────────┬──────────────────────────────────┘   │
│                 │                                       │
│  ┌──────────────┴──────────────┐                       │
│  │                             │                       │
│  ▼                             ▼                       │
│  scada.processed        scada.anomalies               │
│  (all records)          (anomalies only)              │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### Key Features:

#### Error Handling & Resilience
- Automatic model loading with fallback to rule-based detection
- Graceful degradation if models unavailable
- Message deserialization error handling
- Metrics tracking for monitoring

#### Model Management
- Automatic model discovery from MLflow registry
- Runtime model activation and switching
- Model version selection (latest by default)

#### Performance
- Batch message processing with optimized Kafka configuration
- Metrics collection for monitoring
- Auto-commit for offset management

### Configuration:

```python
processor = KafkaStreamProcessor(
    bootstrap_servers="kafka:29092",
    schema_registry_url=None,  # Optional
    mlflow_uri="http://mlflow:5000",
    group_id="stream-processor-production"
)

processor.initialize()  # Initialize Kafka connections and load models
processor.run()         # Start processing loop
```

### Environmental Variables:

```bash
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
MLFLOW_URI=http://mlflow:5000
```

### Processing Flow:

```python
# Consume from: scada.sensors
sensor_data = {
    "sensor_id": "temperature_001",
    "sensor_type": "temperature",
    "value": 55.3,
    "timestamp": "2024-01-15T10:30:00Z"
}

# Process through ML pipelines
processed = processor.process_message(sensor_data)

# Output to: scada.processed (all) and scada.anomalies (if detected)
# {
#     "sensor_id": "temperature_001",
#     "value": 55.3,
#     "anomaly_detected": False,
#     "operational_state": "OPTIMAL",
#     "severity": "LOW",
#     "category": "THERMAL_PRESSURE",
#     "processing_method": "ML_PRODUCTION",
#     "processed_timestamp": "2024-01-15T10:30:00Z"
# }
```

### Monitoring & Metrics:

```python
# Metrics automatically collected during processing
processor.metrics = {
    "messages_processed": 1000,
    "anomalies_detected": 45,
    "errors": 2,
    "last_update": "2024-01-15T10:30:00Z"
}
```

### Running Stream Processor

```bash
# Using Docker
docker-compose up stream-processor

# Manual execution
python stream/stream_processor_production.py

# Monitor in another terminal
docker-compose logs -f stream-processor
```

---

## 4. Docker Compose Setup

### Updated Services:

```yaml
services:
  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.9.1
    ports:
      - "5000:5000"
    # MLflow UI: http://localhost:5000
    
  batch-analytics:
    # Runs batch processing pipeline
    # Saves models to MLflow registry
    # Generates reports to batch/reports/
    
  stream-processor:
    # Runs real-time stream processor
    # Loads models from MLflow registry
    # Processes scada.sensors topic
```

### Running Complete System:

```bash
# Navigate to nt-scada directory
cd nt-scada

# Start all services
docker-compose up -d

# Wait for services to initialize (2-3 minutes)
# Check service health
docker-compose ps

# View logs
docker-compose logs -f

# Access interfaces:
# - Grafana: http://localhost:3000 (admin/admin)
# - MLflow: http://localhost:5000
# - InfluxDB: http://localhost:8086 (admin/adminpass123)
# - Flink: http://localhost:8081
```

---

## 5. MLflow Model Registry UI

### Accessing MLflow:

1. Open `http://localhost:5000` in your browser
2. View registered models and their versions
3. Compare metrics across model versions
4. Track training runs and parameters

### Model Artifacts:

```
/mlflow/artifacts/
├── binary_classifier_v1.0_20240115_103000/
│   ├── model.pkl
│   ├── manifest.json
│   └── features.json
├── multiclass_classifier_v1.0_20240115_103000/
│   └── ...
```

---

## 6. Troubleshooting

### Model Not Loading in Stream Processor

```python
# Check available models
registry = ModelRegistry()
available = registry.list_models()
print(available)

# Get model metadata
metadata = registry.get_model_metadata("model_id")
```

### Batch Processing Fails

```bash
# Check InfluxDB connection
docker-compose exec influxdb influx ping

# View batch logs
docker-compose logs batch-analytics

# Verify data exists in InfluxDB
docker-compose exec influxdb \
  influx query 'from(bucket:"scada_data") |> range(start: -7d)'
```

### Stream Processor Lag

```bash
# Check Kafka consumer group
docker-compose exec kafka \
  kafka-consumer-groups --bootstrap-server kafka:29092 \
  --group stream-processor-production --describe

# Reset consumer offset if needed
docker-compose exec kafka \
  kafka-consumer-groups --bootstrap-server kafka:29092 \
  --group stream-processor-production \
  --reset-offsets --to-latest --execute
```

---

## 7. Performance Tuning

### Batch Processing:
- Adjust `test_size` in data splitting (default: 0.2)
- Modify `n_estimators` for RandomForest (200 trees)
- Adjust `learning_rate` for GradientBoosting (0.1)
- Increase window sizes for rolling statistics

### Stream Processing:
- Adjust consumer `session.timeout.ms` (30000ms)
- Modify `auto.commit.interval.ms` (5000ms)
- Increase parallelism in processing
- Batch multiple messages per Kafka operation

### MLflow:
- Use persistent database (PostgreSQL) instead of SQLite for production
- Enable artifact S3/GCS backend for scalability
- Configure retention policies

---

## 8. Monitoring & Operations

### Health Checks:

```bash
# Check all services
docker-compose ps

# Check specific service logs
docker-compose logs service-name

# Check resource usage
docker stats

# Monitor in Grafana
# - Open http://localhost:3000
# - Import dashboards
```

### Metrics to Track:

**Batch Processing:**
- Training time
- Model accuracy improvements
- Feature engineering time
- Data loading time

**Stream Processing:**
- Messages processed per second
- Anomalies detected per hour
- Processing latency
- Error rate

---

## 9. Production Deployment Checklist

- [ ] MLflow configured with persistent backend (PostgreSQL)
- [ ] InfluxDB with replication/clustering enabled
- [ ] Kafka with multiple brokers
- [ ] Resource limits set in docker-compose
- [ ] Monitoring and alerting configured
- [ ] Log aggregation setup (ELK/Splunk)
- [ ] Model registry backed up regularly
- [ ] Batch job scheduling configured (cron)
- [ ] Stream processor auto-restart enabled
- [ ] Security: SSL/TLS for communications

---

## 10. API Reference

### ModelRegistry

```python
# Register model
model_id = registry.register_model(
    model, model_name, model_type, version,
    metrics, params, metadata, features
)

# Load model
model, metadata = registry.load_model(model_id)

# List models
models = registry.list_models()

# Get metadata
metadata = registry.get_model_metadata(model_id)
```

### KafkaStreamProcessor

```python
# Initialize and run
processor = KafkaStreamProcessor(...)
processor.initialize()
processor.run()

# Process single message
processed = processor.process_message(sensor_data)

# Produce to Kafka
processor.produce_to_kafka(topic, data, key)

# Access metrics
print(processor.metrics)
```

### BatchProcessor

```python
# Run complete pipeline
processor = BatchProcessor(...)
report = processor.run()

# Report contains model IDs and metrics
print(report)
```

---

## Additional Resources

- MLflow Documentation: https://mlflow.org/docs/latest/
- Apache Flink: https://flink.apache.org/
- Confluent Kafka Python: https://github.com/confluentinc/confluent-kafka-python
- InfluxDB Client: https://github.com/influxdata/influxdb-client-python
