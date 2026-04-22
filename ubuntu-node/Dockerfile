FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Install minimal useful tools for network exploration
RUN apt-get update && apt-get install -y \
    iputils-ping \
    curl \
    wget \
    net-tools \
    iproute2 \
    dnsutils \
    python3 \
    vim \
    && rm -rf /var/lib/apt/lists/*

COPY DoS.py /DoS.py

# Keep the container running
CMD ["sleep", "infinity"]
