// Mock of the kafka2sse stream backend for local e2e runs.
// Serves the same contract as the real backend (see kafka2sse-backend/src/main.py):
//   GET /v1/topics                    -> {topics: [...]}
//   GET /health                       -> {status, kafka, backend_type}
//   GET /v1/streams/entity_change     -> SSE stream of change events
// Events are polled from the entitybase mock API's /__mock/events endpoint,
// mirroring how the real stack flows entity changes through redpanda.
import http from 'node:http'

const MOCK_API = process.env.MOCK_API_URL || 'http://localhost:8083'

const TOPICS = ['entity_change']
let lastEventIndex = -1

const clients = new Set()

async function pollEvents() {
  try {
    const res = await fetch(`${MOCK_API}/__mock/events?since=${lastEventIndex}`)
    if (!res.ok) return
    const { events, last } = await res.json()
    for (const event of events) {
      const sseEvent = {
        event_type: 'entity_change',
        id: String(++lastEventIndex),
        data: event,
      }
      for (const client of clients) {
        client.write(`data: ${JSON.stringify(sseEvent)}\n\n`)
      }
    }
    lastEventIndex = Math.max(lastEventIndex, last)
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
    clients.add(res)
    req.on('close', () => clients.delete(res))
    return
  }
  json(404, { message: `no route: ${req.method} ${url.pathname}` })
})

// Poll the mock api for new entity events
setInterval(pollEvents, 300)

server.listen(8888, () => console.log('mock stream api on :8888'))
