@echo off
REM NT-SCADA Automated Setup Script for Windows
REM This script automates the setup process for the NT-SCADA project

setlocal enabledelayedexpansion

echo ============================================================================
echo NT-SCADA Automated Setup Script for Windows
echo ============================================================================
echo.

REM Check Docker
echo Step 1: Checking Prerequisites
echo ----------------------------------------------------------------------------
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is not installed. Please install Docker Desktop first.
    echo Download from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo [OK] Docker is installed

where docker-compose >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker Compose is not installed.
    pause
    exit /b 1
)
echo [OK] Docker Compose is installed

REM Check if Docker daemon is running
docker info >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker daemon is not running. Please start Docker Desktop.
    pause
    exit /b 1
)
echo [OK] Docker daemon is running
echo.

REM Create project directories
echo Step 2: Creating Project Structure
echo ----------------------------------------------------------------------------
if not exist "telegraf" mkdir telegraf
if not exist "stream" mkdir stream
if not exist "producers" mkdir producers
if not exist "actuators" mkdir actuators
if not exist "models" mkdir models
if not exist "data" mkdir data
if not exist "data\swat" mkdir data\swat
if not exist "notebooks" mkdir notebooks
echo [OK] Project directories created
echo.

REM Stop any running containers
echo Step 3: Cleaning Up Previous Installations
echo ----------------------------------------------------------------------------
docker-compose ps | findstr "Up" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Stopping existing containers...
    docker-compose down
    echo [OK] Stopped existing containers
)
echo.

REM Start core infrastructure
echo Step 4: Starting Core Infrastructure
echo ----------------------------------------------------------------------------

echo Starting Zookeeper...
docker-compose up -d zookeeper
timeout /t 10 /nobreak >nul
echo [OK] Zookeeper started

echo Starting Kafka...
docker-compose up -d kafka
timeout /t 15 /nobreak >nul
echo [OK] Kafka started

echo Starting InfluxDB...
docker-compose up -d influxdb
timeout /t 5 /nobreak >nul
echo [OK] InfluxDB started

echo Starting Grafana...
docker-compose up -d grafana
timeout /t 5 /nobreak >nul
echo [OK] Grafana started

echo Starting Kafka UI...
docker-compose up -d kafka-ui
timeout /t 5 /nobreak >nul
echo [OK] Kafka UI started

echo [OK] Core infrastructure started successfully
echo.

REM Create Kafka topics
echo Step 5: Creating Kafka Topics
echo ----------------------------------------------------------------------------
echo Waiting for Kafka to be fully ready...
timeout /t 15 /nobreak >nul

echo Creating topics...
docker exec kafka kafka-topics --create --topic sensor-inputs --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists 2>nul
docker exec kafka kafka-topics --create --topic processed-data --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists 2>nul
docker exec kafka kafka-topics --create --topic anomalies --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists 2>nul
docker exec kafka kafka-topics --create --topic control-commands --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists 2>nul

echo Listing all topics:
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

echo [OK] Kafka topics created
echo.

REM Set up InfluxDB database
echo Step 6: Setting Up InfluxDB Database
echo ----------------------------------------------------------------------------
echo Creating scada_data database...
docker exec influxdb influx -execute "CREATE DATABASE scada_data" 2>nul

echo Verifying database creation...
docker exec influxdb influx -execute "SHOW DATABASES"

echo [OK] InfluxDB database created
echo.

REM Start Telegraf
echo Step 7: Starting Telegraf
echo ----------------------------------------------------------------------------
docker-compose up -d telegraf
timeout /t 5 /nobreak >nul
echo [OK] Telegraf started
echo.

REM Start processing services
echo Step 8: Starting Stream Processing Services
echo ----------------------------------------------------------------------------
echo Starting stream processor...
docker-compose up -d stream-processor
timeout /t 3 /nobreak >nul

echo Starting control processor...
docker-compose up -d control-processor
timeout /t 3 /nobreak >nul

echo Starting mock actuator...
docker-compose up -d mock-actuator
timeout /t 3 /nobreak >nul

echo [OK] Processing services started
echo.

REM Display service status
echo Step 9: Service Status
echo ----------------------------------------------------------------------------
docker-compose ps
echo.

REM Display access information
echo ============================================================================
echo Setup Complete! 🎉
echo ============================================================================
echo.
echo [OK] NT-SCADA system is now running!
echo.
echo Access the following interfaces:
echo.
echo   Kafka UI:        http://localhost:8080
echo   Grafana:         http://localhost:3000 (admin/admin)
echo   InfluxDB API:    http://localhost:8086
echo.
echo Next steps:
echo.
echo   1. Configure Grafana data source (see QUICK-START-GUIDE.md)
echo   2. Place SWaT dataset in data\swat\ directory
echo   3. Train ML models: cd models && python train_binary_model.py
echo   4. Start sensor producer: cd producers && python sensor_producer.py
echo.
echo View logs:
echo.
echo   docker-compose logs -f stream-processor
echo   docker-compose logs -f control-processor
echo   docker-compose logs -f mock-actuator
echo.
echo Stop all services:
echo.
echo   docker-compose down
echo.
echo [WARNING] Important: Add the SWaT dataset to data\swat\ before running the sensor producer
echo.

pause
