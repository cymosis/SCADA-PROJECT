# Grafana Dashboard Setup Guide

Complete guide to setting up and customizing the SWAT monitoring dashboard in Grafana.

---

## 📊 Dashboard Overview

The comprehensive SWAT monitoring dashboard includes:
- **18+ visualization panels**
- **6 process stages** (P1-P6)
- **78+ sensors** monitored
- **Real-time updates** (5-second refresh)
- **Historical data** analysis

---

## 🚀 Quick Import

### Method 1: Import from File

1. **Login to Grafana**: http://localhost:3000
2. **Go to**: Dashboards → Import (or click "+" → Import)
3. **Upload**: `grafana/swat_comprehensive_dashboard_FINAL.json`
4. **Select Data Source**: SCADA InfluxDB
5. **Click**: Import

### Method 2: Import from JSON

1. **Copy** the entire JSON content from the file
2. **Go to**: Dashboards → Import
3. **Paste** JSON into the text box
4. **Select Data Source**: SCADA InfluxDB  
5. **Click**: Import

---

## 🔧 Manual Data Source Configuration

If import fails or data source isn't found:

### Step 1: Add InfluxDB Data Source

1. **Navigate**: Connections → Data sources → Add data source
2. **Select**: InfluxDB
3. **Configure**:
   ```
   Name: SCADA InfluxDB
   Default: ✓ (checked)
   
   HTTP:
   URL: http://influxdb:8086
   Access: Server (default)
   
   InfluxDB Details:
   Database: scada_data
   User: (leave empty)
   Password: (leave empty)
   HTTP Method: GET
   ```
4. **Click**: Save & Test
5. **Verify**: Green success message

### Step 2: Get Data Source UID

1. **After saving**, look at the URL:
   ```
   http://localhost:3000/connections/datasources/edit/XXXXXXXX
   ```
2. **Copy** the UID (`XXXXXXXX`)

### Step 3: Update Dashboard JSON (if needed)

If dashboard shows "No data":

1. **Open dashboard** → Settings (⚙️) → JSON Model
2. **Find & Replace**:
   - Press Ctrl+H (or Cmd+H on Mac)
   - Find: `"uid": "SCADA_InfluxDB"`
   - Replace: `"uid": "YOUR_ACTUAL_UID"`
3. **Click**: Save changes
4. **Click**: Save dashboard

---

## 📈 Dashboard Panels Explained

### Row 1: System Overview

**Panel 1: System Status (Data Points)**
- **Type**: Stat
- **Metric**: Count of sensor_data points
- **Purpose**: Verify data is flowing

**Panel 2: Anomaly Detection Rate**
- **Type**: Time Series
- **Metric**: Anomalies per minute
- **Purpose**: Track anomaly detection performance

**Panel 3: Active Alerts**
- **Type**: Stat
- **Metric**: Count of active anomalies
- **Purpose**: Quick alert overview

---

### Row 2: Stage P1 - Raw Water Intake

**Panel 4: FIT-101 - Raw Water Inflow**
- **Sensor**: Flow Indicator Transmitter 101
- **Unit**: Flow rate
- **Thresholds**: Red line at max capacity (5)
- **Purpose**: Monitor incoming raw water

**Panel 5: LIT-101 - Raw Water Tank Level**
- **Sensor**: Level Indicator Transmitter 101
- **Unit**: Millimeters (mm)
- **Range**: 0-1200mm
- **Thresholds**: 
  - Yellow: Below 200mm (low)
  - Red: Above 1000mm (overflow risk)

**Panel 6: AIT-201 - Water Temperature**
- **Sensor**: Analog Input Temperature 201
- **Unit**: Degrees Celsius (°C)
- **Normal range**: 140-145°C
- **Purpose**: Monitor water quality

---

### Row 3: Stage P2 - Chemical Dosing

**Panel 7: AIT-202 - Post-Dosing Quality**
- Measures water quality after chemical treatment

**Panel 8: FIT-201 - Chemical Flow**
- Monitors dosing chemical flow rate

**Panel 9: P-203 - Dosing Pump Status**
- **Type**: Gauge
- **Values**: 0 (OFF/Red), 1-2 (ON/Green)
- **Purpose**: Monitor pump operation

---

### Rows 4-5: Stages P3, P4 (Similar structure)

Each stage follows the same pattern:
- Flow sensors (FIT)
- Level sensors (LIT)
- Pressure sensors (DPIT, PIT)
- Pump/valve status

---

### Row 6: Actuators & Control

**Panel 16: Pump Status Overview**
- **Type**: Table
- **Shows**: All pump statuses (P-101, P-102, P-203, P-401)
- **Format**: ON (green) / OFF (red)

**Panel 17: Valve Status Overview**
- **Type**: Table
- **Shows**: All valve statuses (MV-101, MV-201, MV-301, MV-401)
- **Format**: OPEN (green) / CLOSED (red)

