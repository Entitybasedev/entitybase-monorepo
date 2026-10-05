const BASE = import.meta.env.VITE_API_BASE || ''

import { authHeaders, token, userId as authUserId } from './auth.js'

function editHeaders() {
  const headers = {
    'Content-Type': 'application/json',
    'X-Edit-Summary': 'Created via entitybase-frontend',
  }
  // A bearer token identifies the user: the API derives X-User-ID from it and
  // rejects a client-sent X-User-ID that disagrees with the token (403), which
  // would lock the user out of editing. So send the token alone and let the
  // API fill in the user id. X-User-ID is only for the token-less case, where
  // auth is not configured on the server.
  if (token.value) return { ...headers, ...authHeaders() }
  if (authUserId.value) headers['X-User-ID'] = String(authUserId.value)
  return headers
}

function safeJsonParse(text) {
  // Quote integer literals >= 15 digits so int64 hashes survive JS parsing
  // (Number.MAX_SAFE_INTEGER is ~9e15; rounding makes them unusable).
  // The trailing delimiter is matched with a lookahead so it is not
  // consumed: otherwise every second hash in a list loses the delimiter it
  // needs as its leading match and gets rounded.
  return JSON.parse(text.replace(/([:,[]\s*)(\d{15,})(?=\s*[,\]}])/g, '$1"$2"'))
}

// The API reports failures as {"error","message"} or FastAPI's {"detail"},
// so pull the human-readable part out instead of showing the raw body. The
// status is kept on the error so callers can tell an auth failure from a
// validation one.
function failureMessage(body) {
  if (!body) return ''
  try {
    const parsed = JSON.parse(body)
    const detail = parsed?.detail
    if (typeof detail === 'string') return detail
    return parsed?.message ?? detail ?? body
  } catch {
    return body
  }
}

async function unwrap(res, what) {
  if (!res.ok) {
    const error = new Error(`${what} failed: ${res.status} ${failureMessage(await res.text())}`)
    error.status = res.status
    throw error
  }
  return safeJsonParse(await res.text())
}

// Machine-readable views of an entity, for linking straight to the data:
// the current revision as Wikibase-style JSON, and as RDF/Turtle.
export function entityJsonUrl(entityId) {
  return `${BASE}/v1/entities/${encodeURIComponent(entityId)}.json`
}

export function entityRdfUrl(entityId) {
  return `${BASE}/v1/entities/${encodeURIComponent(entityId)}.ttl`
}

export async function postItem(_body) {
  const res = await fetch(`${BASE}/v1/entities/items`, {
    method: 'POST',
    headers: editHeaders(),
  })
  const json = await unwrap(res, 'POST item')
  return json.data?.entity_id ?? json.entity_id ?? json.id
}

export async function postProperty(body) {
  const res = await fetch(`${BASE}/v1/entities/properties`, {
    method: 'POST',
    headers: editHeaders(),
    body: JSON.stringify(body ?? { type: 'property' }),
  })
  const json = await unwrap(res, 'POST property')
  return json.data?.entity_id ?? json.entity_id ?? json.id
}

// The property types a property may be created with; drives the type picker
// and the per-type value inputs, so new types need no frontend change.
export async function getPropertyDatatypes() {
  const res = await fetch(`${BASE}/v1/property-datatypes`)
  if (res.status === 404) return []
  const json = await unwrap(res, 'GET property datatypes')
  return json.datatypes ?? []
}

export async function postLexeme(body) {
  const res = await fetch(`${BASE}/v1/entities/lexemes`, {
    method: 'POST',
    headers: editHeaders(),
    body: JSON.stringify(body),
  })
  const json = await unwrap(res, 'POST lexeme')
  return json.data?.entity_id ?? json.entity_id ?? json.id
}

export async function putLabel(entityId, language, value) {
  const res = await fetch(
    `${BASE}/v1/entities/${encodeURIComponent(entityId)}/labels/${encodeURIComponent(language)}`,
    { method: 'PUT', headers: editHeaders(), body: JSON.stringify({ language, value }) }
  )
  return unwrap(res, `PUT label ${entityId}`)
}

export async function putDescription(entityId, language, value) {
  const res = await fetch(
    `${BASE}/v1/entities/${encodeURIComponent(entityId)}/descriptions/${encodeURIComponent(language)}`,
    { method: 'PUT', headers: editHeaders(), body: JSON.stringify({ language, value }) }
  )
  return unwrap(res, `PUT description ${entityId}`)
}

