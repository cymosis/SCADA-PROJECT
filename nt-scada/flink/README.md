# Apache Flink Integration for SCADA Real-time Analytics

This directory contains the Apache Flink implementation for real-time processing of SCADA sensor data and attack detection.

## Architecture Overview

### Current SCADA Architecture
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Data      │    │    Kafka    │    │  InfluxDB   │
│  Producers  │───▶│   Broker    │───▶│   Database  │
└─────────────┘    └─────────────┘    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Grafana   │
                    │ Dashboard  │
                    └─────────────┘
```

### With Flink Integration
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Data      │    │    Kafka    │    │   Apache    │    │  InfluxDB   │
│  Producers  │───▶│   Broker    │───▶│   Flink     │───▶│   Database  │
└─────────────┘    └─────────────┘    │ Processing  │    └─────────────┘
                           │         │   Engine    │           │
                           ▼         └─────────────┘           ▼
                    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
                    │   Grafana   │    │   Alert     │    │   ML/AI     │
                    │ Dashboard  │    │   System    │    │   Models    │
                    └─────────────┘    └─────────────┘    └─────────────┘
```

## Components

### 1. Flink Cluster Services
- **flink-jobmanager**: Master node (UI: http://localhost:8081)
- **flink-taskmanager**: Worker nodes (scaled to 2 instances)
- **flink-job-submitter**: Job submission service

### 2. Real-time Processing Jobs
- **scada_realtime_processor.py**: Main processing pipeline
- **influxdb_sink.py**: Custom InfluxDB sink implementation
- **submit_job.py**: Job management and submission script

### 3. Processing Capabilities
- **Real-time Data Transformation**: Calculate derived metrics (pressure averages, variance)
- **Anomaly Detection**: Filter unusual sensor readings
- **Alert Generation**: Create alerts for attacks and anomalies
- **Stream Union**: Combine normal and attack data streams
- **InfluxDB Integration**: Write processed data and alerts to time-series database

## Key Features

### Real-time Analytics
1. **Pressure Analysis**
   - Calculate average pressure across all sensors
   - Monitor pressure variance for anomaly detection
   - Track pressure state changes

2. **Flow Monitoring**
   - Monitor flow rates (FIT sensors)
   - Detect unusual flow patterns
   - Threshold-based alerting

3. **Attack Detection**
   - Process attack data in real-time
   - Generate immediate alerts for security events
   - Correlate with normal data patterns

### Data Processing Pipeline
```
Kafka Topics → Flink Source → Data Processing → Alert Generation → InfluxDB Sinks
     │               │              │                │              │
     ▼               ▼              ▼                ▼              ▼
scada.normal   KafkaSource   SCADADataProcessor AlertGenerator  InfluxDBSink
scada.attacks                 AnomalyFilter                 AlertInfluxDBSink
```

## Installation and Setup

### 1. Start the Flink Cluster
```bash
# Start all services including Flink
docker-compose up -d

# Check Flink services
docker-compose ps | grep flink
```

### 2. Verify Flink Cluster
```bash
# Access Flink UI
open http://localhost:8081

# Check cluster status
curl http://localhost:8081/overview
```

### 3. Submit the Processing Job
```bash
# Automatic submission (via docker-compose)
docker-compose run --rm flink-job-submitter

# Manual submission
docker exec -it flink-jobmanager python3 /opt/flink/jobs/submit_job.py submit
```

### 4. Monitor Job Execution
```bash
# List running jobs
docker exec -it flink-jobmanager python3 /opt/flink/jobs/submit_job.py list

# View job logs
docker logs flink-jobmanager
docker logs flink-taskmanager
```

## Configuration

### Environment Variables
```yaml
INFLUXDB_URL: http://influxdb:8086
INFLUXDB_TOKEN: mytoken
INFLUXDB_ORG: scada
INFLUXDB_BUCKET: processed_data
INFLUXDB_ALERT_BUCKET: alerts
```

### Flink Configuration
- **Parallelism**: 2 (configurable per job)
- **Task Slots**: 4 per TaskManager
- **Checkpointing**: Can be enabled for stateful processing
- **Watermarks**: Disabled (can be enabled for event time processing)

## Data Flow

### Input Data Schema
```json
{
  "t_stamp": "1574649591000000000",
  "P1": "100.5",
  "P2": "98.2",
  "P1_STATE": "Open",
  "FIT101": "45.6",
  "attack_type": "attack_1"
}
```

### Processed Data Schema
```json
{
  "t_stamp": "1574649591000000000",
  "P1": "100.5",
  "P2": "98.2",
  "P1_STATE": "Open",
  "FIT101": "45.6",
  "processed_at": "2023-11-28T18:55:00",
  "avg_pressure": 99.35,
  "pressure_variance": 2.56,
  "data_type": "normal",
  "severity": "low"
}
```

### Alert Schema
```json
{
  "alert_id": "ALERT_000001",
  "timestamp": "1574649591000000000",
  "sensor_data": {...},
  "alert_type": "attack",
  "severity": "high",
  "message": "Attack detected: attack_1"
}
```

## Monitoring and Visualization

### Grafana Dashboards
1. **Real-time Sensor Data**: Live sensor readings and metrics
2. **Alert Dashboard**: Active alerts and severity distribution
3. **Performance Metrics**: Flink job throughput and latency
4. **Anomaly Detection**: Statistical analysis and patterns

### InfluxDB Queries
```flux
// Real-time sensor data
from(bucket: "processed_data")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "scada_data")

// Active alerts
from(bucket: "alerts")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "scada_alerts" and r.active == 1)
```

## Advanced Features

### 1. Complex Event Processing (CEP)
Can be added for pattern detection:
```python
from pyflink.table import TableEnvironment
from pyflink.table import expressions as expr

# Define patterns for complex event detection
```

### 2. Machine Learning Integration
Real-time ML model inference:
```python
# Load trained models
# Apply predictions on streaming data
# Generate ML-based alerts
```

### 3. Stateful Processing
Window-based aggregations:
```python
# 1-minute sliding windows
# 5-minute tumbling windows
# Session windows for pattern detection
```

## Performance Tuning

### Scaling Options
- **Horizontal Scaling**: Add more TaskManagers
- **Parallelism**: Increase job parallelism
- **Resources**: Adjust memory and CPU allocation

### Optimization Tips
1. **Checkpoint Interval**: Balance between performance and fault tolerance
2. **Buffer Timeout**: Adjust for latency vs throughput
3. **Serialization**: Use efficient formats for large payloads

## Troubleshooting

### Common Issues
1. **Kafka Connection**: Ensure Kafka is accessible from Flink containers
2. **InfluxDB Writes**: Check token authentication and bucket permissions
3. **Memory Issues**: Monitor JVM heap usage in TaskManagers
4. **Backpressure**: Check Flink UI for processing bottlenecks

### Debug Commands
```bash
# Check Flink cluster health
curl http://localhost:8081/overview

# View job metrics
curl http://localhost:8081/jobs/{job-id}/metrics

# Check container logs
docker logs flink-jobmanager --tail 100
docker logs flink-taskmanager --tail 100
```

## Future Enhancements

1. **SQL Interface**: Use Flink SQL for easier stream processing
2. **Window Functions**: Time-based aggregations and analytics
3. **ML Pipeline**: Real-time anomaly detection with trained models
4. **Alert Correlation**: Multi-sensor pattern recognition
5. **Dashboard Integration**: Real-time metrics in Grafana

## Support

For issues and questions:
1. Check Flink UI at http://localhost:8081
2. Review container logs
3. Verify Kafka and InfluxDB connectivity
4. Monitor system resources
