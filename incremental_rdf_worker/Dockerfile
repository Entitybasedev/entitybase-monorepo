# syntax=docker/dockerfile:1
FROM python:3.13-slim

WORKDIR /app

# git is needed to install the backend's git dependency
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY entitybase-backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt

# The worker shares the backend package (data layer, settings) for now
COPY entitybase-backend /app/entitybase-backend
COPY incremental_rdf_worker /app/incremental_rdf_worker

ENV PYTHONPATH=/app/incremental_rdf_worker/src:/app/entitybase-backend/src

CMD ["python", "-m", "incremental_rdf_worker"]
