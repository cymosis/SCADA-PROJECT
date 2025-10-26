@echo off
echo ============================================================
echo NT-SCADA Shutdown Script
echo ============================================================
echo.

echo Stopping NT-SCADA services...
docker-compose down

echo.
echo ============================================================
echo NT-SCADA Services Stopped!
echo ============================================================
echo.
echo To remove all data (volumes): docker-compose down -v
echo To restart: docker-compose up -d
echo.
pause
