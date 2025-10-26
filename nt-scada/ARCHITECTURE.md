# NT-SCADA System Architecture

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         NT-SCADA SYSTEM                              │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      DATA GENERATION LAYER                           │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐              ┌──────────────────┐            │
│  │ Sensor Producer  │              │Actuator Producer │            │
│  │  - Temperature   │              │  - Valves        │            │
│  │  - Pressure      │              │  - Pumps         │            │
│  │  - Flow Rate     │              │  - Breakers      │            │
│  │  - Vibration     │              │  - Motors        │            │
│  │  - Voltage       │              │  - Dampers       │            │
│  │  - Current       │              │  - Relays        │            │
│  └────────┬─────────┘              └────────┬─────────┘            │
└───────────┼──────────────────────────────────┼──────────────────────┘
            │                                  │
            ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    INGESTION LAYER (KAFKA)                           │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Apache Kafka Broker                        │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │  │
│  │  │ scada.sensors  │  │scada.actuators │  │scada.processed │ │  │
│  │  └────────────────┘  └────────────────┘  └────────────────┘ │  │
│  │  ┌────────────────┐                                          │  │
│  │  │scada.anomalies │                                          │  │
│  │  └────────────────┘                                          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────┐                                              │
│  │    Zookeeper     │ (Kafka Coordination)                        │
│  └──────────────────┘                                              │
└───────────────────────┬──────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   STREAM PROCESSING LAYER                            │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Stream Processor (Python/Flink)                  │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │ Pipeline 1: Binary Anomaly Detection                   │  │  │
│  │  │  - Rule-based: value < 20 or > 80                      │  │  │
│  │  │  - Output: Normal (0) vs Anomaly (1)                   │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │ Pipeline 2: Fine-Grained Classification                │  │  │
│  │  │  - 7 Classes: CRITICALLY_LOW, LOW, BELOW_OPTIMAL,      │  │  │
│  │  │    OPTIMAL, ABOVE_OPTIMAL, HIGH, CRITICALLY_HIGH       │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │ Additional Classifications:                             │  │  │
│  │  │  - Severity: CRITICAL, HIGH, MEDIUM, LOW               │  │  │
│  │  │  - Category: THERMAL_PRESSURE, MECHANICAL, ELECTRICAL  │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐                        │
│  │ Flink JobManager │  │ Flink TaskManager│ (Optional)             │
│  └──────────────────┘  └──────────────────┘                        │
└───────────────────────┬──────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                                   │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                  InfluxDB Consumer                            │  │
│  │  - Consumes from: scada.processed, scada.actuators           │  │
│  │  - Writes to: InfluxDB time-series database                  │  │
│  └────────────────────────┬─────────────────────────────────────┘  │
│                            ▼                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      InfluxDB v2                              │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │ Bucket: scada_data                                     │  │  │
│  │  │  - Measurement: sensor_data                            │  │  │
│  │  │    * Tags: sensor_id, sensor_type, location, status,  │  │  │
│  │  │            severity, category, operational_state       │  │  │
│  │  │    * Fields: value, anomaly                            │  │  │
│  │  │  - Measurement: actuator_data                          │  │  │
│  │  │    * Tags: actuator_id, actuator_type, location,      │  │  │
│  │  │            state, command_type, health                 │  │  │
│  │  │    * Fields: analog_output, digital_output             │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└───────────────┬───────────────────────────────┬──────────────────────┘
                │                               │
                ▼                               ▼
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│    VISUALIZATION LAYER          │  │    BATCH ANALYTICS LAYER        │
├─────────────────────────────────┤  ├─────────────────────────────────┤
│  ┌───────────────────────────┐  │  │  ┌───────────────────────────┐  │
│  │       Grafana v10         │  │  │  │   Batch Analytics Job     │  │
│  │  ┌─────────────────────┐  │  │  │  │  ┌─────────────────────┐  │  │
│  │  │ NT-SCADA Dashboard  │  │  │  │  │  │ Task 1: Binary      │  │  │
│  │  │  - Real-time plots  │  │  │  │  │  │ Classification      │  │  │
│  │  │  - Anomaly gauges   │  │  │  │  │  │  - Random Forest    │  │  │
│  │  │  - Tabular views    │  │  │  │  │  └─────────────────────┘  │  │
│  │  │  - Analog I/O plots │  │  │  │  │  ┌─────────────────────┐  │  │
│  │  │  - Distribution     │  │  │  │  │  │ Task 2: Multi-class │  │  │
│  │  │    charts           │  │  │  │  │  │ Classification      │  │  │
│  │  │  - Hourly trends    │  │  │  │  │  │  - Gradient Boost   │  │  │
│  │  └─────────────────────┘  │  │  │  │  └─────────────────────┘  │  │
│  │                            │  │  │  │  ┌─────────────────────┐  │  │
│  │  ┌─────────────────────┐  │  │  │  │  │ Task 3: Daily       │  │  │
│  │  │ InfluxDB Datasource │  │  │  │  │  │ Statistics          │  │  │
│  │  │  - Flux queries     │  │  │  │  │  │  - Aggregations     │  │  │
│  │  │  - Auto-refresh     │  │  │  │  │  │  - JSON reports     │  │  │
│  │  └─────────────────────┘  │  │  │  │  └─────────────────────┘  │  │
│  └───────────────────────────┘  │  │  │                            │  │
│                                  │  │  │  Output:                   │  │
│  Access: http://localhost:3000  │  │  │  - models/*.pkl            │  │
│  Credentials: admin/admin       │  │  │  - reports/*.json          │  │
│                                  │  │  └───────────────────────────┘  │
└─────────────────────────────────┘  └─────────────────────────────────┘
```

## 📊 Data Flow Diagram

```
1. DATA GENERATION
   ├─ Sensor Producer (30 sensors, 6 types)
   │  └─ Generates values every 2 seconds
   │     └─ ~5% anomalies injected
   └─ Actuator Producer (24 actuators, 6 types)
      └─ Generates states every 3 seconds
         └─ Analog & digital outputs

2. INGESTION
   ├─ Kafka Topic: scada.sensors
   │  └─ Partitioned by sensor_id
   └─ Kafka Topic: scada.actuators
      └─ Partitioned by actuator_id

3. STREAM PROCESSING
   ├─ Consume from scada.sensors
   ├─ Apply anomaly detection rules
   ├─ Classify operational state
   ├─ Add metadata (severity, category)
   ├─ Publish to scada.processed
   └─ Filter & publish anomalies to scada.anomalies

4. STORAGE
   ├─ Consume from scada.processed
   ├─ Consume from scada.actuators
   └─ Write to InfluxDB
      ├─ sensor_data measurement
      └─ actuator_data measurement

5. VISUALIZATION
   ├─ Grafana queries InfluxDB
   ├─ Real-time dashboard updates
   └─ Multiple visualization types

6. BATCH ANALYTICS
   ├─ Query historical data from InfluxDB
   ├─ Feature engineering
   ├─ Train ML models
   ├─ Generate reports
   └─ Save models & reports
```

## 🔄 Component Interactions

### Producer → Kafka
```
Sensor/Actuator Producer
    ↓ (JSON messages)
Kafka Topic
    ↓ (partitioned by ID)
Consumer Groups
```

### Kafka → Stream Processor
```
Kafka Consumer (scada.sensors)
    ↓ (deserialize JSON)
Anomaly Detector
    ↓ (add anomaly flag)
Fine-Grained Classifier
    ↓ (add operational_state)
Kafka Producer (scada.processed, scada.anomalies)
```

### Kafka → InfluxDB
```
Kafka Consumer (scada.processed, scada.actuators)
    ↓ (deserialize JSON)
InfluxDB Point Builder
    ↓ (convert to Line Protocol)
InfluxDB Write API
    ↓ (batch writes)
InfluxDB Storage
```

### InfluxDB → Grafana
```
Grafana Dashboard
    ↓ (Flux queries)
InfluxDB Query API
    ↓ (time-series data)
Grafana Visualization
    ↓ (auto-refresh every 5s)
User Browser
```

### InfluxDB → Batch Analytics
```
Batch Analytics Job
    ↓ (Flux queries)
InfluxDB Query API
    ↓ (historical data)
Feature Engineering
    ↓ (rolling stats, encoding)
ML Model Training
    ↓ (scikit-learn)
Model Persistence
    ↓ (pickle files)
Report Generation
    ↓ (JSON files)
File System
```

## 🗂️ Data Models

### Sensor Data Message
```json
{
  "sensor_id": "temperature_001",
  "sensor_type": "temperature",
  "value": 45.67,
  "unit": "°C",
  "status": "NORMAL",
  "anomaly": false,
  "timestamp": "2024-10-23T19:23:45.123456Z",
  "location": "Zone-1",
  "metadata": {
    "firmware_version": "2.1.0",
    "calibration_date": "2024-01-15"
  },
  "anomaly_detected": false,
  "severity": "LOW",
  "category": "THERMAL_PRESSURE",
  "operational_state": "OPTIMAL",
  "processed_timestamp": "2024-10-23T19:23:45.234567Z"
}
```

### Actuator Data Message
```json
{
  "actuator_id": "valve_001",
  "actuator_type": "valve",
  "state": "OPEN",
  "command_type": "FEEDBACK",
  "analog_output": 85.5,
  "digital_output": null,
  "health": "HEALTHY",
  "timestamp": "2024-10-23T19:23:45.123456Z",
  "location": "Zone-2",
  "metadata": {
    "last_maintenance": "2024-02-10",
    "cycle_count": 12345
  }
}
```

### InfluxDB Schema

#### sensor_data Measurement
```
Tags:
  - sensor_id
  - sensor_type
  - location
  - status
  - severity
  - category
  - operational_state

Fields:
  - value (float)
  - anomaly (integer: 0 or 1)

Timestamp: nanosecond precision
```

#### actuator_data Measurement
```
Tags:
  - actuator_id
  - actuator_type
  - location
  - state
  - command_type
  - health

Fields:
  - analog_output (float, nullable)
  - digital_output (integer, nullable)

Timestamp: nanosecond precision
```

## 🔐 Security Considerations

1. **InfluxDB**: Token-based authentication
2. **Grafana**: Username/password authentication
3. **Kafka**: No authentication (development mode)
4. **Network**: Internal Docker network isolation

**Production Recommendations:**
- Enable Kafka SASL/SSL
- Use secrets management (Docker Secrets, Vault)
- Implement RBAC in Grafana
- Enable TLS for all services
- Use strong passwords
- Network segmentation

## 📈 Scalability

### Horizontal Scaling
- **Kafka**: Add more brokers and partitions
- **Flink**: Increase TaskManager replicas
- **InfluxDB**: Use InfluxDB Enterprise/Cloud
- **Producers**: Run multiple instances with different sensor IDs

### Vertical Scaling
- Increase Docker container resources
- Optimize batch sizes
- Tune Kafka retention policies
- Configure InfluxDB shard groups

## 🎯 Performance Metrics

| Component | Throughput | Latency |
|-----------|------------|---------|
| Sensor Producer | ~15 msg/sec | N/A |
| Actuator Producer | ~8 msg/sec | N/A |
| Stream Processor | ~100 msg/sec | <100ms |
| InfluxDB Consumer | ~100 msg/sec | <50ms |
| Grafana Queries | ~10 queries/sec | <500ms |

## 🔧 Configuration Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Service orchestration |
| `.env` | Environment variables |
| `grafana-datasources.yml` | Grafana InfluxDB connection |
| `dashboards/dashboard.yml` | Dashboard provisioning |
| `dashboards/grafana_dashboard.json` | Dashboard definition |
| `*/requirements.txt` | Python dependencies |
| `*/Dockerfile` | Container images |

## 🚀 Deployment Options

### Development (Current)
- Docker Compose on local machine
- Single-node deployment
- Persistent volumes for data

### Production (Future)
- Kubernetes cluster
- Multi-node deployment
- Cloud-native storage (S3, EBS)
- Auto-scaling
- High availability
- Monitoring & alerting

---

**NT-SCADA Architecture** - Designed for scalability, reliability, and real-time performance 🏭⚡
