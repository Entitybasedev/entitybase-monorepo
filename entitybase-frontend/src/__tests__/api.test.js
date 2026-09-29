import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  getItem,
  getLabel,
  getSnak,
  getStatement,
  postItem,
  postLexeme,
  postProperty,
  postStatement,
  putLabel,
} from '../api.js'

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
      jsonResponse({
        id: 'Q42',
        rev_id: 1,
        data: { schema: '4.0.0', revision: { labels: {} } },
      })
    )

    const item = await getItem('Q42')

    expect(fetchMock.mock.calls[0][0]).toBe('/v1/entities/Q42')
    expect(item.id).toBe('Q42')
    expect(item.data.revision.labels).toEqual({})
  })

  it('encodes the entity id in the URL', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ id: 'Q 1' }))
    await getItem('Q 1')
    expect(fetchMock.mock.calls[0][0]).toBe('/v1/entities/Q%201')
  })
})

describe('getLabel', () => {
  it('GETs the label endpoint and returns the value', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ value: 'Universe' }))

    const value = await getLabel('Q42', 'en')

    expect(fetchMock.mock.calls[0][0]).toBe('/v1/entities/Q42/labels/en')
    expect(value).toBe('Universe')
  })

  it('returns null on 404 (no label for language)', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ message: 'not found' }, 404))
    expect(await getLabel('Q42', 'de')).toBeNull()
  })
})

describe('getStatement', () => {
  it('GETs the statement by content hash', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ schema: '1.0', hash: 123, statement: { mainsnak: {} } })
    )

    const res = await getStatement(123)

    expect(fetchMock.mock.calls[0][0]).toBe('/v1/statements/123')
    expect(res.hash).toBe(123)
  })
})

describe('postProperty', () => {
  it('posts to /v1/entities/properties and unwraps the id', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ success: true, data: { entity_id: 'P30000', revision_id: 1 } })
    )

    const propertyId = await postProperty({}, 42)

    expect(propertyId).toBe('P30000')
    expect(fetchMock.mock.calls[0][0]).toBe('/v1/entities/properties')
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(fetchMock.mock.calls[0][1].headers['X-User-ID']).toBe('42')
  })
})

describe('postLexeme', () => {
  it('posts the lexeme payload and unwraps the id from EntityResponse', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ id: 'L77', rev_id: 1, data: { revision: {} } })
    )

    const body = {
      type: 'lexeme',
      lemmas: { en: { language: 'en', value: 'answer' } },
      language: 'Q1860',
      lexical_category: 'Q1084',
    }
    const lexemeId = await postLexeme(body, 42)

    expect(lexemeId).toBe('L77')
    expect(fetchMock.mock.calls[0][0]).toBe('/v1/entities/lexemes')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(body)
  })
})

describe('int64-safe JSON parsing', () => {
  it('preserves large statement hashes as strings', async () => {
    const bigHash = '11653253820340142024'
    const raw = `{"id":"Q1","rev_id":1,"data":{"revision":{"hashes":{"statements":[${bigHash}]}}}}`
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      text: () => Promise.resolve(raw),
      json: () => Promise.resolve(JSON.parse(raw)),
    })

    const item = await getItem('Q1')

    expect(item.data.revision.hashes.statements[0]).toBe(bigHash)
  })

  it('keeps small numbers as numbers', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ id: 'Q1', rev_id: 7, data: { revision: {} } }))
    const item = await getItem('Q1')
    expect(item.rev_id).toBe(7)
  })
})

describe('getSnak', () => {
  it('resolves a snak hash and returns the snak object', async () => {
    const snak = { property: 'P31', datavalue: { value: { id: 'Q5' }, type: 'wikibase-item' } }
    fetchMock.mockResolvedValue(
      jsonResponse([{ snak, hash: 555, created_at: '2025-01-01T00:00:00Z' }])
    )

    const result = await getSnak(555)

    expect(fetchMock.mock.calls[0][0]).toBe('/v1/resolve/snaks/555')
    expect(result.property).toBe('P31')
    expect(result.datavalue.value.id).toBe('Q5')
  })

  it('returns null when the snak is missing', async () => {
    fetchMock.mockResolvedValue(jsonResponse([null]))
    expect(await getSnak(999)).toBeNull()
  })
})
