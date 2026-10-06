#!/bin/bash
# Bring up QLever for Entitybase: build the (empty) index, serve it, then keep it
# current from the change stream.
#
# The order matters. `qlever update-wikidata` pushes updates at a running
# server over HTTP, so the server has to be answering before the updater
# starts, or the first batch fails.
set -euo pipefail

STREAM_URL="${QLEVER_STREAM_URL:-http://kafka2sse-backend:8888/v1/streams/incremental_rdf_diff?offset=0}"
STREAM_TOPIC="${QLEVER_STREAM_TOPIC:-incremental_rdf_diff}"
PORT="${QLEVER_PORT:-7019}"

echo "Building the index (empty; the data comes from the stream)"
qlever index

echo "Starting the SPARQL endpoint on port ${PORT}"
qlever start --port "${PORT}" &
SERVER_PID=$!

# Stop the server with this script, so `docker stop` does not leave it running.
trap 'kill "${SERVER_PID}" 2>/dev/null || true' TERM INT EXIT

# update-wikidata talks to the server over HTTP, so wait for it to answer
# rather than starting the updater against a socket that is not there yet.
echo "Waiting for the endpoint to answer"
for _ in $(seq 1 60); do
  if curl -sf "http://localhost:${PORT}/" > /dev/null; then
    break
  fi
  if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
    echo "The server exited before it became reachable" >&2
    exit 1
  fi
  sleep 1
done

if ! curl -sf "http://localhost:${PORT}/" > /dev/null; then
  echo "The endpoint did not become reachable on port ${PORT}" >&2
  exit 1
fi

# ?offset=0 in the URL is what makes this follow the stream from its start
# rather than from the latest message: kafka2sse assigns partition 0 at offset
# 0. It is left off the --since option on purpose, because kafka2sse falls back
# to "subscribe from latest" when a timestamp matches no offset, which would
# silently skip everything already in the topic.
echo "Following ${STREAM_TOPIC} from the start of the stream"
exec qlever update-wikidata "${STREAM_URL}" \
  --host-name localhost \
  --port "${PORT}" \
  --topic "${STREAM_TOPIC}" \
  --partition 0 \
  --log-level INFO