#!/bin/bash

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     NT-SCADA Production System Startup Script              ║"
echo "╚════════════════════════════════════════════════════════════╝"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Docker
echo -e "${BLUE}[*] Checking Docker installation...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[✗] Docker is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}[✓] Docker is installed${NC}"

# Check Docker Compose
echo -e "${BLUE}[*] Checking Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}[✗] Docker Compose is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}[✓] Docker Compose is installed${NC}"

# Check docker-compose.yml
echo -e "${BLUE}[*] Checking docker-compose.yml...${NC}"
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}[✗] docker-compose.yml not found${NC}"
    exit 1
fi
echo -e "${GREEN}[✓] docker-compose.yml found${NC}"

# Check requirements.txt
echo -e "${BLUE}[*] Checking requirements.txt...${NC}"
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}[✗] requirements.txt not found${NC}"
    exit 1
fi
echo -e "${GREEN}[✓] requirements.txt found${NC}"

echo ""
echo -e "${BLUE}[*] Starting NT-SCADA Production System...${NC}"
echo ""

# Start services
echo -e "${YELLOW}[*] Building and starting services...${NC}"
docker-compose up -d

# Wait for services to be healthy
echo ""
echo -e "${YELLOW}[*] Waiting for services to initialize (60 seconds)...${NC}"
sleep 10

# Check service health
echo ""
echo -e "${BLUE}[*] Checking service health...${NC}"

SERVICES=("zookeeper" "kafka" "influxdb" "mlflow" "grafana")

for service in "${SERVICES[@]}"; do
    attempt=0
    max_attempts=12
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose ps | grep -q "$service.*Up"; then
            echo -e "${GREEN}[✓] $service is running${NC}"
            break
        else
            attempt=$((attempt + 1))
            if [ $attempt -lt $max_attempts ]; then
                echo -e "${YELLOW}[*] Waiting for $service... ($attempt/$max_attempts)${NC}"
                sleep 5
            fi
        fi
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo -e "${RED}[✗] $service failed to start${NC}"
    fi
done

echo ""
echo -e "${BLUE}[*] Service Status:${NC}"
docker-compose ps

echo ""
echo -e "${BLUE}[*] Starting data producers...${NC}"
docker-compose up -d sensor-producer actuator-producer

echo ""
echo -e "${BLUE}[*] Waiting for producers...${NC}"
sleep 5

echo -e "${GREEN}[✓] Producers started${NC}"

echo ""
echo -e "${BLUE}[*] Starting batch analytics...${NC}"
docker-compose up -d batch-analytics

echo ""
echo -e "${BLUE}[*] Starting stream processor...${NC}"
docker-compose up -d stream-processor

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║           NT-SCADA Started Successfully! 🚀                ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║                   Access Points:                            ║"
echo "║                                                             ║"
echo "║   Grafana (Dashboards):                                    ║"
echo "║   → http://localhost:3000                                  ║"
echo "║   → Credentials: admin / admin                             ║"
echo "║                                                             ║"
echo "║   MLflow (Model Registry):                                 ║"
echo "║   → http://localhost:5000                                  ║"
echo "║                                                             ║"
echo "║   InfluxDB (Time-Series Data):                             ║"
echo "║   → http://localhost:8086                                  ║"
echo "║   → Credentials: admin / adminpass123                      ║"
echo "║                                                             ║"
echo "║   Kafka Broker:                                            ║"
echo "║   → localhost:9092 (external)                              ║"
echo "║   → kafka:29092 (internal)                                 ║"
echo "║                                                             ║"
echo "║   Flink Dashboard (Optional):                              ║"
echo "║   → http://localhost:8081                                  ║"
echo "║                                                             ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║                    Useful Commands:                         ║"
echo "║                                                             ║"
echo "║   View all logs:                                           ║"
echo "║   $ docker-compose logs -f                                 ║"
echo "║                                                             ║"
echo "║   View specific service logs:                              ║"
echo "║   $ docker-compose logs -f batch-analytics                 ║"
echo "║   $ docker-compose logs -f stream-processor                ║"
echo "║                                                             ║"
echo "║   Stop all services:                                       ║"
echo "║   $ docker-compose down                                    ║"
echo "║                                                             ║"
echo "║   View service status:                                     ║"
echo "║   $ docker-compose ps                                      ║"
echo "║                                                             ║"
echo "║   Check Kafka topics:                                      ║"
echo "║   $ docker-compose exec kafka kafka-topics --list \\       ║"
echo "║     --bootstrap-server kafka:29092                         ║"
echo "║                                                             ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║              Documentation:                                 ║"
echo "║                                                             ║"
echo "║   Complete Guide:                                          ║"
echo "║   → PRODUCTION_GUIDE.md                                    ║"
echo "║                                                             ║"
echo "║   Implementation Details:                                  ║"
echo "║   → IMPLEMENTATION_SUMMARY.md                              ║"
echo "║                                                             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}System is ready!${NC}"
echo ""
