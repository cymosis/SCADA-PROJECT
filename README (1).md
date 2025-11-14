# NT-SCADA: New-Tech SCADA System

## 🎯 Project Overview

A comprehensive Supervisory Control and Data Acquisition (SCADA) platform built using open-source technologies for real-time monitoring and anomaly detection in industrial water treatment systems.

**Dataset**: SWaT (Secure Water Treatment) - Contains sensor and actuator data from a water treatment testbed

**Team Size**: 5 members

**Mentor**: Imre Lendak

---

## 🏗️ System Architecture

```
┌─────────────┐      ┌─────────┐      ┌───────────┐      ┌──────────┐      ┌─────────┐
│  SWaT Data  │──▶───│  Kafka  │──▶───│ Telegraf  │──▶───│ InfluxDB │──▶───│ Grafana │
│  (Excel)    │      │ Topics  │      │ Consumer  │      │  (TSDB)  │      │Dashboard│
└─────────────┘      └─────────┘      └───────────┘      └──────────┘      └─────────┘
                          │                                     ▲
                          │                                     │
                          ▼                                     │
                    ┌──────────────┐                           │
                    │   Stream     │───────────────────────────┘
                    │  Processor   │   (Anomaly Detection)
                    │  (ML Models) │
                    └──────────────┘
                          │
                          ▼
                    ┌──────────────┐      ┌────────────┐
                    │   Control    │──▶───│    Mock    │
                    │  Processor   │      │  Actuators │
                    └──────────────┘      └────────────┘
```

---

## 🛠️ Technology Stack

- **Apache Kafka** (v7.7.0) - Real-time data streaming
- **InfluxDB** (v1.8) - Time-series database
- **Telegraf** (v1.28) - Metrics collection
- **Grafana** (v10.2.0) - Visualization
- **Python** (v3.9) - Data processing & ML
- **Docker** - Containerization

---

## 🚀 Quick Start

### 1. Start Infrastructure
```bash
docker-compose up -d
```

### 2. Run Sensor Producer
```bash
cd producers
python sensor_producer.py
```

### 3. Access Grafana
```
URL: http://localhost:3000
Username: admin
Password: admin
```

For detailed instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

## 📁 Project Structure

```
├── producers/         # Data producers
├── stream/           # Stream processors
├── actuators/        # Mock actuators
├── data/swat/        # SWAT dataset
├── models/           # ML models
├── grafana/          # Dashboard configs
├── telegraf/         # Telegraf config
└── docker-compose.yml
```

---

## 📊 Dashboard

**18+ panels** monitoring:
- Stage P1: Raw Water Intake
- Stage P2: Chemical Dosing
- Stage P3: Ultrafiltration
- Stage P4: Reverse Osmosis
- Stage P5: UV Disinfection
- Stage P6: Backwash

**78+ sensors** tracked in real-time

---

## 📚 Documentation

- [Setup Guide](SETUP_GUIDE.md)
- [Grafana Dashboard Guide](GRAFANA_SETUP.md)
- [Changelog](CHANGELOG.md)

---

**Last Updated**: November 2025
