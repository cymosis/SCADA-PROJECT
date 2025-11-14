# NT-SCADA: Open-Source Supervisory Control and Data Acquisition System

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

A comprehensive SCADA system built with open-source technologies for real-time monitoring, anomaly detection, and automated control of industrial sensor networks.

## 🎯 Project Overview

**NT-SCADA** (New-Tech SCADA) is a modern, scalable supervisory control and data acquisition platform designed to:

- **Ingest** large volumes of sensor data in real-time
- **Store** time-series data efficiently  
- **Analyze** sensor readings using machine learning
- **Detect** anomalies and security threats
- **Control** actuators based on intelligent decision-making
- **Visualize** data through interactive dashboards

### Team Members
- Cynthia Mutisya
- Narayan Anshu
- Sheillah Khaluvitsi

**Mentor:** Imre Lendak

**Repository:** https://github.com/cymosis/SCADA-PROJECT

---

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐
│   Sensors   │────▶│  Kafka   │────▶│   Stream     │────▶│ InfluxDB │
│   (SWaT)    │     │          │     │  Processing  │     │          │
└─────────────┘     └──────────┘     └──────────────┘     └──────────┘
                         │                   │                   │
                         │                   ▼                   ▼
                         │            ┌──────────────┐     ┌──────────┐
                         │            │   Anomaly    │────▶│ Grafana  │
                         │            │  Detection   │     │          │
                         │            └──────────────┘     └──────────┘
                         │                   │
                         ▼                   ▼
                    ┌──────────┐      ┌──────────────┐
                    │ Control  │─────▶│  Actuators   │
                    │ Commands │      │   (Mock)     │
                    └──────────┘      └──────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
- **Docker Compose** (v1.27+)
- **Python 3.9+** (for model training)
- **Git**
- **8GB+ RAM** (16GB recommended)
- **20GB+ free disk space**

### One-Command Setup

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows:**
```batch
setup.bat
```

### Manual Setup

See [QUICK-START-GUIDE.md](QUICK-START-GUIDE.md) for detailed step-by-step instructions.

---

## 📦 Technology Stack

### Data Ingestion & Streaming
- **Apache Kafka** - Real-time data streaming
- **Zookeeper** - Kafka cluster coordination

### Data Processing
- **Apache Flink** - Stream and batch processing
- **Python** - Custom stream processors

### Data Storage
- **InfluxDB** - Time-series database
- **Telegraf** - Metrics collection agent

### Machine Learning
- **Scikit-learn** - Classification models
- **Sktime** - Time-series analysis
- **Pandas/NumPy** - Data manipulation

### Visualization & Monitoring
- **Grafana** - Real-time dashboards
- **Kafka UI** - Kafka cluster monitoring

### Orchestration
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration

---

## 📊 Features

### ✅ Implemented

- [x] Real-time sensor data ingestion via Kafka
- [x] Time-series data storage in InfluxDB
- [x] Stream processing for anomaly detection
- [x] Binary classification (Normal vs Attack)
- [x] Control command generation
- [x] Mock actuator simulation
- [x] Grafana dashboards
- [x] Kafka UI for monitoring

### 🔄 In Progress

- [ ] Fine-grained attack classification
- [ ] Daily statistics batch processing
- [ ] Advanced ML models (LSTM, isolation forest)
- [ ] Kubernetes deployment

### 🎯 Planned

- [ ] Real hardware integration
- [ ] Custom Grafana plugins
- [ ] Alert notification system
- [ ] User authentication & authorization
- [ ] API for external integrations

---

## 📁 Project Structure

```
SCADA-PROJECT/
├── docker-compose.yml              # Container orchestration
├── setup.sh / setup.bat            # Automated setup scripts
├── QUICK-START-GUIDE.md            # Beginner-friendly guide
├── README.md                       # This file
│
├── telegraf/
│   └── telegraf.conf              # Telegraf configuration
│
├── stream/
│   └── stream_processor.py        # Real-time anomaly detection
│
├── producers/
│   ├── sensor_producer.py         # Simulates sensor data
│   └── control_producer.py        # Generates control commands
│
├── actuators/
│   └── mock_actuator.py           # Simulates actuator responses
│
├── models/
│   ├── train_binary_model.py     # Binary classification training
│   ├── train_multiclass_model.py # Multi-class classification
│   └── daily_statistics.py        # Batch analytics
│
├── data/
│   └── swat/                      # SWaT dataset location
│       ├── SWaT_Dataset_Normal_v1.csv
│       └── SWaT_Dataset_Attack_v0.csv
│
└── notebooks/
    └── exploratory_analysis.ipynb # Data exploration
```

---

## 🔧 Configuration

### Environment Variables

Key environment variables in `docker-compose.yml`:

```yaml
KAFKA_BOOTSTRAP_SERVERS: kafka:9092
INFLUXDB_URL: http://influxdb:8086
INFLUXDB_DATABASE: scada_data
GRAFANA_ADMIN_PASSWORD: admin
```

### Port Mappings

| Service | Port | Description |
|---------|------|-------------|
| Kafka | 9092 | Kafka broker |
| Zookeeper | 2181 | Zookeeper client |
| Kafka UI | 8080 | Kafka monitoring |
| InfluxDB | 8086 | InfluxDB API |
| Grafana | 3000 | Grafana UI |
| Flink | 8081 | Flink dashboard |

---

## 🎓 Usage

### 1. Start the System

