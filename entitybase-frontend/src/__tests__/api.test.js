import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { getItem, postItem, postStatement, putLabel } from '../api.js'

const fetchMock = vi.fn()

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(JSON.stringify(body)),
    json: () => Promise.resolve(body),
  }
}

describe('postItem', () => {
  it('posts to /v1/entities/items with edit headers', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ success: true, data: { entity_id: 'Q1000', revision_id: 1 } })
    )

    const entityId = await postItem({}, 42)

    expect(entityId).toBe('Q1000')
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/v1/entities/items')
    expect(init.method).toBe('POST')
    expect(init.headers['X-User-ID']).toBe('42')
    expect(init.headers['X-Edit-Summary']).toBeTruthy()
  })

  it('unwraps entity_id from the data envelope', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ success: true, data: { entity_id: 'Q7', revision_id: 3 } })
    )
    expect(await postItem({}, 1)).toBe('Q7')
  })

  it('throws with status and body on failure', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ message: 'boom' }, 500))
    await expect(postItem({}, 1)).rejects.toThrow(/500/)
  })
})

describe('putLabel', () => {
  it('PUTs language and value to the label endpoint', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ hash: 'abc' }))

    await putLabel('Q42', 'en', 'Universe', 9)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/v1/entities/Q42/labels/en')
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body)).toEqual({ language: 'en', value: 'Universe' })
    expect(init.headers['X-User-ID']).toBe('9')
  })
})

describe('postStatement', () => {
  it('posts the claim body to the statements endpoint', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ success: true, data: {} }))

    const claim = { mainsnak: { snaktype: 'value', property: 'P31' } }
    await postStatement('Q42', { claim }, 5)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/v1/entities/Q42/statements')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ claim })
  })
})

describe('getItem', () => {
  it('GETs the entity and unwraps the response', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ id: 'Q42', rev_id: 1, data: { labels: {} } })
    )

    const item = await getItem('Q42')

    expect(fetchMock.mock.calls[0][0]).toBe('/v1/entities/Q42')
    expect(item.id).toBe('Q42')
    expect(item.data.labels).toEqual({})
  })

  it('encodes the entity id in the URL', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ id: 'Q 1' }))
    await getItem('Q 1')
    expect(fetchMock.mock.calls[0][0]).toBe('/v1/entities/Q%201')
  })
})
