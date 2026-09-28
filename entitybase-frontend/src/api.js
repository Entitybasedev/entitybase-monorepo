const BASE = import.meta.env.VITE_API_BASE || ''

function editHeaders(userId) {
  return {
    'Content-Type': 'application/json',
    'X-User-ID': String(userId ?? 90001),
    'X-Edit-Summary': 'Created via entitybase-frontend',
  }
}

async function unwrap(res, what) {
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${what} failed: ${res.status} ${text}`)
  }
  return res.json()
}

export async function postItem(_body, userId) {
  const res = await fetch(`${BASE}/v1/entities/items`, {
    method: 'POST',
    headers: editHeaders(userId),
  })
  const json = await unwrap(res, 'POST item')
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
