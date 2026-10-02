// Mock of the kafka2sse stream backend for local e2e runs.
// Serves the same contract as the real backend (see kafka2sse-backend/src/main.py):
//   GET /v1/topics                    -> {topics: [...]}
//   GET /health                       -> {status, kafka, backend_type}
//   GET /v1/streams/entity_change     -> SSE stream of change events
// Events are polled from the entitybase mock API's /__mock/events endpoint,
// mirroring how the real stack flows entity changes through redpanda.
import http from 'node:http'

// Mock ports live in the 90xx range so they never collide with the
// docker stack (80xx). Override with MOCK_API_PORT / MOCK_STREAM_PORT.
const API_PORT = Number(process.env.MOCK_API_PORT || 9083)
const STREAM_PORT = Number(process.env.MOCK_STREAM_PORT || 9088)

const MOCK_API = process.env.MOCK_API_URL || `http://localhost:${API_PORT}`

const TOPICS = ['entity_change']

// Full event history; each client replays from the start on connect
// (mirrors the real backend's offset=0 replay)
const eventLog = []
const clients = new Map() // res -> cursor into eventLog
let lastPolled = -1

function flush() {
  for (const [res, startCursor] of clients) {
    let i = startCursor
    while (i < eventLog.length) {
      const sseEvent = {
        event_type: 'entity_change',
        id: String(i),
        data: eventLog[i],
      }
      res.write(`data: ${JSON.stringify(sseEvent)}\n\n`)
      i++
    }
    clients.set(res, i)
  }
}

async function pollEvents() {
  try {
    const res = await fetch(`${MOCK_API}/__mock/events?since=${lastPolled}`)
    if (!res.ok) return
    const { events, last } = await res.json()
    eventLog.push(...events)
    lastPolled = Math.max(lastPolled, last)
    flush()
  } catch {
    // mock api not up yet; retry on next tick
  }
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x')
  const json = (code, obj) => {
    res.writeHead(code, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(obj))
  }

  if (url.pathname === '/health') {
    return json(200, { status: 'ok', kafka: 'connected', backend_type: 'mock' })
  }
  if (url.pathname === '/v1/topics') {
    return json(200, { topics: TOPICS })
  }
  if (url.pathname === '/v1/streams/entity_change') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    })
    res.write(': connected\n\n')
    clients.set(res, -1)
    flush()
    req.on('close', () => clients.delete(res))
    return
  }
  json(404, { message: `no route: ${req.method} ${url.pathname}` })
})

// Poll the mock api for new entity events
setInterval(pollEvents, 300)

server.listen(STREAM_PORT, () => console.log(`mock stream api on :${STREAM_PORT}`))
