import { test, expect } from '@playwright/test'
import { API_URL, USER_ID, createPropertyViaApi } from './helpers.js'

const HEADERS = {
  'Content-Type': 'application/json',
  'X-User-ID': USER_ID,
  'X-Edit-Summary': 'e2e njson setup',
}

function edit(request, path, method, data) {
  return request.fetch(`${API_URL}${path}`, { method, headers: HEADERS, data })
}

/**
 * An item with a label, a description, aliases and a statement, so the
 * normalized endpoint has every kind of hash reference to resolve.
 */
async function createItemWithContent(request, stamp) {
  const created = await edit(request, '/v1/entities/items', 'POST')
  expect(created.ok()).toBeTruthy()
  const { data } = await created.json()
  const entityId = data.entity_id

  const label = `E2E Njson ${stamp}`
  await edit(request, `/v1/entities/${entityId}/labels/en`, 'PUT', {
    language: 'en',
    value: label,
  })
  await edit(request, `/v1/entities/${entityId}/descriptions/en`, 'PUT', {
    language: 'en',
    value: 'Created for the normalized json e2e test',
  })
  await edit(request, `/v1/entities/${entityId}/aliases/en`, 'PUT', [
    `E2E alias one ${stamp}`,
    `E2E alias two ${stamp}`,
  ])

  const propertyId = await createPropertyViaApi(request)
  const statement = await edit(
    request,
    `/v1/entities/${entityId}/statements/${propertyId}`,
    'POST',
    {
      snaktype: 'value',
      property: propertyId,
      datatype: 'wikibase-item',
      datavalue: { value: { id: entityId }, type: 'wikibase-item' },
    }
  )
  expect(statement.ok()).toBeTruthy()

  return { entityId, label }
}

async function fetchNormalized(request, entityId) {
  const response = await request.get(`${API_URL}/v1/entities/${entityId}.njson`)
  expect(response.status(), 'njson request should succeed').toBeTruthy()
  expect(response.status()).toBe(200)
  return (await response.json()).data
}

test('normalized json carries the label text, not its hash', async ({ request }) => {
  const stamp = Date.now()
  const { entityId, label } = await createItemWithContent(request, stamp)

  const data = await fetchNormalized(request, entityId)

  expect(data.id).toBe(entityId)
  // The value is present as text...
  expect(data.labels.en.value).toBe(label)
  expect(data.labels.en.language).toBe('en')
  // ...and not as a hash: the stored revision holds a number here
  expect(typeof data.labels.en.value).toBe('string')
})

test('normalized json carries descriptions and aliases', async ({ request }) => {
  const stamp = Date.now()
  const { entityId } = await createItemWithContent(request, stamp)

  const data = await fetchNormalized(request, entityId)

  expect(data.descriptions.en.value).toBe(
    'Created for the normalized json e2e test'
  )
  const aliases = data.aliases.en.map((a) => a.value)
  expect(aliases).toContain(`E2E alias one ${stamp}`)
  expect(aliases).toContain(`E2E alias two ${stamp}`)
})

test('normalized json carries the statement with its value inline', async ({
  request,
}) => {
  const stamp = Date.now()
  const { entityId } = await createItemWithContent(request, stamp)

  const data = await fetchNormalized(request, entityId)

  expect(Array.isArray(data.statements)).toBe(true)
  expect(data.statements).toHaveLength(1)

  const [statement] = data.statements
  // The statement is a readable object, not a hash pointing at one
  expect(statement.mainsnak).toBeTruthy()
  expect(statement.mainsnak.property).toMatch(/^P\d+$/)
  expect(statement.mainsnak.datavalue.value.id).toBe(entityId)
})

test('normalized json leaks no hashes', async ({ request }) => {
  const stamp = Date.now()
  const { entityId } = await createItemWithContent(request, stamp)

  // The .json endpoint is the hash-based view; read it to learn the hashes
  const raw = await request.get(`${API_URL}/v1/entities/${entityId}.json`)
  expect(raw.status()).toBe(200)
  const revision = (await raw.json()).data

  const data = await fetchNormalized(request, entityId)

  // The internal index is gone entirely
  expect(data.hashes).toBeUndefined()
  expect(revision.hashes).toBeTruthy()

  // No content hash from the revision appears anywhere in the response
  const body = JSON.stringify(data)
  const hashes = []
  for (const group of Object.values(revision.hashes)) {
    if (Array.isArray(group)) hashes.push(...group.map(String))
    else if (group && typeof group === 'object') {
      for (const value of Object.values(group)) {
        if (typeof value === 'number') hashes.push(String(value))
        else if (value && typeof value === 'object' && value.title_hash) {
          hashes.push(String(value.title_hash))
        }
      }
    }
  }
  expect(hashes.length).toBeGreaterThan(0)
  for (const hash of hashes) {
    expect(body).not.toContain(hash)
  }
})

test('the two endpoints describe the same entity', async ({ request }) => {
  const stamp = Date.now()
  const { entityId, label } = await createItemWithContent(request, stamp)

  const raw = await request.get(`${API_URL}/v1/entities/${entityId}.json`)
  const revision = (await raw.json()).data
  const data = await fetchNormalized(request, entityId)

  // Everything that is not a hash reference is identical
  for (const field of [
    'revision_id',
    'entity_type',
    'datatype',
    'properties',
    'property_counts',
    'state',
    'edit',
    'created_at',
    'schema_version',
    'redirects_to',
  ]) {
    expect(data[field], `${field} should match .json`).toEqual(revision[field])
  }

  // Same number of terms and statements, now resolved
  expect(Object.keys(data.labels)).toEqual(Object.keys(revision.hashes.labels))
  expect(Object.keys(data.descriptions)).toEqual(
    Object.keys(revision.hashes.descriptions)
  )
  expect(data.aliases.en).toHaveLength(revision.hashes.aliases.en.length)
  expect(data.statements).toHaveLength(revision.hashes.statements.length)
  expect(data.labels.en.value).toBe(label)
})

test('an empty item normalizes to empty collections', async ({ request }) => {
  const created = await edit(request, '/v1/entities/items', 'POST')
  const { data } = await created.json()

  const entity = await fetchNormalized(request, data.entity_id)

  expect(entity.labels).toEqual({})
  expect(entity.descriptions).toEqual({})
  expect(entity.aliases).toEqual({})
  expect(entity.sitelinks).toEqual({})
  expect(entity.statements).toEqual([])
})

test('a missing entity is a 404 on the normalized endpoint too', async ({
  request,
}) => {
  const response = await request.get(`${API_URL}/v1/entities/Q999999999.njson`)
  expect(response.status()).toBe(404)
})