export async function putAliases(entityId, language, values) {
  const res = await fetch(
    `${BASE}/v1/entities/${encodeURIComponent(entityId)}/aliases/${encodeURIComponent(language)}`,
    { method: 'PUT', headers: editHeaders(), body: JSON.stringify(values) }
  )
  return unwrap(res, `PUT aliases ${entityId}`)
}

export async function deleteStatement(entityId, statementHash) {
  const res = await fetch(
    `${BASE}/v1/entities/${encodeURIComponent(entityId)}/statements/${encodeURIComponent(statementHash)}`,
    { method: 'DELETE', headers: editHeaders() }
  )
  return unwrap(res, `DELETE statement ${entityId}/${statementHash}`)
}

export async function postStatement(entityId, body) {
  const res = await fetch(
    `${BASE}/v1/entities/${encodeURIComponent(entityId)}/statements`,
    { method: 'POST', headers: editHeaders(), body: JSON.stringify(body) }
  )
  return unwrap(res, `POST statement ${entityId}`)
}

export async function getItem(entityId) {
  const res = await fetch(`${BASE}/v1/entities/${encodeURIComponent(entityId)}`)
  return unwrap(res, `GET item ${entityId}`)
}

export async function getLabel(entityId, language) {
  const res = await fetch(
    `${BASE}/v1/entities/${encodeURIComponent(entityId)}/labels/${encodeURIComponent(language)}`
  )
  if (res.status === 404) return null
  const json = await unwrap(res, `GET label ${entityId}/${language}`)
  return json.value ?? null
}

export async function getDescription(entityId, language) {
  const res = await fetch(
    `${BASE}/v1/entities/${encodeURIComponent(entityId)}/descriptions/${encodeURIComponent(language)}`
  )
  if (res.status === 404) return null
  const json = await unwrap(res, `GET description ${entityId}/${language}`)
  return json.value ?? null
}

export async function getAliases(entityId, language) {
  const res = await fetch(
    `${BASE}/v1/entities/${encodeURIComponent(entityId)}/aliases/${encodeURIComponent(language)}`
  )
  if (res.status === 404) return []
  const json = await unwrap(res, `GET aliases ${entityId}/${language}`)
  return json.aliases ?? []
}

export async function getLexemeForms(entityId) {
  const res = await fetch(
    `${BASE}/v1/entities/lexemes/${encodeURIComponent(entityId)}/forms`
  )
  if (res.status === 404) return []
  const json = await unwrap(res, `GET forms ${entityId}`)
  return json.forms ?? []
}

export async function getLexemeSenses(entityId) {
  const res = await fetch(
    `${BASE}/v1/entities/lexemes/${encodeURIComponent(entityId)}/senses`
  )
  if (res.status === 404) return []
  const json = await unwrap(res, `GET senses ${entityId}`)
  return json.senses ?? []
}

export async function postLexemeForm(entityId, body) {
  const res = await fetch(
    `${BASE}/v1/entities/lexemes/${encodeURIComponent(entityId)}/forms`,
    { method: 'POST', headers: editHeaders(), body: JSON.stringify(body) }
  )
  const json = await unwrap(res, `POST form ${entityId}`)
  return json.data?.entity_id ?? json.entity_id ?? json.id
}

export async function postLexemeSense(entityId, body) {
  const res = await fetch(
    `${BASE}/v1/entities/lexemes/${encodeURIComponent(entityId)}/senses`,
    { method: 'POST', headers: editHeaders(), body: JSON.stringify(body) }
  )
  const json = await unwrap(res, `POST sense ${entityId}`)
  return json.data?.entity_id ?? json.entity_id ?? json.id
}

export async function getEntityTerms(entityId, language) {
  const res = await fetch(
    `${BASE}/v1/entities/${encodeURIComponent(entityId)}/terms/${encodeURIComponent(language)}`
  )
  if (res.status === 404) return { language, label: '', description: '', aliases: [] }
  const json = await unwrap(res, `GET terms ${entityId}/${language}`)
  return json
}

export async function getStatement(contentHash) {
  const res = await fetch(`${BASE}/v1/statements/${encodeURIComponent(contentHash)}`)
  return unwrap(res, `GET statement ${contentHash}`)
}

export async function getSnak(snakHash) {
  const res = await fetch(`${BASE}/v1/resolve/snaks/${encodeURIComponent(snakHash)}`)
  const json = await unwrap(res, `GET snak ${snakHash}`)
  return json[0]?.snak ?? null
}

// --- Change stream (kafka2sse backend) ---

export async function getStreamTopics() {
  const res = await fetch(`${BASE}/v1/topics`)
  const json = await unwrap(res, 'GET topics')
  return json.topics ?? []
}

