# NT-SCADA Troubleshooting Guide

## 🔍 Common Issues and Solutions

### 1. Services Won't Start

#### Problem: Docker Compose fails to start services

**Symptoms:**
- Error: "Cannot start service..."
- Services show "Exited" status
- Port binding errors

**Solutions:**

```cmd
# Check if Docker is running
docker --version
docker ps

# Check for port conflicts
netstat -ano | findstr :9092
netstat -ano | findstr :3000
netstat -ano | findstr :8086
netstat -ano | findstr :8081

# Stop conflicting services or change ports in docker-compose.yml

# Restart Docker Desktop
# Right-click Docker Desktop icon → Restart

# Clean up and restart
docker-compose down -v
docker-compose up -d
```

---

### 2. No Data in Grafana

#### Problem: Grafana dashboard shows "No Data"

**Symptoms:**
- Empty graphs and tables
- "No data" messages in panels
- Queries return no results

**Solutions:**

**Step 1: Wait for data accumulation**
```cmd
# Wait 2-3 minutes after startup
# Check if producers are running
docker-compose ps | findstr producer
```

**Step 2: Verify producers are sending data**
```cmd
# Check sensor producer logs
docker-compose logs sensor-producer | findstr "Sent"

# Check actuator producer logs
docker-compose logs actuator-producer | findstr "Sent"
```

**Step 3: Verify Kafka has data**
```cmd
# List topics
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Consume sensor messages
docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic scada.sensors --max-messages 5
```

**Step 4: Verify stream processor is working**
```cmd
# Check stream processor logs
docker-compose logs stream-processor | findstr "Processed"
```

**Step 5: Verify InfluxDB consumer is writing**
```cmd
# Check consumer logs
docker-compose logs influx-consumer | findstr "Written"
```

**Step 6: Query InfluxDB directly**
```cmd
docker-compose exec influxdb influx query --org nt-scada --token nt-scada-token-secret-key-12345 "from(bucket:\"scada_data\") |> range(start: -1h) |> limit(n: 10)"
```

**Step 7: Check Grafana datasource**
- Open Grafana: http://localhost:3000
- Go to Configuration → Data Sources
- Click "InfluxDB"
- Click "Save & Test"
- Should show "Data source is working"

---

### 3. Kafka Connection Errors

#### Problem: Services can't connect to Kafka

**Symptoms:**
- "NoBrokersAvailable" errors
- "Connection refused" errors
- Services keep restarting

**Solutions:**

```cmd
# Check Kafka health
docker-compose logs kafka | findstr "started"

# Verify Kafka is listening
docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Restart Kafka and Zookeeper
docker-compose restart zookeeper kafka

# Wait 30 seconds, then restart dependent services
timeout /t 30
docker-compose restart sensor-producer actuator-producer stream-processor influx-consumer
```

---

### 4. InfluxDB Connection Errors

#### Problem: Services can't connect to InfluxDB

**Symptoms:**
- "Connection refused" errors
- "Unauthorized" errors
- "Bucket not found" errors

**Solutions:**

```cmd
# Check InfluxDB health
docker-compose exec influxdb influx ping

# Verify InfluxDB is ready
docker-compose logs influxdb | findstr "Listening"

# Check bucket exists
docker-compose exec influxdb influx bucket list --org nt-scada --token nt-scada-token-secret-key-12345

# Restart InfluxDB
docker-compose restart influxdb

# Wait 20 seconds, then restart consumers
timeout /t 20
docker-compose restart influx-consumer batch-analytics
```

---

### 5. Flink Dashboard Not Accessible

#### Problem: Can't access Flink at http://localhost:8081

**Symptoms:**
- "Connection refused" or "Site can't be reached"
- Flink UI doesn't load

**Solutions:**

```cmd
# Check Flink JobManager is running
docker-compose ps | findstr flink

# Check Flink logs
docker-compose logs flink-jobmanager

# Restart Flink services
docker-compose restart flink-jobmanager flink-taskmanager

# Wait 15 seconds
timeout /t 15

# Try accessing again: http://localhost:8081
```

