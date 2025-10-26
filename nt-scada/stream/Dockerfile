FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Flink job
COPY flink_job.py .
COPY stream_processor.py .

# Run the stream processor
CMD ["python", "stream_processor.py"]
