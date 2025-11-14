# NT-SCADA Complete Setup Guide

This guide walks you through setting up the complete NT-SCADA system from scratch.

---

## 📋 Prerequisites

### Required Software
- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
- **Docker Compose** v2.0+
- **Python** 3.9 or higher
- **Git**
- **8GB+ RAM** (16GB recommended)
- **10GB+ free disk space**

### Check Installations
```bash
docker --version          # Should show v20.0+
docker-compose --version  # Should show v2.0+
python --version          # Should show 3.9+
git --version            # Should show 2.0+
```

---

## 🚀 Installation Steps

### Step 1: Clone the Repository

```bash
git clone https://github.com/cymosis/SCADA-PROJECT.git
cd SCADA-PROJECT/NT-SCADA-LOCAL-TEST
```

---

### Step 2: Install Python Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### Step 3: Prepare SWAT Dataset

1. **Download SWaT dataset** from iTrust or use provided data
2. **Place data files** in:
   ```
   data/swat/Attack Data 2019/
   data/swat/Normal Data 2023/
   ```
3. **Verify files exist**:
   ```bash
   # Windows
   dir data\swat\*

   # Linux/Mac
   ls -R data/swat/
   ```

---

### Step 4: Start Docker Services

```bash
# Start all services in detached mode
docker-compose up -d

# Wait 30-60 seconds for services to initialize
# Check status
docker-compose ps
```

**All services should show "Up" and healthy status:**
- ✅ zookeeper (healthy)
- ✅ kafka (healthy)
- ✅ influxdb (healthy)
- ✅ grafana
- ✅ telegraf
- ✅ stream-processor
- ✅ control-processor
- ✅ mock-actuator

---

### Step 5: Verify Services

#### Check Kafka
```bash
# Access Kafka UI
http://localhost:8080
```

#### Check InfluxDB
```bash
# Test InfluxDB connection
docker exec -it influxdb influx -execute "SHOW DATABASES"

# Should see: scada_data, _internal
```

#### Check Grafana
```bash
# Access Grafana
http://localhost:3000

# Default credentials:
Username: admin
Password: admin
```

---

### Step 6: Configure Grafana Data Source

1. **Login to Grafana** (http://localhost:3000)
2. **Go to**: Connections → Data sources
3. **Add InfluxDB**:
   - Name: `SCADA InfluxDB`
   - URL: `http://influxdb:8086`
   - Database: `scada_data`
   - HTTP Method: `GET`
4. **Save & Test** - should show green "Data source is working"

---

### Step 7: Start Sensor Data Producer

```bash
# Navigate to producers directory
cd producers

# Run the sensor producer
python sensor_producer.py
```

**You should see:**
```
✓ Connected to Kafka at localhost:9093
📊 Loaded dataset with 14,096 rows and 78 columns
🚀 Starting to stream data to topic: sensor-inputs
📡 Sent 100 messages...
📡 Sent 200 messages...
```

**Let it run for 2-3 minutes** to accumulate data.

---

### Step 8: Import Grafana Dashboard

1. **In Grafana**, go to: Dashboards → Import
2. **Upload file**: `grafana/swat_comprehensive_dashboard_FINAL.json`
3. **Or paste JSON** content directly
4. **Select data source**: SCADA InfluxDB
5. **Click Import**

---

### Step 9: View Your Dashboard

1. **Navigate to** the imported dashboard
2. **Set time range** to "Last 6 hours" (top right)
3. **You should see** sensor data flowing in real-time! 🎉

---

## 🔧 Configuration Details

### Kafka Configuration

**Topics automatically created:**
- `sensor-inputs` - Raw sensor data
- `processed-data` - Processed with ML predictions
- `anomalies` - Detected anomalies
- `control-commands` - Control actions

**Access Kafka directly:**
```bash
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic sensor-inputs \
  --from-beginning \
  --max-messages 5
```

### InfluxDB Configuration

**Database**: `scada_data`
**Measurements**: `sensor_data`, `kafka_consumer`

**Query data:**
```bash
docker exec -it influxdb influx -database scada_data -execute "SELECT * FROM sensor_data LIMIT 5"
```

### Telegraf Configuration

**File**: `telegraf/telegraf.conf`

**Key settings:**
- Consumes from Kafka topics
- Writes to InfluxDB
- Collects system metrics

**View logs:**
```bash
docker-compose logs telegraf --tail 50
```

---

## 🐛 Troubleshooting

### Problem: No data in Grafana

**Solution:**
1. Check sensor producer is running
2. Verify time range (try "Last 6 hours")
3. Check InfluxDB has data:
   ```bash
   docker exec -it influxdb influx -database scada_data -execute "SELECT COUNT(*) FROM sensor_data"
   ```

### Problem: Kafka not starting

**Solution:**
```bash
# Restart services
docker-compose down
docker-compose up -d

# Check logs
docker-compose logs kafka
```

### Problem: Port conflicts

**Solution:**
Check if ports are in use:
```bash
# Windows
netstat -ano | findstr :3000
netstat -ano | findstr :8086
netstat -ano | findstr :9092

# Linux/Mac
lsof -i :3000
lsof -i :8086
lsof -i :9092
```

Stop conflicting services or change ports in `docker-compose.yml`.

### Problem: Out of memory

**Solution:**
Increase Docker memory allocation:
- Docker Desktop → Settings → Resources → Memory → 8GB+

---

## 📊 Verification Checklist

- [ ] All Docker containers running and healthy
- [ ] Kafka accessible at localhost:9092
- [ ] InfluxDB accessible at localhost:8086
- [ ] Grafana accessible at localhost:3000
- [ ] Sensor producer streaming data
- [ ] InfluxDB contains sensor_data measurements
- [ ] Grafana dashboard showing real-time data
- [ ] No errors in container logs

---

## 🎓 Next Steps

1. **Train ML Models**: See `notebooks/` for model training
2. **Enable Anomaly Detection**: Configure stream processor
3. **Set up Alerts**: Configure Grafana alert rules
4. **Scale Up**: Deploy to Kubernetes

---

## 📞 Support

If you encounter issues:
1. Check troubleshooting section above
2. Review container logs: `docker-compose logs [service]`
3. Open GitHub issue with:
   - Error messages
   - Output of `docker-compose ps`
   - Relevant log snippets

---

**Setup Time**: ~30-45 minutes

**Last Updated**: November 2025
