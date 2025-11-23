FROM python:3.11-slim

WORKDIR /app


# Copy application files
COPY predict_anomaly.py /app/
COPY requirements.txt /app/

# Models will be mounted via volume at runtime

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run script automatically
CMD ["python", "predict_anomaly.py"]
