FROM python:3.11-slim

WORKDIR /app

# Install build dependencies for numpy/pandas and PostgreSQL client libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory
RUN mkdir -p /app/data

EXPOSE 7001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7001"]