---

## 🎨 Customization

### Change Panel Colors

1. **Edit panel** → Panel options
2. **Color scheme**: Select from dropdown
   - Classic palette
   - Green-Yellow-Red (gradient)
   - Single color
3. **Thresholds**: Add custom thresholds for color changes

### Adjust Time Range

**Quick ranges** (top right):
- Last 5 minutes
- Last 15 minutes
- Last 1 hour
- Last 6 hours
- Last 24 hours
- Custom range

### Add Threshold Alerts

1. **Edit panel** → Alert tab
2. **Create alert rule**:
   - Condition: WHEN value > threshold
   - For: 5 minutes
   - Evaluate: Every 1m
3. **Add notification channel** (email, Slack, etc.)

### Modify Refresh Rate

1. **Dashboard settings** → Time options
2. **Auto refresh**: Change from 5s to desired interval
   - 5s (default)
   - 10s
   - 30s
   - 1m

---

## 🔍 Query Examples

### Basic Sensor Query (InfluxQL)

```sql
SELECT mean("sensors_FIT 101") 
FROM "sensor_data" 
WHERE $timeFilter 
GROUP BY time($__interval) fill(null)
```

### Count Data Points

```sql
SELECT count("sensors_FIT 101") 
FROM "sensor_data" 
WHERE $timeFilter
```

### Multiple Sensors

```sql
SELECT 
  mean("sensors_FIT 101") as "Flow",
  mean("sensors_LIT 101") as "Level"
FROM "sensor_data" 
WHERE $timeFilter 
GROUP BY time($__interval)
```

---

## 📊 Panel Types Guide

### Time Series (Line Graph)
**Best for**: Continuous sensor data
**Use for**: Temperature, flow, pressure, level sensors

### Gauge
**Best for**: Binary states (ON/OFF, OPEN/CLOSED)
**Use for**: Pumps, valves, switches

### Stat (Big Number)
**Best for**: Single value display
**Use for**: Counts, percentages, status

### Table
**Best for**: Multiple related values
**Use for**: Actuator overviews, comparisons

---

## 🚨 Setting Up Alerts

### Email Notifications

1. **Grafana** → Alerting → Contact points
2. **Add contact point**:
   - Name: Email Alerts
   - Integration: Email
   - Addresses: your-email@example.com
3. **Test** → Save

### Slack Notifications

1. **Create Slack webhook** in Slack workspace
2. **Grafana** → Alerting → Contact points
3. **Add contact point**:
   - Name: Slack Alerts
   - Integration: Slack
   - Webhook URL: (paste your webhook)
4. **Test** → Save

### Create Alert Rule

1. **Edit panel** → Alert tab
2. **Create alert rule**:
   ```
   Name: High Temperature Alert
   Evaluate every: 1m
   For: 5m
   
   Conditions:
   WHEN avg() OF query(A, 1m, now) 
   IS ABOVE 150
   ```
3. **Add notification**: Select contact point
4. **Save**

---

## 🎓 Best Practices

### 1. Dashboard Organization
- Group related panels by process stage
- Use consistent naming conventions
- Add descriptions to panels

### 2. Performance
- Limit queries to necessary time ranges
- Use aggregation (mean, max, min) instead of raw data
- Set appropriate refresh intervals

### 3. Monitoring
- Set up alerts for critical sensors
- Monitor dashboard refresh performance
- Review query performance regularly

### 4. Maintenance
- Export dashboard JSON regularly (backup)
- Document custom changes
- Version control dashboard configurations

---

## 📁 Dashboard Files

### Current Dashboard
- **File**: `grafana/swat_comprehensive_dashboard_FINAL.json`
- **Panels**: 18
- **Sensors**: 78+
- **Version**: 1.0

### Backup Your Dashboard

1. **Dashboard** → Settings (⚙️) → JSON Model
2. **Copy** entire JSON
3. **Save** to file locally
4. **Commit** to Git (optional)

---

## 🐛 Troubleshooting Grafana

### Dashboard Shows "No Data"

**Check:**
1. Time range includes data period
2. Data source connected
3. InfluxDB has data
4. Field names match (spaces vs underscores)

**Fix:**
```bash
# Verify data exists
docker exec -it influxdb influx -database scada_data -execute "SELECT * FROM sensor_data LIMIT 5"
```

### Panels Show Errors

**Common causes:**
- Wrong data source UID
- Incorrect field names
- Time filter issues

**Fix**: Edit panel → Check query syntax

### Dashboard Won't Save

**Causes:**
- Permission issues
- JSON syntax errors

**Fix**: Export JSON, fix syntax, re-import

---

## 📞 Support

For dashboard issues:
1. Check panel query in edit mode
2. Review Grafana logs: `docker logs grafana`
3. Verify data source configuration
4. Check InfluxDB connectivity

---

**Last Updated**: November 2025
