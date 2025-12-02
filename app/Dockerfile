FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/data /app/config

# Copy application files
COPY collector.py .

# Make collector executable
RUN chmod +x collector.py

# Health check endpoint (we'll add a simple HTTP server later if needed)
# For now, check if process is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f collector.py || exit 1

# Run the collector
CMD ["python", "collector.py"]

