# NT-SCADA Quick Start Guide

## 🚀 Start the System (Windows)

### Option 1: Using Batch Script
```cmd
start.bat
```

### Option 2: Using Docker Compose
```cmd
docker-compose up -d
```

## 🌐 Access Dashboards

Wait 2-3 minutes after startup, then access:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin / admin |
| **Flink Dashboard** | http://localhost:8081 | No auth |
| **InfluxDB** | http://localhost:8086 | admin / adminpass123 |

## 📊 View Data in Grafana

1. Open http://localhost:3000
2. Login: `admin` / `admin`
3. Go to **Dashboards** → **Browse**
4. Click **NT-SCADA Dashboard**
5. You should see:
   - Real-time sensor values
   - Anomaly detection metrics
   - Tabular data views
   - Analog plots
   - Distribution charts

## 🔍 Monitor Services

### View All Logs
```cmd
docker-compose logs -f
```

### View Specific Service Logs
```cmd
docker-compose logs -f sensor-producer
docker-compose logs -f stream-processor
docker-compose logs -f influx-consumer
docker-compose logs -f batch-analytics
```

### Check Service Status
```cmd
docker-compose ps
```

## 🧪 Test the System

### 1. Verify Kafka Topics
```cmd
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

Expected topics:
- `scada.sensors`
- `scada.actuators`
- `scada.processed`
- `scada.anomalies`

### 2. View Sensor Messages
```cmd
docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic scada.sensors --max-messages 5
```

### 3. View Anomalies
```cmd
docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic scada.anomalies --max-messages 5
```

### 4. Query InfluxDB
```cmd
docker-compose exec influxdb influx query --org nt-scada --token nt-scada-token-secret-key-12345 "from(bucket:\"scada_data\") |> range(start: -1h) |> filter(fn: (r) => r._measurement == \"sensor_data\") |> limit(n: 10)"
```

## 🤖 Run Batch Analytics

The batch analytics runs automatically on startup. To run again:

```cmd
docker-compose restart batch-analytics
docker-compose logs -f batch-analytics
```

### View Generated Models
```cmd
docker-compose exec batch-analytics ls -la /app/models
```

Expected files:
- `binary_classifier.pkl`
- `binary_scaler.pkl`
- `multiclass_classifier.pkl`
- `multiclass_scaler.pkl`
- `class_names.pkl`

### View Reports
```cmd
docker-compose exec batch-analytics ls -la /app/reports
```

## 🛑 Stop the System

### Option 1: Using Batch Script
```cmd
stop.bat
```

### Option 2: Using Docker Compose
```cmd
docker-compose down
```

### Remove All Data (Reset)
```cmd
docker-compose down -v
```

## 🔧 Troubleshooting

### Problem: No data in Grafana

**Solution:**
1. Wait 2-3 minutes for data to accumulate
2. Check if producers are running:
   ```cmd
   docker-compose logs sensor-producer
   ```
3. Verify InfluxDB consumer is writing data:
   ```cmd
   docker-compose logs influx-consumer
   ```

### Problem: Kafka connection errors

**Solution:**
1. Check Kafka is healthy:
   ```cmd
   docker-compose logs kafka
   ```
2. Restart Kafka:
   ```cmd
   docker-compose restart kafka zookeeper
   ```

### Problem: Port already in use

**Solution:**
1. Check which ports are in use:
   ```cmd
   netstat -ano | findstr :3000
   netstat -ano | findstr :9092
   netstat -ano | findstr :8086
   ```
2. Stop conflicting services or change ports in `docker-compose.yml`

### Problem: Services keep restarting

**Solution:**
1. Check logs for errors:
   ```cmd
   docker-compose logs <service-name>
   ```
2. Increase Docker memory allocation (Docker Desktop → Settings → Resources)

## 📈 Performance Tips

1. **Adjust Data Generation Rate**: Edit `producers/sensor_producer.py` and change `time.sleep(2)` value
2. **Reduce Batch Size**: Modify producer batch sizes to reduce memory usage
3. **Increase Resources**: Allocate more RAM to Docker (recommended: 8GB+)

## 🎯 Next Steps

1. ✅ Start the system
2. ✅ Access Grafana dashboard
3. ✅ Monitor real-time data
4. ✅ Check anomaly detection
5. ✅ Run batch analytics
6. ✅ Explore ML models
7. 📚 Read full README.md for advanced features
8. 🔬 Integrate with SWaT dataset
9. 🚀 Deploy to Kubernetes (future)

## 📞 Need Help?

- Check the full **README.md** for detailed documentation
- View logs: `docker-compose logs -f`
- Restart services: `docker-compose restart <service-name>`
- Reset everything: `docker-compose down -v && docker-compose up -d`

---

**Happy Monitoring! 🏭⚡**
