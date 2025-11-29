FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy producer scripts
COPY attack.py .

# Default environment variables (can be overridden at runtime)
ENV PRODUCER_TYPE=attack

# Run the attack producer
CMD ["python", "attack.py"]
