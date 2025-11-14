# 🚀 NT-SCADA Quick Start Guide

## Step-by-Step Setup for Beginners

This guide will help you get the NT-SCADA system running on your computer, even if you're new to Docker and these technologies.

---

## 📋 Prerequisites Checklist

Before starting, install these required software:

### 1. Install Docker Desktop
- **Windows/Mac**: Download from https://www.docker.com/products/docker-desktop
- **Linux**: Follow instructions at https://docs.docker.com/engine/install/
- After installation, open Docker Desktop and ensure it's running

### 2. Install Git
- Download from: https://git-scm.com/downloads
- During installation, use default settings

### 3. Install Python (for model training)
- Download from: https://www.python.org/downloads/
- Choose Python 3.9 or higher
- ✅ Check "Add Python to PATH" during installation

---

## 🎯 Phase 1: Get the Project

### Option A: Clone from GitHub (Recommended)

```bash
# Open Terminal (Mac/Linux) or Command Prompt (Windows)

# Navigate to where you want the project
cd Desktop  # or any folder you prefer

# Clone the repository
git clone https://github.com/cymosis/SCADA-PROJECT.git

# Navigate into the project
cd SCADA-PROJECT

# Check what's there
ls  # Mac/Linux
dir  # Windows
```

### Option B: If Repository is Private or You Don't Have Access

Create the project structure manually:

```bash
# Create project folder
mkdir SCADA-PROJECT
cd SCADA-PROJECT

# Create subdirectories
mkdir telegraf stream producers actuators models data data/swat notebooks
```

Then copy the files I've created into the appropriate directories.

---

## 🏗️ Phase 2: Set Up Project Structure

Your project should have this structure:

```
SCADA-PROJECT/
├── docker-compose.yml       ← Your existing file
├── telegraf/
│   └── telegraf.conf       ← Create this
├── stream/
│   └── stream_processor.py ← Create this
├── producers/
│   ├── sensor_producer.py  ← Create this
│   └── control_producer.py ← Create this
├── actuators/
│   └── mock_actuator.py    ← Create this
├── models/
│   └── train_binary_model.py ← Create this
└── data/
    └── swat/               ← Place SWaT dataset here
```

---

## 📦 Phase 3: Download SWaT Dataset

1. **Get the Dataset**:
   - Contact your mentor (Imre Lendak) for the SWaT dataset
   - Or download from: https://itrust.sutd.edu.sg/itrust-labs_datasets/dataset_info/

2. **Place the Dataset**:
   ```
   SCADA-PROJECT/data/swat/
   ├── SWaT_Dataset_Normal_v1.csv
   └── SWaT_Dataset_Attack_v0.csv
   ```

---

## 🐳 Phase 4: Start Docker Services

### Step 4.1: Verify Docker is Running

```bash
# Check Docker is running
docker --version
docker-compose --version

# Test Docker
docker run hello-world
```

If you see "Hello from Docker!", you're ready!

### Step 4.2: Start Core Infrastructure

```bash
# From SCADA-PROJECT directory
cd SCADA-PROJECT

# Start Zookeeper, Kafka, InfluxDB, Grafana
docker-compose up -d zookeeper kafka influxdb grafana kafka-ui

# Wait 30 seconds for services to start
# You can watch the logs:
docker-compose logs -f kafka
# Press Ctrl+C to stop watching logs

# Check if services are running
docker-compose ps
```

You should see these services as "Up":
- zookeeper
- kafka  
- influxdb
- grafana
- kafka-ui

### Step 4.3: Access Web Interfaces

Open your browser and visit:

1. **Kafka UI**: http://localhost:8080
   - See Kafka topics and messages

2. **Grafana**: http://localhost:3000
   - Username: `admin`
   - Password: `admin`
   - You'll be prompted to change password

3. **InfluxDB**: http://localhost:8086
   - No UI in version 1.8, but API is available

---

## 📊 Phase 5: Create Kafka Topics

You have two options:

