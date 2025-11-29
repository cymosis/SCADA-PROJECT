# Unified SCADA System (NT-SCADA)

![SCADA System](https://img.shields.io/badge/System-SCADA-blue)
![Status](https://img.shields.io/badge/Status-Active-success)
![Kubernetes](https://img.shields.io/badge/Kubernetes-K8s-326CE5?logo=kubernetes&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![InfluxDB](https://img.shields.io/badge/InfluxDB-2.7-22ADF6?logo=influxdb&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-10.2-F46800?logo=grafana&logoColor=white)
![Kafka](https://img.shields.io/badge/Kafka-7.7-231F20?logo=apachekafka&logoColor=white)
![Flink](https://img.shields.io/badge/Flink-1.18-E6526F?logo=apacheflink&logoColor=white)

**NT-SCADA** (New-Tech SCADA) is a complete, open-source Supervisory Control and Data Acquisition platform built with modern big data technologies. It is designed to ingest, store, analyze, and visualize large volumes of analog and digital inputs from industrial sensors, and control actuators based on real-time analysis.

---

## Team Members

1.  **Cynthia Mutisya**
2.  **Narayan Anshu**
3.  **Sheillah Khaluvitsi**

**GitHub Repo**: [https://github.com/cymosis/SCADA-PROJECT](https://github.com/cymosis/SCADA-PROJECT)

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Key Technologies](#key-technologies)
- [Features](#features)
- [Work Plan & Phases](#work-plan--phases)
- [Getting Started](#getting-started)
- [Service Dashboard](#service-dashboard)
- [Project Structure](#project-structure)
- [Additional Documentation](#additional-documentation)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

The aim of the project is to develop a supervisory control and data acquisition platform based on open-source technologies. We implement ingesting, storing, analyzing, and visualizing large volumes of analog and digital inputs collected from sensors. We also add support for handling analog and digital outputs sent from the SCADA to actuators (e.g., breakers, valves, and other equipment which turns electric signals into physical actions).

### Use Cases

- **Industrial IoT Monitoring**: Real-time monitoring of manufacturing processes and equipment
- **Predictive Maintenance**: Detect equipment failures before they occur using ML models
- **Critical Infrastructure**: Monitor water treatment plants, power grids, and other essential systems
- **Digital Twin**: Create virtual replicas of physical industrial systems
- **Research & Education**: Learn about SCADA systems, stream processing, and anomaly detection
- **Cybersecurity**: Test and validate security measures for industrial control systems

---

## System Architecture

The proposed architecture leverages Kubernetes for orchestration and a robust pipeline for data processing.

```mermaid
graph TD
    subgraph "Data Sources"
        S[Industrial Sensors] -->|Real-time Data| K[Apache Kafka]
        A[Actuators] -->|Status| K
        D[SWaT & Other Datasets] -->|Simulated Stream| K
    end

    subgraph "Data Ingestion & Messaging"
        K[Apache Kafka]
    end

    subgraph "Stream Processing"
        K -->|Consume| F_Stream[Apache Flink Stream]
        F_Stream -->|Anomaly Detection| F_Stream
        F_Stream -->|Fine-grained Classification| F_Stream
        F_Stream -->|Processed Data| K
    end

    subgraph "Batch Processing"
        DB[(InfluxDB)] -->|Historical Data| F_Batch[Apache Flink Batch]
        F_Batch -->|sktime Analysis| F_Batch
        F_Batch -->|Train ML Models| M[Model Registry]
    end

    subgraph "Storage"
        K -->|Persist| DB[(InfluxDB)]
    end

    subgraph "Visualization & Control"
        DB -->|Query| G[Grafana]
        G -->|Control Commands| K
        K -->|Execute| A[Actuators]
    end

3.  **Data Processing**:
    *   **Apache Flink**: This will be the primary engine for both stream processing and batch processing.
        *   **Stream Processing**:
            *   Flink will consume real-time sensor data directly from Kafka topics. It will apply the pre-trained machine learning models (Pipeline 1: binary classification for anomaly detection, Pipeline 2: fine-grained classification) to the incoming data stream. This will enable real time anomaly detection, providing alerts or insights.
        *   **Batch Processing**:
            *   Flink will process historical data, likely pulled from InfluxDB or directly from specific Kafka topics that persist data for longer durations.
            *   **Batch 1 & 2 (ML Model Training)**: Flink can be used to prepare (extract features, clean) the historical data before feeding it to sktime (or another library) for training binary and fine-grained classification models.
            *   **Batch 3 (Daily Statistics)**: Flink can compute daily aggregates, averages, min/max values, and other statistics from stored data, which will then be pushed to InfluxDB or directly to visualization.

4.  **Time-Series Database**:
    *   **InfluxDB**:
        *   This will be used for storing all raw and processed sensor/actuator data for historical analysis, dashboarding, and serving as a data source for batch processing (e.g., retraining models). It's crucial for visualization and understanding trends over time.

5.  **Container Orchestration**:
    *   **Kubernetes (K8s)**:
        *   Kubernetes is a platform for automating deployment, scaling, and management of containerized applications. All our components (Kafka brokers, Flink jobs, InfluxDB, Grafana) will run as containers on Kubernetes. Kubernetes provides scalability, high availability, and simplified management for your distributed SCADA system. It can also be scaled up easily and can also ensure components restart automatically if they fail.

6.  **Data Visualization & Control**:
    *   **Grafana**:
        *   This will be our primary user interface for visualizing all sensor and actuator data (tabular, plots, dashboards) as it connects easily to InfluxDB and Kafka. It will display the results of our real-time anomaly detection and fine-grained classification. It can also be used to send *control commands* back to actuators (via a custom plugin or integration with Kafka).

7.  **Actuators (Output Control)**:
    *   **Industrial Equipment (Simulated)**: In a real SCADA system, these are physical devices but, in our project, we will likely simulate their behavior. Typically, Grafana via user interaction will send a control command to a Kafka topic. A Flink job will consume this command from Kafka and will then interface with the physical actuator but in our case, the actuator service will simply log the command or update a simulated state.

---

## Key Technologies

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Apache Kafka** | 7.7.0 | Distributed streaming platform for real-time data ingestion |
| **Apache Flink** | 1.18.0 | Stream and batch processing engine |
| **InfluxDB** | 2.7 | Time-series database for sensor/actuator data storage |
| **Grafana** | 10.2.0 | Visualization and monitoring platform |
| **Kubernetes** | Latest | Container orchestration and deployment |
| **Python** | 3.9+ | Data processing, ML training, and producers |
| **scikit-learn** | Latest | Machine learning library for classification models |
| **sktime** | Latest | Time-series analysis and forecasting |
| **Docker** | Latest | Containerization for all services |

---

## Features

### Real-time Data Processing
- **High-throughput Ingestion**: Kafka handles thousands of sensor readings per second
- **Stream Processing**: Real-time anomaly detection using Apache Flink
- **Binary Classification**: Detects normal vs. anomalous sensor behavior
- **Fine-grained Classification**: Classifies sensor states into 7 categories (CRITICALLY_LOW, LOW, BELOW_OPTIMAL, OPTIMAL, ABOVE_OPTIMAL, HIGH, CRITICALLY_HIGH)

### Machine Learning & Analytics
- **Automated Model Training**: Batch jobs train Random Forest and Gradient Boosting models
- **Feature Engineering**: Extracts time-series features using `sktime`
- **Daily Statistics**: Computes aggregates, averages, and trends
- **Model Registry**: Stores and versions trained ML models

### Data Visualization
- **Interactive Dashboards**: Pre-configured Grafana dashboards for real-time monitoring
- **Historical Analysis**: Query and visualize trends over time
- **Anomaly Alerts**: Visual indicators for detected anomalies
- **Tabular Views**: Comprehensive sensor and actuator data tables

### Actuator Control
- **Command Publishing**: Send control commands from Grafana to actuators
- **Simulated Actuators**: Mock industrial equipment for testing
- **Closed-loop Control**: Complete feedback loop from sensors to actuators
- **Command Logging**: Track all control commands for audit purposes

### Scalability & Reliability
- **Kubernetes Orchestration**: Auto-scaling and self-healing infrastructure
- **High Availability**: Redundant components and automatic failover
- **Distributed Processing**: Workload distributed across multiple nodes
- **Data Persistence**: Reliable storage with InfluxDB time-series database

---

## Work Plan & Phases

We plan to implement the project in phases as described below. We have not defined roles for each team member yet since it will be more of teamwork.

*   **Phase 1: Setup & Data Simulation (Sheillah, Cynthia & Narayan)**
    *   Set up a local Kubernetes cluster.
    *   Use Helm charts to deploy Kafka, InfluxDB, and Grafana into Kubernetes.
    *   Develop the **SWaT Kafka Producer** to stream the dataset into our sensor-inputs topic.

*   **Phase 2: Storage & Visualization (Sheillah, Cynthia & Narayan)**
    *   Configure InfluxDB to store the incoming data.
    *   Connect Grafana to InfluxDB and build the first dashboards (Analog Input Plots, Tabular Data).

*   **Phase 3: Batch Processing & Model Training (Sheillah, Cynthia & Narayan)**
    *   Develop the **Apache Flink** batch jobs.
    *   Use `sktime` and `scikit-learn` within these jobs to train our two models.
    *   Store the trained models in a model registry.

*   **Phase 4: Real-time Stream Processing (Sheillah, Cynthia & Narayan)**
    *   Develop the **Kafka Streams** applications for anomaly detection (Pipeline 1) and fine-grained classification (Pipeline 2). They will consume the live sensor inputs, use the models from Phase 3, and produce results to new topics.

*   **Phase 5: Actuator Control & Closing the Loop (Sheillah, Cynthia & Narayan)**
    *   Develop the **Control Logic** service that listens for anomalies and publishes commands.
    *   Develop a "mock actuator" consumer that subscribes to the control-commands topic and simply logs what command it *would have* executed. This proves the control loop works without needing a physical valve.

---

## Getting Started (Local Docker Version)

*Note: While the target architecture uses Kubernetes, this repository currently includes a Docker Compose setup for easy local development.*

### Prerequisites
*   **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
*   **Docker Compose** v2.0+
*   Minimum **8GB RAM** allocated to Docker

### Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/cymosis/SCADA-PROJECT.git
    cd SCADA-PROJECT
    ```

2.  **Start the System**
    ```bash
    docker-compose up -d
    ```
    *This will pull necessary images, build custom components, and start all services.*

3.  **Verify Deployment**
    ```bash
    docker-compose ps
    ```

---

## Service Dashboard

Access the various components of the system using the following credentials:

| Service | URL | Username | Password | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Grafana** | [http://localhost:3000](http://localhost:3000) | `admin` | `admin` | Main visualization dashboard |
| **InfluxDB** | [http://localhost:8086](http://localhost:8086) | `admin` | `adminpass123` | Time-series database UI |
| **Kafka UI** | [http://localhost:8080](http://localhost:8080) | - | - | Kafka cluster management |
| **Flink Dashboard** | [http://localhost:8081](http://localhost:8081) | - | - | Stream processing jobs |

> **Note**: InfluxDB Organization is `nt-scada` and Bucket is `scada_data`.

---

## Project Structure

```text
SCADA-PROJECT/
├── docker-compose.yml          # Main orchestration file
├── nt-scada/                   # Core application code
│   ├── producers/              # Data generators (Sensors/Actuators)
│   ├── stream/                 # Stream processing logic (Anomaly Detection)
│   ├── storage/                # InfluxDB consumer
│   ├── batch/                  # ML models and analytics
│   ├── dashboards/             # Grafana provisioning
│   └── README.md               # Detailed component documentation
├── Swat Data/                  # Reference datasets
└── Documentation/              # Additional guides and docs
```

---

## Troubleshooting

### Common Issues

**1. Services keep restarting**
*   Check logs: `docker-compose logs <service-name>`
*   Ensure you have enough memory allocated to Docker (8GB+ recommended).

**2. No data in Grafana**
*   Verify producers are running: `docker-compose logs sensor-producer`
*   Check InfluxDB connection: `docker-compose logs influx-consumer`
*   Wait a few minutes for the initial data pipeline to flush.

### Useful Commands

*   **View Logs**: `docker-compose logs -f`
*   **Restart Service**: `docker-compose restart <service-name>`
*   **Stop System**: `docker-compose down`
*   **Clean Reset**: `docker-compose down -v` (Deletes all data)

---

## Additional Documentation

For more detailed information, please refer to the following documentation files in the `nt-scada/` directory:

- **[ARCHITECTURE.md](nt-scada/ARCHITECTURE.md)** - Deep dive into system architecture and design decisions
- **[QUICK_START.md](nt-scada/QUICK_START.md)** - Simplified quick start guide
- **[TROUBLESHOOTING.md](nt-scada/TROUBLESHOOTING.md)** - Comprehensive troubleshooting guide
- **[PRODUCTION_GUIDE.md](nt-scada/PRODUCTION_GUIDE.md)** - Production deployment guidelines
- **[IMPLEMENTATION_SUMMARY.md](nt-scada/IMPLEMENTATION_SUMMARY.md)** - Summary of implementation details
- **[ATTACK_DATA_SETUP_GUIDE.md](nt-scada/ATTACK_DATA_SETUP_GUIDE.md)** - Guide for loading SWaT attack data

---

## Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the Repository**
   ```bash
   git fork https://github.com/cymosis/SCADA-PROJECT.git
   ```

2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Your Changes**
   - Follow the existing code style
   - Add tests if applicable
   - Update documentation as needed

4. **Commit Your Changes**
   ```bash
   git commit -m "Add feature: your feature description"
   ```

5. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Submit a Pull Request**
   - Provide a clear description of your changes
   - Reference any related issues
   - Ensure all tests pass

### Areas for Contribution
- **Bug Fixes**: Help identify and fix issues
- **New Features**: Add new functionality or components
- **Documentation**: Improve or expand documentation
- **Testing**: Add or improve test coverage
- **UI/UX**: Enhance Grafana dashboards and visualizations
- **Performance**: Optimize processing pipelines

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---


