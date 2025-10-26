FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy consumer script
COPY to_influx.py .

# Run the consumer
CMD ["python", "to_influx.py"]