```bash
docker-compose up -d
```

### 2. Verify Services

```bash
docker-compose ps
```

All services should show status as "Up".

### 3. Access Interfaces

- **Kafka UI**: http://localhost:8080
- **Grafana**: http://localhost:3000 (admin/admin)
- **InfluxDB**: http://localhost:8086

### 4. Train ML Models

```bash
cd models
python train_binary_model.py
```

### 5. Start Sensor Data Producer

```bash
cd producers
python sensor_producer.py
```

### 6. Monitor Logs

```bash
# Stream processor
docker-compose logs -f stream-processor

# Control processor
docker-compose logs -f control-processor

# Mock actuator
docker-compose logs -f mock-actuator
```

### 7. Stop the System

```bash
docker-compose down
```

---

## 📊 Data Flow

1. **Sensor Data** → Kafka topic: `sensor-inputs`
2. **Stream Processor** → Consumes from `sensor-inputs`, applies ML models
3. **Processed Data** → Kafka topic: `processed-data` → InfluxDB
4. **Anomalies** → Kafka topic: `anomalies`
5. **Control Logic** → Consumes from `anomalies`, generates commands
6. **Control Commands** → Kafka topic: `control-commands`
7. **Actuators** → Consume from `control-commands`, execute actions
8. **Visualization** → Grafana queries InfluxDB

---

## 🧪 Testing

### Test Kafka Message Flow

```bash
# Produce test message
docker exec -it kafka bash
kafka-console-producer --topic sensor-inputs --bootstrap-server localhost:9092

# Consume messages
kafka-console-consumer --topic sensor-inputs --bootstrap-server localhost:9092 --from-beginning
```

### Test InfluxDB Storage

```bash
docker exec -it influxdb influx
USE scada_data
SHOW MEASUREMENTS
SELECT * FROM sensor_data LIMIT 10
```

### Test Grafana Visualization

1. Login to Grafana
2. Create dashboard
3. Add panel with InfluxDB query
4. Verify real-time data updates

---

## 🐛 Troubleshooting

### Common Issues

**Issue: Kafka won't start**
```bash
docker-compose down
docker-compose up -d zookeeper
sleep 10
docker-compose up -d kafka
```

**Issue: No data in Grafana**
- Check InfluxDB database exists
- Verify Telegraf is running
- Ensure sensor producer is sending data
- Confirm Kafka topics are created

**Issue: Port already in use**
```bash
# Find and kill process using port
lsof -i :9092  # Mac/Linux
netstat -ano | findstr :9092  # Windows
```

See [QUICK-START-GUIDE.md](QUICK-START-GUIDE.md) for more troubleshooting tips.

---

## 📚 Documentation

- [Quick Start Guide](QUICK-START-GUIDE.md) - Step-by-step setup
- [Implementation Guide](NT-SCADA-IMPLEMENTATION-GUIDE.md) - Detailed documentation
- [Architecture Document](OPEN_SOURCE_SCADA.pdf) - System design

---

## 🤝 Contributing

This is an academic project. Team members:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📈 Project Phases

### Phase 1: Setup & Data Simulation ✅
- Local infrastructure setup
- SWaT dataset integration
- Kafka producer for data streaming

### Phase 2: Storage & Visualization ✅
- InfluxDB configuration
- Grafana dashboards
- Real-time data visualization

### Phase 3: Batch Processing ✅
- Binary classification model
- Model training pipeline
- Model evaluation

### Phase 4: Stream Processing 🔄
- Real-time anomaly detection
- Fine-grained classification
- Performance optimization

### Phase 5: Actuator Control ✅
- Control logic implementation
- Mock actuator simulation
- Closed-loop testing

---

## 📖 Dataset

This project uses the **SWaT (Secure Water Treatment)** dataset:

- **Source**: iTrust, SUTD Singapore
- **Website**: https://itrust.sutd.edu.sg/itrust-labs_datasets/
- **Description**: Real-world data from a water treatment testbed
- **Contents**: 
  - Normal operational data
  - Attack scenarios data
  - 51 sensor/actuator data points

**Note**: Dataset not included in repository due to licensing. Contact mentor for access.

---

## 🎯 Learning Objectives

Through this project, team members will learn:

- Real-time data streaming with Kafka
- Time-series data management with InfluxDB
- Machine learning for anomaly detection
- Stream processing architectures
- Container orchestration with Docker
- Industrial SCADA concepts
- Data visualization best practices

---

## 📝 License

This project is created for academic purposes as part of coursework.

---

## 🙏 Acknowledgments

- **Mentor**: Imre Lendak - For guidance and support
- **iTrust Labs**: For providing the SWaT dataset
- **Open Source Community**: For amazing tools and libraries

---

## 📞 Support

For questions or issues:

1. Check [QUICK-START-GUIDE.md](QUICK-START-GUIDE.md)
2. Check [Troubleshooting](#-troubleshooting) section
3. Review Docker logs: `docker-compose logs <service>`
4. Contact team members or mentor

---

## 🔗 Links

- **GitHub**: https://github.com/cymosis/SCADA-PROJECT
- **Kafka Documentation**: https://kafka.apache.org/documentation/
- **InfluxDB Documentation**: https://docs.influxdata.com/
- **Grafana Documentation**: https://grafana.com/docs/
- **Docker Documentation**: https://docs.docker.com/

---

**Built with ❤️ by Team NT-SCADA**

*Last Updated: November 2025*
