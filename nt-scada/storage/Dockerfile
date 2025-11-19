FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy consumers
COPY to_influx.py .
COPY attack_influx.py .

# Default – normal consumer
CMD ["python", "to_influx.py"]

