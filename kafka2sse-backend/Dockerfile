FROM python:3.13-slim AS builder
WORKDIR /app

# Build stage: Install compiler and dev headers for confluent-kafka
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "fastapi>=0.115,<1.0" \
    "httpx>=0.27,<1.0" \
    "sse-starlette>=2.0,<3.0" \
    "aiokafka>=0.10,<1.0" \
    "confluent-kafka>=2.3,<3.0" \
    "pydantic>=2.5,<3.0" \
    "pyyaml>=6.0,<7.0" \
    "uvicorn[standard]>=0.25,<1.0" \
    "valkey>=0.15"

FROM python:3.13-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    librdkafka1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src ./src

ARG VERSION=v2026.4.8
ENV VERSION=$VERSION
ENV PYTHONPATH=/app
ENV KAFKA_BROKERS=localhost:9092
ENV VALKEY_HOST=localhost
ENV KAFKA_CLIENT_QUEUE_SIZE=100
ENV HOST=0.0.0.0
ENV PORT=8888

EXPOSE 8888

CMD ["python", "-m", "src.main"]
