# NT-SCADA (New-Tech SCADA)

A complete open-source Supervisory Control and Data Acquisition (SCADA) system built with modern big data technologies for real-time monitoring, stream processing, and analytics of industrial sensor and actuator data.

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐
│   Sensors   │────▶│    Kafka    │
│  Actuators  │     │  (Ingest)   │
└─────────────┘     └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Stream    │
                    │  Processor  │
                    │  (Anomaly   │
                    │ Detection)  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  InfluxDB   │
                    │  (Storage)  │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
       ┌──────▼──────┐          ┌──────▼──────┐
       │   Grafana   │          │    Batch    │
       │ (Visualize) │          │  Analytics  │
       └─────────────┘          │  (ML Models)│
                                └─────────────┘
```

## 🚀 Features

### Real-time Data Ingestion
- **Kafka Topics**: `scada.sensors`, `scada.actuators`
- Simulates industrial sensor data (temperature, pressure, flow rate, vibration, voltage, current)
- Simulates actuator commands (valves, pumps, breakers, motors, dampers, relays)
- Configurable anomaly injection for testing

### Stream Processing
- **Pipeline 1**: Binary anomaly detection (Normal vs Anomaly)
  - Rule-based: value < 20 or > 80 triggers anomaly
- **Pipeline 2**: Fine-grained classification (7 operational states)
  - CRITICALLY_LOW, LOW, BELOW_OPTIMAL, OPTIMAL, ABOVE_OPTIMAL, HIGH, CRITICALLY_HIGH
- Real-time severity classification (CRITICAL, HIGH, MEDIUM, LOW)
- Category classification (THERMAL_PRESSURE, MECHANICAL, ELECTRICAL)

### Time-Series Storage
- **InfluxDB** for high-performance time-series data storage
- Separate measurements for sensor and actuator data
- Tagged data for efficient querying and aggregation
- Fields: sensor_id, value, anomaly, timestamp, operational_state, etc.

### Batch Analytics
- **Task 1**: Binary classification model (Random Forest)
- **Task 2**: Multi-class classification model (Gradient Boosting)
- **Task 3**: Daily statistics and reporting
- Feature engineering with rolling statistics
- Model persistence (model.pkl files)
- JSON reports with comprehensive metrics

### Visualization
- **Grafana Dashboards** with multiple panels:
  - Real-time sensor value plots
  - Anomaly detection gauges
  - Tabular views for sensors and actuators
  - Analog input/output time-series plots
  - Operational state distribution (pie charts)
  - Hourly anomaly trends

## 📁 Project Structure

```
nt-scada/
├── docker-compose.yml          # Main orchestration file
├── producers/
│   ├── sensor_producer.py      # Sensor data simulator
│   ├── actuator_producer.py    # Actuator data simulator
│   ├── Dockerfile
│   └── requirements.txt
├── stream/
│   ├── flink_job.py           # Flink stream processing (optional)
│   ├── stream_processor.py    # Python stream processor
│   ├── Dockerfile
│   └── requirements.txt
├── storage/
│   ├── to_influx.py           # Kafka to InfluxDB consumer
│   ├── Dockerfile
│   └── requirements.txt
├── batch/
│   ├── train_model.py         # ML model training & analytics
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── models/                # Saved ML models
│   └── reports/               # Daily reports
├── dashboards/
│   └── grafana_dashboard.json # Grafana dashboard config
├── grafana-datasources.yml    # Grafana InfluxDB connection
├── requirements.txt           # Global Python dependencies
└── README.md                  # This file
```

## 🔧 Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0+
- At least 8GB RAM available for Docker
- Ports available: 9092 (Kafka), 8081 (Flink), 3000 (Grafana), 8086 (InfluxDB)

## 🚀 Quick Start

### 1. Clone or Navigate to Project Directory

```bash
cd nt-scada
```

### 2. Start All Services

```bash
docker-compose up -d
```

This will start:
- Zookeeper (Kafka coordination)
- Kafka (message broker)
- InfluxDB (time-series database)
- Grafana (visualization)
- Flink JobManager & TaskManager (stream processing framework)
- Sensor Producer (data generator)
- Actuator Producer (data generator)
- Stream Processor (anomaly detection)
- InfluxDB Consumer (data storage)
- Batch Analytics (ML training - runs once)

### 3. Verify Services

Check that all containers are running:

```bash
docker-compose ps
```

Expected output: All services should show "Up" status.

### 4. Access Web Interfaces

- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`
  - Navigate to Dashboards → NT-SCADA Dashboard

- **Flink Dashboard**: http://localhost:8081
  - Monitor stream processing jobs

- **InfluxDB**: http://localhost:8086
  - Username: `admin`
  - Password: `adminpass123`
  - Organization: `nt-scada`
  - Bucket: `scada_data`

- **Kafka**: localhost:9092 (no web UI, use CLI tools)

## 📊 Using the System

### View Real-time Data

1. Open Grafana at http://localhost:3000
2. Login with admin/admin
3. Import the dashboard from `dashboards/grafana_dashboard.json` or it should be auto-provisioned
4. View real-time sensor values, anomalies, and actuator states

### Monitor Stream Processing

```bash
# View stream processor logs
docker-compose logs -f stream-processor

# View InfluxDB consumer logs
docker-compose logs -f influx-consumer
```

### Run Batch Analytics

The batch analytics runs once on startup. To run it again:

