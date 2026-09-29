// Minimal mock of the Entitybase v1 API for running e2e-ui tests
// without docker or the real backend. Shape-matches the real API:
//   POST /v1/users                      -> {user_id}
//   POST /v1/entities/items             -> {success, data:{entity_id, revision_id}}
//   PUT  /v1/entities/{id}/labels/{l}   -> {hash}
//   POST /v1/entities/{id}/statements   -> {success, data:claim}
//   GET  /v1/entities/{id}              -> {id, rev_id, data:{labels, statements, ...}}
//   GET  /health                        -> 200 "ok"
import http from 'node:http'

const db = new Map()
const statementsByHash = new Map()
const events = []
let counter = 1000

function recordEvent(entityId, type) {
  events.push({
    id: entityId,
    rev: 1,
    type,
    from_rev: 0,
    at: new Date().toISOString(),
    summary: 'mock event',
    user: '90001',
  })
}

const server = http.createServer((req, res) => {
  let body = ''
  req.on('data', (c) => (body += c))
  req.on('end', () => {
    const json = (code, obj) => {
      res.writeHead(code, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify(obj))
    }
    const url = new URL(req.url, 'http://x')
    const jsonBody = body ? JSON.parse(body) : {}

    if (url.pathname === '/health') {
      res.writeHead(200)
      return res.end('ok')
    }
    if (req.method === 'POST' && url.pathname === '/v1/users') {
      return json(200, { user_id: jsonBody.user_id })
    }
    if (url.pathname === '/__mock/events') {
      const since = Number(url.searchParams.get('since') ?? -1)
      return json(200, { events: events.slice(since + 1), last: events.length - 1 })
    }
    if (url.pathname === '/__mock/produce' && req.method === 'POST') {
      const event = jsonBody
      if (!event.id || !event.rev || !event.type) {
        return json(400, { message: 'event needs id, rev and type' })
      }
      events.push(event)
      return json(200, { accepted: true, last: events.length - 1 })
    }
    if (req.method === 'POST' && url.pathname === '/v1/entities/items') {
      const id = `Q${counter++}`
      db.set(id, { id, type: 'item', labels: {}, hashes: { statements: [] } })
      recordEvent(id, 'creation')
      return json(200, { success: true, data: { entity_id: id, revision_id: 1 } })
    }
    if (req.method === 'POST' && url.pathname === '/v1/entities/properties') {
      const id = `P${counter++}`
      db.set(id, { id, type: 'property', labels: {}, hashes: { statements: [] } })
      recordEvent(id, 'creation')
      return json(200, { success: true, data: { entity_id: id, revision_id: 1 } })
    }
    if (req.method === 'POST' && url.pathname === '/v1/entities/lexemes') {
      const id = `L${counter++}`
      const body = jsonBody
      db.set(id, {
        id,
        type: 'lexeme',
        lemmas: body.lemmas ?? {},
        labels: {},
        hashes: { statements: [] },
      })
      recordEvent(id, 'creation')
      return json(200, { id, rev_id: 1, data: { revision: {} } })
    }
    const sm = url.pathname.match(/^\/v1\/statements\/(\d+)$/)
    if (req.method === 'GET' && sm) {
      const hash = Number(sm[1])
      const claim = statementsByHash.get(hash)
      if (!claim) return json(404, { message: 'statement not found' })
      return json(200, { schema: '1.0', hash, statement: claim })
    }
    const m = url.pathname.match(/^\/v1\/entities\/([^/]+)(\/.*)?$/)
    if (m) {
      const id = m[1]
      const item = db.get(id)
      if (!item) return json(404, { message: 'not found' })
      const rest = m[2] || ''
      if (rest === '/statements' && req.method === 'POST') {
        const claim = jsonBody.claim
        claim.id = claim.id ?? `S${counter++}`
        const hash = counter++
        statementsByHash.set(hash, claim)
        item.hashes.statements.push(hash)
        return json(200, { success: true, data: claim })
      }
      const lm = rest.match(/^\/labels\/(\w+)$/)
      if (lm) {
        const lang = lm[1]
        if (req.method === 'PUT' || req.method === 'POST') {
          item.labels[lang] = { language: lang, value: jsonBody.value }
          return json(200, { hash: 'mock' })
        }
        return json(200, { value: item.labels[lang]?.value ?? '' })
      }
      if (req.method === 'GET') return json(200, { id, rev_id: 1, data: item })
    }
    json(404, { message: `no route: ${req.method} ${url.pathname}` })
  })
})

server.listen(8083, () => console.log('mock entitybase api on :8083'))