---

### 6. High CPU/Memory Usage

#### Problem: Docker consuming too many resources

**Symptoms:**
- Computer running slow
- Docker Desktop showing high resource usage
- Services crashing due to OOM (Out of Memory)

**Solutions:**

**Increase Docker Resources:**
1. Open Docker Desktop
2. Go to Settings → Resources
3. Increase Memory to at least 8GB
4. Increase CPU to at least 4 cores
5. Click "Apply & Restart"

**Reduce Data Generation Rate:**

Edit `producers/sensor_producer.py`:
```python
# Change from:
time.sleep(2)
# To:
time.sleep(5)  # Slower generation
```

Edit `producers/actuator_producer.py`:
```python
# Change from:
time.sleep(3)
# To:
time.sleep(6)  # Slower generation
```

Then restart:
```cmd
docker-compose restart sensor-producer actuator-producer
```

---

### 7. Batch Analytics Not Running

#### Problem: ML models not being created

**Symptoms:**
- No files in `batch/models/` directory
- No reports in `batch/reports/` directory
- Batch analytics container exits immediately

**Solutions:**

```cmd
# Check batch analytics logs
docker-compose logs batch-analytics

# Common issue: Not enough data
# Wait 10-15 minutes for data to accumulate, then run:
docker-compose restart batch-analytics

# Monitor the training process
docker-compose logs -f batch-analytics

# Check if models were created
docker-compose exec batch-analytics ls -la /app/models
docker-compose exec batch-analytics ls -la /app/reports
```

---

### 8. Grafana Can't Login

#### Problem: Can't login to Grafana

**Symptoms:**
- "Invalid username or password"
- Login page not loading

**Solutions:**

**Default credentials:**
- Username: `admin`
- Password: `admin`

**Reset Grafana:**
```cmd
# Stop Grafana
docker-compose stop grafana

# Remove Grafana data
docker volume rm nt-scada_grafana-data

# Restart Grafana
docker-compose up -d grafana

# Wait 10 seconds
timeout /t 10

# Try login again with admin/admin
```

---

### 9. Dashboard Not Auto-Provisioned

#### Problem: NT-SCADA dashboard not appearing in Grafana

**Symptoms:**
- Empty dashboard list
- Can't find NT-SCADA dashboard

**Solutions:**

**Manual Import:**
1. Open Grafana: http://localhost:3000
2. Click "+" → "Import"
3. Click "Upload JSON file"
4. Select `dashboards/grafana_dashboard.json`
5. Select "InfluxDB" as datasource
6. Click "Import"

**Check Provisioning:**
```cmd
# Check if dashboard file is mounted
docker-compose exec grafana ls -la /etc/grafana/provisioning/dashboards/

# Restart Grafana
docker-compose restart grafana
```

---

### 10. Anomalies Not Being Detected

#### Problem: All sensor readings show anomaly = false

**Symptoms:**
- Anomaly gauge shows 0
- No data in `scada.anomalies` topic
- All operational states are "OPTIMAL"

**Solutions:**

**This is normal if:**
- System just started (anomalies are random ~5%)
- Not enough data generated yet

**Verify anomaly detection is working:**
```cmd
# Check stream processor logs
docker-compose logs stream-processor | findstr "Anomalies"

# Consume from anomalies topic
docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic scada.anomalies --from-beginning --max-messages 10

# Wait 5-10 minutes for anomalies to appear naturally
```

**Force anomalies (for testing):**

Edit `producers/sensor_producer.py` and increase anomaly probability:
```python
# Change from:
'anomaly_prob': 0.05
# To:
'anomaly_prob': 0.20  # 20% anomalies
```

Restart:
```cmd
docker-compose restart sensor-producer
```

---

### 11. Docker Compose Version Issues

#### Problem: "version is obsolete" or syntax errors

**Symptoms:**
- YAML parsing errors
- Unknown directive errors

**Solutions:**

```cmd
# Check Docker Compose version
docker-compose --version

# Should be v2.0 or higher
# If not, update Docker Desktop

# Alternative: Use docker compose (without hyphen)
docker compose up -d
```

