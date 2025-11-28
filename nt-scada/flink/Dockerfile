# Flink Job Builder Dockerfile
FROM flink:1.17.1-scala_2.12-java11

# Switch to root user to install packages
USER root

# Install Python dependencies and development tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create python symlink for Flink compatibility
RUN ln -s /usr/bin/python3 /usr/bin/python

# Upgrade pip first (separate layer for better caching)
RUN pip3 install --upgrade pip

# Copy requirements first for better Docker layer caching
COPY requirements.txt /opt/flink/requirements.txt

# Install Python packages with optimizations
RUN pip3 install --no-cache-dir \
    --prefer-binary \
    --only-binary=:all: \
    -r /opt/flink/requirements.txt || \
    pip3 install --no-cache-dir -r /opt/flink/requirements.txt

# Copy job files (separate layer)
COPY jobs/ /opt/flink/jobs/

# Make Python scripts executable
RUN chmod +x /opt/flink/jobs/*.py

# Switch back to flink user for Flink operations
USER flink

# Set working directory
WORKDIR /opt/flink

# Expose job submission port
EXPOSE 8081

# Add Python path for Flink
ENV PYTHONPATH=/opt/flink/jobs:$PYTHONPATH
ENV FLINK_ROOT=/opt/flink

# Default command for Flink JobManager
CMD ["jobmanager"]
