# syntax=docker/dockerfile:1
FROM python:3.13-slim

WORKDIR /app

# git is needed to install the backend's git dependency, wget for the healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends git wget \
    && rm -rf /var/lib/apt/lists/*

COPY entitybase-backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt

# The worker shares the backend package (data layer, settings) for now
COPY entitybase-backend /app/entitybase-backend
COPY general_stats_worker /app/general_stats_worker

ENV PYTHONPATH=/app/general_stats_worker/src:/app/entitybase-backend/src

CMD ["python", "-m", "general_stats_worker"]
