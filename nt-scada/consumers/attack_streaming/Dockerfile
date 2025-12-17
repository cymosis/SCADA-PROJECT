FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    kafka-python \
    influxdb-client

# Copy consumer script
COPY consumer_attack_streaming.py /app/consumer.py

# Run the consumer
CMD ["python", "-u", "consumer.py"]
