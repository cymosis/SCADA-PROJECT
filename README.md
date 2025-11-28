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

## Overview

**The aim of the project is to develop a supervisory control and data acquisition platform based on open-source technologies. We implement ingesting, storing, analyzing, and visualizing large volumes of analog and digital inputs collected from the SWaT dataset.**
---

## System Architecture


### Component Details

1.  **Data Sources**:

    *   **SWaT Dataset**: The SWAT data contains both normal and anomalous data during the sewage treating process.

2.  **Data Ingestion & Messaging**:
    *   **Apache Kafka**: Using the cleaned data saved in excel files, we will use Kafka to simulate a real-time data stream.
        *   **Purpose**: It acts as a highly scalable, fault-tolerant, and high-throughput distributed streaming platform. 

3.  **Data Processing**:
    *   **Apache Kafka**: This will be the primary engine for both stream processing and batch processing.
        *   **How**: Using kafka producers and consumers,  to process the data in real-time and store it in InfluxDB.

4.  **Time-Series Database**:
    *   **InfluxDB**:
        *   Stores the data while keeping the time stamps which is useful in anomaly detection.

5.  **Container Orchestration**:
    *   **Kubernetes (K8s)**:
        *   Kubernetes is a platform for automating deployment, scaling, and management of containerized applications. All our components (Kafka brokers, Flink jobs, InfluxDB, Grafana) will run as containers on Kubernetes. Kubernetes provides scalability, high availability, and simplified management for your distributed SCADA system. It can also be scaled up easily and can also ensure components restart automatically if they fail.

6.  **Data Visualization & Control**:
    *   **Grafana**:
        *   This is the primary user interface used to visualize, the current state, anomalies and flink jobs metrics.for visualizing all sensor and actuator data (tabular, plots, dashboards) as it connects easily to InfluxDB and Kafka. It will display the results of our real-time anomaly detection and fine-grained classification. It can also be used to send *control commands* back to actuators (via a custom plugin or integration with Kafka).

7.  **Actuators (Output Control)**:
    *   **Industrial Equipment (Simulated)**: In a real SCADA system, these are physical devices but, in our project, we will likely simulate their behavior. Typically, Grafana via user interaction will send a control command to a Kafka topic. A Flink job will consume this command from Kafka and will then interface with the physical actuator but in our case, the actuator service will simply log the command or update a simulated state.

8.  **Apache Flink Jobs**:
    *  **Real-time Analytics**: To provide real time analytics of consumers, producers and topics.
    

-

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


### Data Visualization
- **Interactive Dashboards**: Pre-configured Grafana dashboards for real-time monitoring
- **Historical Analysis**: Query and visualize trends over time
- **Anomaly Alerts**: Visual indicators for detected anomalies
- **Tabular Views**: Comprehensive sensor and actuator data tables

### Scalability & Reliability
- **Kubernetes Orchestration**: Auto-scaling and self-healing infrastructure
- **High Availability**: Redundant components and automatic failover
- **Distributed Processing**: Workload distributed across multiple nodes
- **Data Persistence**: Reliable storage with InfluxDB time-series database

---

## Work Plan & Phases


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

## 🖥 Service Dashboard

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



---

<p align="center">
  We acknowledge using the SWAT data set in this project
</p>
