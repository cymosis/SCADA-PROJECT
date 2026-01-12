FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for ML libraries
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir \
    scikit-learn==1.3.2 \
    joblib==1.3.2 \
    numpy==1.26.2

# Copy all Python files
COPY *.py .

# Create models directory (will be mounted from host)
RUN mkdir -p /app/models

# Run the ML stream processor
CMD ["python", "stream_processor_ml.py"]