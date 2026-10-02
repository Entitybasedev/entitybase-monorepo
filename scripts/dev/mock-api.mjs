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
const recentChanges = []
let counter = 1000
let changeSeq = 0

function recordChange(entityId, changeType, summary, userId = 90001) {
  recentChanges.push({
    id: ++changeSeq,
    created_at: new Date().toISOString(),
    user_id: userId,
    activity_type: changeType === 'entity_create' ? 'entity_create' : 'entity_edit',
    change_type: changeType,
    entity_id: entityId,
    revision_id: 1,
    edit_summary: summary,
  })
}

function recordRevision(entityId, summary) {
  const item = db.get(entityId)
  if (!item) return
  item.revisions ||= []
  const rev = {
    revision_id: item.revisions.length + 1,
    created_at: new Date().toISOString(),
    user_id: 90001,
    summary,
  }
  item.revisions.push(rev)
  item.rev_id = rev.revision_id
}

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
    if (req.method === 'POST' && url.pathname === '/v1/auth/register') {
      return json(200, { token: 'mock-token', user_id: 90001, username: jsonBody.username })
    }
    if (req.method === 'POST' && url.pathname === '/v1/auth/login') {
      return json(200, { token: 'mock-token', user_id: 90001, username: jsonBody.username })
    }
    if (req.method === 'GET' && url.pathname === '/v1/users') {
      const limit = Number(url.searchParams.get('limit') ?? 10)
      const offset = Number(url.searchParams.get('offset') ?? 0)
      // The import user (0) plus any registered users; mock keeps a static set
      const users = [{ user_id: 0, username: 'import', created_at: '', last_activity: '' }]
      const page = users.slice(offset, offset + limit)
      return json(200, { users: page, count: page.length })
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
      recordRevision(id, 'Created item')
      recordChange(id, 'entity_create', 'Created via entitybase-frontend')
      return json(200, { success: true, data: { entity_id: id, revision_id: 1 } })
    }
    if (req.method === 'POST' && url.pathname === '/v1/entities/properties') {
      const id = `P${counter++}`
      db.set(id, { id, type: 'property', labels: {}, hashes: { statements: [] } })
      recordEvent(id, 'creation')
      recordRevision(id, 'Created property')
      recordChange(id, 'entity_create', 'Created via entitybase-frontend')
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
      recordRevision(id, 'Created lexeme')
      recordChange(id, 'entity_create', 'Created via entitybase-frontend')
      return json(200, { id, rev_id: 1, data: { revision: {} } })
    }
    if (req.method === 'GET' && url.pathname === '/v1/recentchanges') {
      let rows = recentChanges
      if (url.searchParams.get('exclude_imports') === 'true') {
        rows = rows.filter((row) => row.change_type !== 'entity_import')
      }
      const limit = Number(url.searchParams.get('limit') ?? 50)
      const offset = Number(url.searchParams.get('offset') ?? 0)
      const ordered = [...rows].sort((a, b) => b.id - a.id)
      return json(200, ordered.slice(offset, offset + limit))
    }
    if (req.method === 'GET' && url.pathname === '/v1/entities') {
      const type = url.searchParams.get('entity_type') ?? ''
      const prefix = { item: 'Q', property: 'P', lexeme: 'L', entityschema: 'E' }[type] ?? ''
      const ids = [...db.keys()].filter((id) => id.startsWith(prefix)).sort().reverse()
      const limit = Number(url.searchParams.get('limit') ?? 100)
      const offset = Number(url.searchParams.get('offset') ?? 0)
      const page = ids
        .slice(offset, offset + limit)
        .map((id) => ({ entity_id: id, head_revision_id: db.get(id).rev_id ?? 1 }))
      return json(200, { entities: page, count: page.length })
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
        recordRevision(id, 'Add statement')
        recordChange(id, 'statement_add', 'Created via entitybase-frontend')
        return json(200, { success: true, data: claim })
      }
      const lm = rest.match(/^\/labels\/(\w+)$/)
      if (lm) {
        const lang = lm[1]
        if (req.method === 'PUT' || req.method === 'POST') {
          item.labels[lang] = { language: lang, value: jsonBody.value }
          recordRevision(id, 'Set label')
          recordChange(id, 'label_update', 'Created via entitybase-frontend')
          return json(200, { hash: 'mock' })
        }
        return json(200, { value: item.labels[lang]?.value ?? '' })
      }
      const dm = rest.match(/^\/descriptions\/(\w+)$/)
      if (dm) {
        const lang = dm[1]
        if (req.method === 'PUT' || req.method === 'POST') {
          item.descriptions ||= {}
          item.descriptions[lang] = { language: lang, value: jsonBody.value }
          recordRevision(id, 'Set description')
          recordChange(id, 'description_update', 'Created via entitybase-frontend')
          return json(200, { hash: 'mock' })
        }
        return json(200, { value: item.descriptions[lang]?.value ?? '' })
      }
      const am = rest.match(/^\/aliases\/(\w+)$/)
      if (am) {
        const lang = am[1]
        if (req.method === 'PUT') {
          const values = Array.isArray(jsonBody) ? jsonBody : []
          item.aliases ||= {}
          item.aliases[lang] = values
          recordRevision(id, 'Set aliases')
          recordChange(id, 'aliases_update', 'Created via entitybase-frontend')
          return json(200, { hashes: values.map(() => 'mock') })
        }
        return json(200, { aliases: item.aliases?.[lang] ?? [] })
      }
      if (rest === '/revisions' && req.method === 'GET') {
        return json(200, item.revisions ?? [])
      }
      const rm = rest.match(/^\/revision\/(\d+)$/)
      if (rm && req.method === 'GET') {
        return json(200, { id, rev_id: Number(rm[1]), data: item })
      }
      if (req.method === 'GET') return json(200, { id, rev_id: item.rev_id ?? 1, data: item })
    }
    json(404, { message: `no route: ${req.method} ${url.pathname}` })
  })
})

server.listen(8083, () => console.log('mock entitybase api on :8083'))
