FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy producer script
COPY normal_data.py .

# Run the normal producer
CMD ["python", "normal_data.py"]
