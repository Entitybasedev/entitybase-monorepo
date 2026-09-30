const BASE = import.meta.env.VITE_API_BASE || ''

function editHeaders(userId) {
  return {
    'Content-Type': 'application/json',
    'X-User-ID': String(userId ?? 90001),
    'X-Edit-Summary': 'Created via entitybase-frontend',
  }
}

function safeJsonParse(text) {
  // Quote integer literals >= 15 digits so int64 hashes survive JS parsing
  // (Number.MAX_SAFE_INTEGER is ~9e15; rounding makes them unusable).
  return JSON.parse(text.replace(/([:[,\[]\s*)(\d{15,})(\s*[,\]}])/g, '$1"$2"$3'))
}

async function unwrap(res, what) {
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${what} failed: ${res.status} ${text}`)
  }
  return safeJsonParse(await res.text())
}

export async function postItem(_body, userId) {
  const res = await fetch(`${BASE}/v1/entities/items`, {
    method: 'POST',
    headers: editHeaders(userId),
  })
  const json = await unwrap(res, 'POST item')
  return json.data?.entity_id ?? json.entity_id ?? json.id
}

export async function postProperty(_body, userId) {
  const res = await fetch(`${BASE}/v1/entities/properties`, {
    method: 'POST',
    headers: editHeaders(userId),
  })
  const json = await unwrap(res, 'POST property')
  return json.data?.entity_id ?? json.entity_id ?? json.id
}

export async function postLexeme(body, userId) {
  const res = await fetch(`${BASE}/v1/entities/lexemes`, {
    method: 'POST',
    headers: editHeaders(userId),
    body: JSON.stringify(body),
  })
  const json = await unwrap(res, 'POST lexeme')
  return json.data?.entity_id ?? json.entity_id ?? json.id
}

export async function putLabel(entityId, language, value, userId) {
  const res = await fetch(
    `${BASE}/v1/entities/${encodeURIComponent(entityId)}/labels/${encodeURIComponent(language)}`,
    { method: 'PUT', headers: editHeaders(userId), body: JSON.stringify({ language, value }) }
  )
  return unwrap(res, `PUT label ${entityId}`)
}

export async function postStatement(entityId, body, userId) {
  const res = await fetch(
    `${BASE}/v1/entities/${encodeURIComponent(entityId)}/statements`,
    { method: 'POST', headers: editHeaders(userId), body: JSON.stringify(body) }
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
