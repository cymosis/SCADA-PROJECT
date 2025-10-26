@echo off
echo ============================================================
echo NT-SCADA Startup Script
echo ============================================================
echo.

echo Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not running!
    echo Please install Docker Desktop and try again.
    pause
    exit /b 1
)

echo Docker is running.
echo.

echo Starting NT-SCADA services...
docker-compose up -d

echo.
echo ============================================================
echo NT-SCADA Services Started!
echo ============================================================
echo.
echo Web Interfaces:
echo   - Grafana:  http://localhost:3000 (admin/admin)
echo   - Flink:    http://localhost:8081
echo   - InfluxDB: http://localhost:8086 (admin/adminpass123)
echo.
echo Kafka Broker: localhost:9092
echo.
echo To view logs: docker-compose logs -f
echo To stop:      docker-compose down
echo.
echo Wait 2-3 minutes for data to start flowing...
echo ============================================================
pause
