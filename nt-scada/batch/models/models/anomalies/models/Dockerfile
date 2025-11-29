FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy batch script
COPY train_model.py .

# Create directories for models and reports
RUN mkdir -p /app/models /app/reports

# Run batch job (can be scheduled with cron or run manually)
CMD ["python", "train_model.py"]