---

### 12. Volumes Permission Issues

#### Problem: Permission denied errors in containers

**Symptoms:**
- Can't write to `/app/models` or `/app/reports`
- Permission denied errors in logs

**Solutions:**

```cmd
# Stop all services
docker-compose down

# Remove volumes
docker volume rm nt-scada_influxdb-data
docker volume rm nt-scada_grafana-data
docker volume rm nt-scada_flink-checkpoints

# Restart
docker-compose up -d
```

---

### 13. Network Issues

#### Problem: Services can't communicate

**Symptoms:**
- "No route to host"
- "Connection refused" between services
- DNS resolution failures

**Solutions:**

```cmd
# Check network exists
docker network ls | findstr scada

# Inspect network
docker network inspect nt-scada_scada-network

# Recreate network
docker-compose down
docker-compose up -d
```

---

### 14. Complete Reset

#### Problem: Everything is broken, need fresh start

**Nuclear Option:**

```cmd
# Stop all containers
docker-compose down -v

# Remove all NT-SCADA containers
docker ps -a | findstr nt-scada
docker rm -f <container_ids>

# Remove all NT-SCADA volumes
docker volume ls | findstr nt-scada
docker volume rm <volume_names>

# Remove all NT-SCADA networks
docker network ls | findstr scada
docker network rm <network_name>

# Clean Docker system (optional - removes ALL unused resources)
docker system prune -a --volumes

# Restart Docker Desktop

# Start fresh
docker-compose up -d

# Wait 3-5 minutes
timeout /t 180

# Check status
docker-compose ps
```

---

## 🔧 Diagnostic Commands

### Check All Services Status
```cmd
docker-compose ps
```

### View All Logs
```cmd
docker-compose logs
```

### View Specific Service Logs
```cmd
docker-compose logs -f <service-name>
```

### Check Resource Usage
```cmd
docker stats
```

### Verify Kafka Topics
```cmd
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

### Test InfluxDB Connection
```cmd
docker-compose exec influxdb influx ping
```

### Check Grafana Health
```cmd
curl http://localhost:3000/api/health
```

### Inspect Container
```cmd
docker inspect <container-name>
```

---

## 📞 Getting Help

If issues persist:

1. **Check Logs**: `docker-compose logs -f`
2. **Review Documentation**: README.md, ARCHITECTURE.md
3. **Verify Requirements**: Docker version, available resources
4. **Search Error Messages**: Copy exact error to search engine
5. **Reset System**: Use complete reset procedure above

---

## 🐛 Known Issues

### Issue: Flink Python API Compatibility
**Status**: Workaround implemented  
**Solution**: Python-based stream processor (`stream_processor.py`) used instead of PyFlink

### Issue: Windows Path Separators
**Status**: Resolved  
**Solution**: All paths use forward slashes in Docker Compose

### Issue: Initial Data Delay
**Status**: Expected behavior  
**Solution**: Wait 2-3 minutes after startup for data to flow

---

## ✅ Health Check Checklist

Run through this checklist to verify system health:

- [ ] Docker Desktop is running
- [ ] All 11 services show "Up" status: `docker-compose ps`
- [ ] Kafka topics exist: `docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092`
- [ ] Producers are sending data: `docker-compose logs sensor-producer | findstr "Sent"`
- [ ] Stream processor is running: `docker-compose logs stream-processor | findstr "Processed"`
- [ ] InfluxDB consumer is writing: `docker-compose logs influx-consumer | findstr "Written"`
- [ ] InfluxDB has data: Query via UI or CLI
- [ ] Grafana is accessible: http://localhost:3000
- [ ] Grafana datasource works: Configuration → Data Sources → Test
- [ ] Dashboard shows data: Dashboards → NT-SCADA Dashboard
- [ ] Flink UI is accessible: http://localhost:8081

If all checks pass: **System is healthy!** ✅

---

**Need more help?** Check the full documentation in README.md and ARCHITECTURE.md
