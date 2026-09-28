Your are a senior python engineer

Your task is to first explore entitybase-sse/ (ignore the frontend/ subdir)

Then: Design a **reusable Kafka → SSE gateway** rather than a project tied to a specific domain written in Python and use uv to handle dependencies.

The service must allow HTTP clients to subscribe to Kafka topics via **Server-Sent Events (SSE)** and receive events streamed in real time.

The gateway should act as a lightweight streaming API on top of Kafka.

---

SUBSCRIPTION ENDPOINT

GET /streams/{topic}

Streams events from a Kafka topic using SSE.

Optional query parameters:

offset
Start streaming from a specific Kafka offset.

since
Start streaming from the first event whose timestamp is greater than or equal to the provided ISO8601 timestamp.

limit
Maximum number of events to deliver before closing the connection.

---

EXAMPLE REQUESTS

/streams/entity-events

/streams/entity-events?offset=12345

/streams/entity-events?since=2026-03-05T12:00:00Z

/streams/entity-events?offset=500&limit=100

/streams/entity-events?since=2026-03-05T12:00:00Z&limit=200

---

OFFSET AND TIME HANDLING

When a client connects:

If offset is provided:

* seek the Kafka consumer to that offset

If since is provided:

* use Kafka timestamp lookup to determine the offset
* seek to the first offset with timestamp >= since

If both offset and since are provided:

* offset takes precedence

If neither is provided:

* start streaming from the latest offset

---

LIMIT HANDLING

If limit is specified:

* stream at most `limit` events
* once the limit is reached, gracefully close the SSE connection

If limit is not specified:

* keep streaming indefinitely until the client disconnects

---

METADATA ENDPOINTS

GET /topics

Returns a list of Kafka topics available for streaming.

GET /health

Returns service health status and Kafka connectivity.

Example response:

{
"status": "ok",
"kafka": "connected"
}

---

SHARED KAFKA CONSUMER + FANOUT ARCHITECTURE

The system MUST NOT create one Kafka consumer per SSE client.

Instead implement a **fan-out architecture**:

* one Kafka consumer per topic
* events distributed to all subscribed SSE clients

Architecture:

KafkaConsumerService
↓
EventRouter
↓
StreamManager
↓
fanout queues
↓
SSEBroadcaster
↓
SSE Clients

Responsibilities:

KafkaConsumerService

* consumes Kafka topics
* validates events
* forwards events to EventRouter

EventRouter

* routes events to subscribed topic streams

StreamManager

* maintains client subscription registry
* performs event fanout to clients

---

CLIENT STREAM MANAGEMENT

The service must support **many concurrent SSE clients per topic**.

Each client must have:

* an independent asyncio.Queue
* bounded queue size
* isolation from other clients

Example:

asyncio.Queue(maxsize=100)

---

BACKPRESSURE PROTECTION

If a client consumes events too slowly:

* drop the oldest event in the queue
* log a warning
* continue streaming

Slow clients must never block:

* Kafka consumption
* other SSE clients

---

KAFKA EVENT MODEL

All Kafka messages must validate against this schema: entitybase-schemas/events/entity_change/1.0.0/schema.yaml - validate in tests only

---

SSE OUTPUT FORMAT

Each event must be emitted as:

event: message
id: <event_id>
data: <JSON serialized event>

Example:

event: message
id: 82c5a9
data: {"event_type":"entity_update","payload":{...}}

validate the output in tests using entitybase-schemas/events/sse/entity_change/1.0.0/schema.yaml

---

SCALABILITY GOAL

The architecture must support:

* thousands of concurrent SSE clients
* minimal Kafka consumers
* efficient in-memory fanout
* non-blocking event distribution

---

DESIGN CONSTRAINTS

* support multiple topics
* support many clients per topic
* no blocking operations in streaming path
* Kafka consumption must run independently of SSE clients
* SSE connections must close cleanly on disconnect
* event validation must use Pydantic models
* use confluent-kafka
* use litestar api framework