### Option A: Using Kafka UI (Easiest for Beginners)

1. Go to http://localhost:8080
2. Click "Topics" in the left menu
3. Click "Add a Topic" button
4. Create these topics (one by one):
   - Topic name: `sensor-inputs`, Partitions: 3
   - Topic name: `processed-data`, Partitions: 3
   - Topic name: `anomalies`, Partitions: 3
   - Topic name: `control-commands`, Partitions: 3

### Option B: Using Command Line

```bash
# Access Kafka container
docker exec -it kafka bash

# Create topics
kafka-topics --create --topic sensor-inputs --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

kafka-topics --create --topic processed-data --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

kafka-topics --create --topic anomalies --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

kafka-topics --create --topic control-commands --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

# Verify topics were created
kafka-topics --list --bootstrap-server localhost:9092

# Exit container
exit
```

---

## 🗄️ Phase 6: Set Up InfluxDB Database

### Option A: Using Command Line (Recommended)

```bash
# Access InfluxDB container
docker exec -it influxdb bash

# Open InfluxDB CLI
influx

# Create database
CREATE DATABASE scada_data

# Verify
SHOW DATABASES

# Exit
exit
exit
```

### Option B: Using API

```bash
curl -X POST http://localhost:8086/query --data-urlencode "q=CREATE DATABASE scada_data"
```

---

## 🎨 Phase 7: Configure Grafana

1. **Login to Grafana**: http://localhost:3000
   - Username: `admin`
   - Password: `admin`

2. **Add InfluxDB Data Source**:
   - Click ⚙️ (Configuration) → Data Sources
   - Click "Add data source"
   - Select "InfluxDB"
   - Configure:
     - Name: `SCADA InfluxDB`
     - URL: `http://influxdb:8086`
     - Database: `scada_data`
   - Click "Save & Test"
   - You should see "Data source is working"

3. **Create Your First Dashboard**:
   - Click + (Create) → Dashboard
   - Click "Add new panel"
   - In Query, select:
     - Data source: `SCADA InfluxDB`
     - FROM: select `sensor_data`
   - Click "Apply"
   - Click 💾 (Save) to save dashboard

---

## 🤖 Phase 8: Start Telegraf

```bash
# From SCADA-PROJECT directory
docker-compose up -d telegraf

# Check logs
docker-compose logs -f telegraf

# You should see: "Started successfully"
# Press Ctrl+C to stop watching logs
```

---

## 🎓 Phase 9: Train ML Models (Optional but Recommended)

### Step 9.1: Install Python Dependencies

```bash
# Create virtual environment (optional but recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install required packages
pip install pandas numpy scikit-learn kafka-python influxdb-client joblib
```

### Step 9.2: Train Binary Classification Model

```bash
# Navigate to models directory
cd models

# Run training script
python train_binary_model.py

# This will create:
# - models/binary_classifier.pkl
# - models/scaler.pkl
# - models/binary_classification_report.txt
```

---

## 🚀 Phase 10: Start the Complete System

Now let's start all components:

```bash
# From SCADA-PROJECT directory

# Start all services
docker-compose up -d

# Check all services are running
docker-compose ps

# You should see all services as "Up":
# - zookeeper
# - kafka
# - kafka-ui
# - influxdb
# - grafana
# - telegraf
# - stream-processor
# - control-processor
# - mock-actuator
```

---

## 🧪 Phase 11: Test the System

### Test 1: Check Logs

```bash
# Watch stream processor logs
docker-compose logs -f stream-processor

# In another terminal, watch control processor
docker-compose logs -f control-processor

# In another terminal, watch mock actuator
docker-compose logs -f mock-actuator
```

### Test 2: Start Sensor Data Producer

If you have the SWaT dataset:

```bash
# Create a sensor producer service or run manually
cd producers
python sensor_producer.py
```

If you don't have the dataset, it will generate test data automatically.

### Test 3: Monitor in Kafka UI