```bash
docker-compose restart batch-analytics

# View logs
docker-compose logs -f batch-analytics
```

### Check Generated Models

```bash
# List saved models
docker-compose exec batch-analytics ls -la /app/models

# View daily reports
docker-compose exec batch-analytics ls -la /app/reports
```

### Query Data Manually

Using InfluxDB CLI:

```bash
docker-compose exec influxdb influx query \
  --org nt-scada \
  --token nt-scada-token-secret-key-12345 \
  'from(bucket:"scada_data") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "sensor_data") |> limit(n: 10)'
```

## 🔍 Data Flow

1. **Data Generation**: Producers simulate sensor/actuator data every 2-3 seconds
2. **Ingestion**: Data sent to Kafka topics (`scada.sensors`, `scada.actuators`)
3. **Stream Processing**: 
   - Stream processor consumes from `scada.sensors`
   - Applies anomaly detection rules
   - Performs multi-class classification
   - Publishes to `scada.processed` and `scada.anomalies`
4. **Storage**: InfluxDB consumer writes processed data to time-series database
5. **Visualization**: Grafana queries InfluxDB and displays real-time dashboards
6. **Batch Analytics**: Periodically trains ML models and generates reports

## 🧪 Testing Anomaly Detection

The system automatically generates anomalies (~5% of readings). To verify:

1. Check Grafana "Anomalies Detected" gauge
2. View the "Sensor Data - Tabular View" panel (anomaly column highlighted)
3. Check stream processor logs for anomaly counts
4. Query anomalies topic:

```bash
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic scada.anomalies \
  --from-beginning \
  --max-messages 10
```

## 📈 Machine Learning Models

### Binary Classification Model
- **Algorithm**: Random Forest
- **Purpose**: Detect anomalies (Normal vs Anomaly)
- **Features**: Value, time features, rolling statistics, sensor metadata
- **Output**: `models/binary_classifier.pkl`, `models/binary_scaler.pkl`

### Multi-class Classification Model
- **Algorithm**: Gradient Boosting
- **Purpose**: Classify operational states (7 classes)
- **Features**: Same as binary model
- **Output**: `models/multiclass_classifier.pkl`, `models/multiclass_scaler.pkl`, `models/class_names.pkl`

### Daily Statistics
- Total records, anomaly percentage
- Sensor-level aggregations
- Daily summaries (mean, min, max, std)
- Top anomalous sensors
- **Output**: `reports/daily_report_YYYYMMDD_HHMMSS.json`

## 🛠️ Configuration

### Environment Variables

Edit `docker-compose.yml` to customize:

- `KAFKA_BOOTSTRAP_SERVERS`: Kafka connection string
- `INFLUXDB_URL`: InfluxDB endpoint
- `INFLUXDB_TOKEN`: Authentication token
- `INFLUXDB_ORG`: Organization name
- `INFLUXDB_BUCKET`: Bucket name

### Adjust Data Generation Rate

Edit `producers/sensor_producer.py`:

```python
time.sleep(2)  # Change sleep duration (seconds)
```

### Modify Anomaly Detection Rules

Edit `stream/stream_processor.py`:

```python
def detect_anomaly(sensor_value):
    return sensor_value < 20 or sensor_value > 80  # Adjust thresholds
```

## 🐛 Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose logs

# Restart specific service
docker-compose restart <service-name>
```

### Kafka Connection Issues

```bash
# Verify Kafka is healthy
docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092
```

### InfluxDB Connection Issues

```bash
# Check InfluxDB health
docker-compose exec influxdb influx ping
```

### No Data in Grafana

1. Wait 2-3 minutes for data to accumulate
2. Check InfluxDB has data:
   ```bash
   docker-compose logs influx-consumer
   ```
3. Verify Grafana datasource is configured correctly
4. Refresh dashboard

### Reset Everything

```bash
# Stop and remove all containers, networks, volumes
docker-compose down -v

# Restart
docker-compose up -d
```

## 📚 Technologies Used

- **Apache Kafka**: Distributed streaming platform for real-time data ingestion
- **Apache Flink**: Stream processing framework (optional, Python alternative included)
- **InfluxDB**: High-performance time-series database
- **Grafana**: Visualization and monitoring platform
- **Python**: Data generation, stream processing, ML training
- **scikit-learn**: Machine learning library for classification models
- **Docker & Docker Compose**: Containerization and orchestration

## 🎯 Use Cases

- Industrial IoT monitoring
- Predictive maintenance
- Real-time anomaly detection
- Process optimization
- Energy management
- Smart manufacturing
- Critical infrastructure monitoring

## 📝 Future Enhancements

- [ ] Kubernetes deployment manifests
- [ ] Integration with SWaT dataset
- [ ] Advanced ML models (LSTM, Transformer)
- [ ] Alerting system (email, SMS, Slack)
- [ ] Historical data replay
- [ ] Multi-tenancy support
- [ ] REST API for external integrations
- [ ] Mobile dashboard app
- [ ] Network flow analysis
- [ ] Cybersecurity threat detection

## 👥 Team & Mentorship

- **Team Size**: 5 members
- **Mentor**: Imre Lendak
- **Dataset**: SWaT and other SCADA datasets

## 📄 License

This project is open-source and available for educational and research purposes.

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📧 Support

For issues, questions, or suggestions, please open an issue on the project repository.

---

**NT-SCADA** - Modern SCADA for the Digital Age 🏭⚡
