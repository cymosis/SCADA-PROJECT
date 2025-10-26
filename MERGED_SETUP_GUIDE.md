# Merged NT-SCADA Setup Guide

## ✅ What Was Done

Your existing infrastructure and NT-SCADA have been **merged into one unified system**!

### Changes Made:

1. **Updated `c:\scada-docker\docker-compose.yml`**:
   - ✅ Kept your existing Kafka, Zookeeper, Kafka-UI
   - ✅ Upgraded InfluxDB 1.8 → 2.7 (required for NT-SCADA)
   - ✅ Upgraded Grafana 9.0 → 10.2
   - ✅ Upgraded Flink 1.16 → 1.18
   - ✅ Added NT-SCADA producers (sensor + actuator)
   - ✅ Added NT-SCADA stream processor
   - ✅ Added NT-SCADA InfluxDB consumer
   - ✅ Added NT-SCADA batch analytics
   - ✅ Commented out Telegraf (needs config update for InfluxDB 2.x)
   - ✅ Added unified network: `scada-network`

2. **Services Now Running** (13 total):
   - Infrastructure: Zookeeper, Kafka, Kafka-UI
   - Storage: InfluxDB 2.7
   - Visualization: Grafana 10.2
   - Stream Processing: Flink JobManager, Flink TaskManager
   - Data Producers: Sensor Producer, Actuator Producer
   - Processors: Stream Processor, InfluxDB Consumer
   - Analytics: Batch Analytics

## 🚀 How to Start the Merged System

### Step 1: Stop Your Old Setup (if running)

```cmd
cd c:\scada-docker
docker-compose down
```

**⚠️ IMPORTANT**: This will remove your old InfluxDB 1.8 data since we're upgrading to InfluxDB 2.x

### Step 2: Remove Old InfluxDB Volume (optional but recommended)

```cmd
docker volume rm scada-docker_influxdb_data
```

### Step 3: Start the Merged System

```cmd
cd c:\scada-docker
docker-compose up -d
```

This will:
- Pull new images (InfluxDB 2.7, Grafana 10.2, Flink 1.18)
- Build NT-SCADA components (producers, processors, consumers)
- Start all 13 services
- Create topics automatically in Kafka

### Step 4: Verify Everything is Running

```cmd
docker-compose ps
```

You should see all services with status "Up".

### Step 5: Wait for Data (2-3 minutes)

The system needs time to:
- Initialize InfluxDB
- Create Kafka topics
- Start producing data
- Process and store data

## 🌐 Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin / admin |
| **Kafka UI** | http://localhost:8080 | No auth |
| **Flink Dashboard** | http://localhost:8081 | No auth |
| **InfluxDB** | http://localhost:8086 | admin / adminpass123 |

## 📊 What's Different from Before

### InfluxDB Changes

**Before (InfluxDB 1.8)**:
- Database: `scada`
- No authentication
- InfluxQL query language

**After (InfluxDB 2.x)**:
- Organization: `nt-scada`
- Bucket: `scada_data`
- Token authentication: `nt-scada-token-secret-key-12345`
- Flux query language

### Kafka Topics

**Your old topics** (if you had any):
- `sensors-raw`
- `actuators-raw`

**NT-SCADA topics** (auto-created):
- `scada.sensors` - Raw sensor data
- `scada.actuators` - Raw actuator data
- `scada.processed` - Processed sensor data with classifications
- `scada.anomalies` - Filtered anomalous data only

### Telegraf Status

**Temporarily disabled** because it needs configuration updates for InfluxDB 2.x.

To re-enable Telegraf:
1. Update `telegraf/telegraf.conf` for InfluxDB 2.x
2. Uncomment the telegraf service in `docker-compose.yml`
3. Restart: `docker-compose up -d`

## 🔍 Verify Data Flow

### 1. Check Kafka Topics

```cmd
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

Expected output:
```
scada.actuators
scada.anomalies
scada.processed
scada.sensors
```

### 2. View Sensor Data in Kafka

```cmd
docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic scada.sensors --max-messages 5
```

### 3. Check InfluxDB Has Data

```cmd
docker-compose exec influxdb influx query --org nt-scada --token nt-scada-token-secret-key-12345 "from(bucket:\"scada_data\") |> range(start: -1h) |> limit(n: 10)"
```

### 4. View Grafana Dashboard

1. Open http://localhost:3000
2. Login: `admin` / `admin`
3. Go to Dashboards → Browse
4. Open **NT-SCADA Dashboard**
5. You should see real-time data flowing!

## 📈 Monitor the System

### View All Logs

```cmd
docker-compose logs -f
```

### View Specific Service Logs

```cmd
# Sensor data producer
docker-compose logs -f sensor-producer

# Stream processor (anomaly detection)
docker-compose logs -f stream-processor

# InfluxDB consumer
docker-compose logs -f influx-consumer

# Batch analytics
docker-compose logs -f batch-analytics
```

### Check Resource Usage

```cmd
docker stats
```

## 🔧 Troubleshooting

### Problem: Services keep restarting

**Solution**: Check logs for the specific service
```cmd
docker-compose logs <service-name>
```

### Problem: No data in Grafana

**Solution**: 
1. Wait 2-3 minutes for data to accumulate
2. Check producers are running: `docker-compose logs sensor-producer`
3. Check InfluxDB has data (see verification steps above)

### Problem: Port conflicts

**Solution**: Make sure your old setup is stopped
```cmd
docker-compose down
docker ps -a
```

### Problem: Out of memory

**Solution**: Increase Docker Desktop memory allocation
1. Docker Desktop → Settings → Resources
2. Set Memory to at least 8GB
3. Apply & Restart

## 🛑 Stop the System

```cmd
cd c:\scada-docker
docker-compose down
```

To remove all data and start fresh:
```cmd
docker-compose down -v
```

## 📚 Next Steps

1. ✅ Explore the Grafana dashboard
2. ✅ Monitor real-time anomaly detection
3. ✅ Run batch analytics: `docker-compose restart batch-analytics`
4. ✅ Check generated ML models: `ls nt-scada/batch/models/`
5. ✅ View daily reports: `ls nt-scada/batch/reports/`
6. 📖 Read full documentation: `nt-scada/README.md`

## 🔄 Re-enabling Telegraf (Optional)

If you want to use Telegraf alongside NT-SCADA, update the config:

**Edit `telegraf/telegraf.conf`**:

```toml
[agent]
  interval = "5s"

[[inputs.kafka_consumer]]
  brokers = ["kafka:29092"]
  topics = ["scada.sensors", "scada.actuators"]
  group_id = "telegraf-consumer"
  data_format = "json"

[[outputs.influxdb_v2]]
  urls = ["http://influxdb:8086"]
  token = "nt-scada-token-secret-key-12345"
  organization = "nt-scada"
  bucket = "scada_data"
```

Then uncomment telegraf in `docker-compose.yml` and restart:
```cmd
docker-compose up -d
```

## ✅ Summary

You now have a **unified SCADA system** with:
- ✅ Single infrastructure (Kafka, InfluxDB, Grafana, Flink)
- ✅ Real-time data generation (30 sensors, 24 actuators)
- ✅ Stream processing (anomaly detection, classification)
- ✅ Time-series storage (InfluxDB 2.x)
- ✅ Machine learning (binary + multi-class models)
- ✅ Visualization (Grafana dashboards)
- ✅ Batch analytics (daily reports)

**Everything runs from one command**: `docker-compose up -d`

---

**Questions?** Check the troubleshooting section above or the full docs in `nt-scada/README.md`
