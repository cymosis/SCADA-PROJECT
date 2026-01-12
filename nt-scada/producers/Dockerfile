FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy producer scripts
COPY sensor_producer.py .
COPY actuator_producer.py .

# Default to sensor producer (can be overridden)
ENV PRODUCER_TYPE=sensor

# Run the appropriate producer based on environment variable
CMD if [ "$PRODUCER_TYPE" = "sensor" ]; then \
    python sensor_producer.py; \
    else \
    python actuator_producer.py; \
    fi
