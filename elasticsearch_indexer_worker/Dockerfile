# syntax=docker/dockerfile:1
FROM python:3.13-slim

WORKDIR /app

COPY entitybase-backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt

# The worker shares the backend package (data layer, settings) for now
COPY entitybase-backend /app/entitybase-backend
COPY elasticsearch_indexer_worker /app/elasticsearch_indexer_worker

ENV PYTHONPATH=/app/elasticsearch_indexer_worker/src:/app/entitybase-backend/src

CMD ["python", "-m", "elasticsearch_indexer_worker"]
