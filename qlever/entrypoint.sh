#!/bin/bash
# Bring up QLever for Entitybase: build the (empty) index, serve it, then keep it
# current from the change stream.
#
# The order matters. `qlever update-wikidata` pushes updates at a running server
# over HTTP, so the server has to be answering before the updater starts, or the
# first batch fails.
set -euo pipefail

STREAM_URL="${QLEVER_STREAM_URL:-http://kafka2sse-backend:8888/v1/streams/incremental_rdf_diff?offset=0}"
STREAM_TOPIC="${QLEVER_STREAM_TOPIC:-incremental_rdf_diff}"
PORT="${QLEVER_PORT:-7019}"

# qlever index insists on being given --name and --input-files, so it is driven
# from here rather than from the Qleverfile. --input-files has to be a pattern
# relative to the working directory: an absolute one is rejected outright.
#
# The index is built from an empty stream that only declares the prefixes.
# Everything else arrives over the change stream, which is the point: the graph
# holds what the stream has carried, not what happened to exist when the index
# was built.
#
# Only build it when it is not there. The index lives in a volume, so it
# survives a restart, and qlever index refuses to overwrite an existing one -
# which would turn every restart into a failure rather than a fast start.
if [ -f entitybase.index.spo ]; then
  echo "Reusing the index in the volume"
else
  echo "Building an empty index; the data comes from the stream"
  printf '@prefix wd: <http://www.wikidata.org/entity/> .\n' > seed.ttl
  qlever index \
    --name entitybase \
    --input-files seed.ttl \
    --cat-input-files 'cat seed.ttl' \
    --system native
fi

echo "Starting the SPARQL endpoint on port ${PORT}"
qlever start \
  --name entitybase \
  --description "Entitybase knowledge base, kept current from the change stream" \
  --host-name localhost \
  --port "${PORT}" \
  --access-token "${QLEVER_ACCESS_TOKEN:-entitybase}" \
  --system native \
  --run-in-foreground &
SERVER_PID=$!

# Stop the server with this script, so `docker stop` does not leave it behind.
trap 'kill "${SERVER_PID}" 2>/dev/null || true' TERM INT EXIT

# update-wikidata talks to the server over HTTP, so wait for it to answer
# rather than pointing the updater at a socket that is not there yet.
# /ping is the probe: the root path is 404 unless a query is supplied, so a
# plain GET / is not a liveness test.
echo "Waiting for the endpoint to answer"
for _ in $(seq 1 60); do
  if curl -sf "http://localhost:${PORT}/ping" > /dev/null; then
    break
  fi
  if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
    echo "The server exited before it became reachable" >&2
    exit 1
  fi
  sleep 1
done

if ! curl -sf "http://localhost:${PORT}/ping" > /dev/null; then
  echo "The endpoint did not become reachable on port ${PORT}" >&2
  exit 1
fi

# ?offset=0 in the URL is what makes kafka2sse hand over the topic from its
# start rather than from the latest message: it assigns partition 0 at offset
# 0. --offset 0 then stops qlever from trying to work out where to resume by
# querying the endpoint for its next offset, which on a fresh index has no such
# triple and comes back unparseable. Both are needed, and neither alone is.
#
# It is deliberately not the --since option: kafka2sse falls back to "subscribe
# from latest" when a timestamp matches no offset, which would silently skip
# everything already in the topic.
# --lag-seconds decides how stale a message may be before qlever stops waiting
# for a bigger batch and commits what it has. Its default is 1 second, and the
# check only runs while reading a message, so on a stream that is edited
# occasionally a batch can stay open indefinitely: the triples sit in memory,
# unpublished, and the endpoint answers queries against a graph that reads as
# empty. Nothing errors; there is simply nothing committed yet.
#
# A day is the useful line here, and it separates two cases rather than
# compromising between them. A message dated within the last day is a live edit
# and is committed at once, which is the whole point of following the stream. A
# message from a historical backlog is far older than that, so it does not trip
# the check and replay still batches as intended.
#
# --batch-size 1 is for the same reason, and it is what actually closes the gap.
# Every one of those conditions is evaluated while a message is in hand, so with
# a larger batch the last edit of a quiet afternoon is never committed: it waits
# for the next edit to arrive and trigger the check. An edit stream that is
# edited occasionally - which is what this is - would sit one edit behind
# indefinitely, with no error to say so. Committing each message as it is read
# makes the graph reflect the last edit, which is the whole point.
#
# It costs one update request per message. That is the right trade for following
# a change stream; importing a bulk dump would want a larger value, and would
# want --lag-seconds small with it.
echo "Following ${STREAM_TOPIC} from the start of the stream"
exec qlever update-wikidata "${STREAM_URL}" \
  --host-name localhost \
  --port "${PORT}" \
  --access-token "${QLEVER_ACCESS_TOKEN:-entitybase}" \
  --topic "${STREAM_TOPIC}" \
  --partition 0 \
  --offset 0 \
  --lag-seconds "${QLEVER_LAG_SECONDS:-86400}" \
  --batch-size "${QLEVER_BATCH_SIZE:-1}" \
  --log-level INFO