export async function getStreamHealth() {
  const res = await fetch(`${BASE}/k2s/health`)
  return unwrap(res, 'GET stream health')
}

// --- Statistics ---

export async function getGeneralStats() {
  const res = await fetch(`${BASE}/v1/stats`)
  return unwrap(res, 'GET general stats')
}

export async function getEditStats() {
  const res = await fetch(`${BASE}/v1/stats/edits`)
  return unwrap(res, 'GET edit stats')
}

export async function getDeduplicationStats() {
  const res = await fetch(`${BASE}/v1/stats/deduplication`)
  return unwrap(res, 'GET deduplication stats')
}

// --- User list ---

export async function getUserList(limit = 10, offset = 0) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  const res = await fetch(`${BASE}/v1/users?${params}`)
  return unwrap(res, 'GET user list')
}

// --- Search ---

export async function searchEntities(query, { type = '', limit = 20, offset = 0 } = {}) {
  const params = new URLSearchParams({
    q: query,
    limit: String(limit),
    offset: String(offset),
  })
  if (type) params.set('type', type)
  const res = await fetch(`${BASE}/v1/search?${params}`)
  return unwrap(res, 'GET search')
}

// --- Entity list ---

export async function getEntityList(entityType, limit = 10, offset = 0) {
  const params = new URLSearchParams({
    entity_type: entityType,
    limit: String(limit),
    offset: String(offset),
  })
  const res = await fetch(`${BASE}/v1/entities?${params}`)
  return unwrap(res, 'GET entity list')
}

// --- Recent changes ---

export async function getRecentChanges(limit = 50, offset = 0, excludeImports = false) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (excludeImports) params.set('exclude_imports', 'true')
  const res = await fetch(`${BASE}/v1/recentchanges?${params}`)
  return unwrap(res, 'GET recentchanges')
}

// --- Per-user UI settings ---

export async function getUserSettings(userId) {
  const res = await fetch(`${BASE}/v1/users/${encodeURIComponent(userId)}/settings`, {
    headers: authHeaders(),
  })
  if (res.status === 404) return {}
  return unwrap(res, `GET user settings ${userId}`)
}

export async function putUserSettings(userId, settings) {
  const res = await fetch(
    `${BASE}/v1/users/${encodeURIComponent(userId)}/settings`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(settings),
    }
  )
  return unwrap(res, `PUT user settings ${userId}`)
}

// --- Entity history ---

export async function getEntityHistory(entityId, limit = 20, offset = 0) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  const res = await fetch(
    `${BASE}/v1/entities/${encodeURIComponent(entityId)}/revisions?${params}`
  )
  return unwrap(res, `GET history ${entityId}`)
}

export async function getEntityRevision(entityId, revisionId) {
  const res = await fetch(
    `${BASE}/v1/entities/${encodeURIComponent(entityId)}/revision/${encodeURIComponent(revisionId)}`
  )
  return unwrap(res, `GET revision ${entityId}/${revisionId}`)
}

// --- Hash-resolve helpers (terms are stored hash-referenced) ---

async function resolveBatch(kind, hashes) {
  const hashesList = hashes.filter(Boolean).map(String)
  if (!hashesList.length) return {}
  const out = {}
  for (let i = 0; i < hashesList.length; i += 20) {
    const chunk = hashesList.slice(i, i + 20).join(',')
    const res = await fetch(`${BASE}/v1/resolve/${kind}/${encodeURIComponent(chunk)}`)
    const json = await unwrap(res, `GET ${kind} ${chunk}`)
    Object.assign(out, json)
  }
  return out
}

export function resolveLabels(hashes) {
  return resolveBatch('labels', hashes).then((r) => r.labels ?? r)
}

export function resolveDescriptions(hashes) {
  return resolveBatch('descriptions', hashes).then((r) => r.descriptions ?? r)
}

export function resolveAliases(hashes) {
  return resolveBatch('aliases', hashes).then((r) => r.aliases ?? r)
}

// Fallback-aware term getters: try each language in order, first hit wins
export async function getLabelWithFallback(entityId, chain) {
  for (const lang of chain) {
    const value = await getLabel(entityId, lang)
    if (value) return value
  }
  return null
}

export async function getDescriptionWithFallback(entityId, chain) {
  for (const lang of chain) {
    const value = await getDescription(entityId, lang)
    if (value) return value
  }
  return null
}

export async function getAliasesWithFallback(entityId, chain) {
  for (const lang of chain) {
    const aliases = await getAliases(entityId, lang)
    if (aliases && aliases.length) return aliases
  }
  return []
}