1. Go to http://localhost:8080
2. Click on "Topics"
3. Click on "sensor-inputs"
4. Click "Messages" tab
5. You should see messages flowing in

### Test 4: Check InfluxDB Data

```bash
docker exec -it influxdb influx

# Inside InfluxDB CLI:
USE scada_data
SHOW MEASUREMENTS
SELECT * FROM sensor_data LIMIT 10
exit
```

### Test 5: View in Grafana

1. Go to http://localhost:3000
2. Navigate to your dashboard
3. You should see real-time data visualization

---

## 🛠️ Common Issues and Solutions

### Issue 1: "Cannot connect to Docker daemon"

**Solution**: Make sure Docker Desktop is running

```bash
# Check Docker status
docker info
```

### Issue 2: "Port already in use"

**Solution**: Another application is using the port

```bash
# Check what's using port 9092 (example)
# Windows:
netstat -ano | findstr :9092

# Mac/Linux:
lsof -i :9092

# Kill the process or change port in docker-compose.yml
```

### Issue 3: Kafka won't start

**Solution**: Zookeeper needs to start first

```bash
# Stop all services
docker-compose down

# Start Zookeeper first
docker-compose up -d zookeeper

# Wait 10 seconds
sleep 10

# Start Kafka
docker-compose up -d kafka

# Wait 20 seconds
sleep 20

# Start remaining services
docker-compose up -d
```

### Issue 4: "No data in Grafana"

**Checklist**:
1. ✅ Is InfluxDB database created?
2. ✅ Is Telegraf running?
3. ✅ Is sensor producer sending data?
4. ✅ Are Kafka topics created?
5. ✅ Is Grafana data source configured correctly?

```bash
# Check InfluxDB has data
docker exec -it influxdb influx -execute 'SHOW DATABASES'
docker exec -it influxdb influx -database scada_data -execute 'SHOW MEASUREMENTS'
```

---

## 📚 Useful Commands

### Docker Compose Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart kafka

# View logs
docker-compose logs -f service-name

# List running services
docker-compose ps

# Remove all containers and volumes (CAUTION: deletes data!)
docker-compose down -v
```

### Docker Commands

```bash
# List running containers
docker ps

# Stop a container
docker stop container-name

# Access container shell
docker exec -it container-name bash

# View container logs
docker logs container-name

# Remove stopped containers
docker container prune
```

---

## 🎯 Next Steps

Once everything is running:

1. ✅ **Verify Data Flow**: Check logs to ensure data flows through the pipeline
2. ✅ **Create Dashboards**: Build comprehensive Grafana dashboards
3. ✅ **Train Advanced Models**: Implement fine-grained classification (Batch 2)
4. ✅ **Daily Statistics**: Implement Batch 3 for daily analytics
5. ✅ **Test Scenarios**: Test different anomaly scenarios
6. ✅ **Documentation**: Document your findings and insights

---

## 📞 Getting Help

If you encounter issues:

1. **Check the Logs**: Most issues are revealed in logs
   ```bash
   docker-compose logs service-name
   ```

2. **Restart Services**: Sometimes a simple restart helps
   ```bash
   docker-compose restart service-name
   ```

3. **Consult Team Members**: Your teammates may have encountered the same issue

4. **Ask Your Mentor**: Imre Lendak can provide guidance

5. **Check Documentation**:
   - Kafka: https://kafka.apache.org/documentation/
   - InfluxDB: https://docs.influxdata.com/
   - Grafana: https://grafana.com/docs/

---

## 🎉 Success Criteria

You know the system is working when:

✅ All Docker containers are running (`docker-compose ps`)
✅ Kafka topics are created and receiving messages
✅ InfluxDB contains sensor data
✅ Grafana displays real-time visualizations
✅ Stream processor detects anomalies
✅ Control commands are generated for anomalies
✅ Mock actuator responds to commands

---

**Good luck with your NT-SCADA project! 🚀**

**Team**: Cynthia Mutisya, Narayan Anshu, Sheillah Khaluvitsi
**Mentor**: Imre Lendak
