FROM flink:1.17.1-scala_2.12

# Install Python & pip
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    pip3 install --no-cache-dir requests && \
    apt-get clean

# Copy jobs directory
COPY jobs /opt/flink/jobs

