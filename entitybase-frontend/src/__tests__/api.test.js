import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  deleteStatement,
  entityJsonUrl,
  entityRdfUrl,
  getItem,
  getAliases,
  getDescription,
  getEntityTerms,
  getLabel,
  getSnak,
  getStatement,
  postItem,
  postLexeme,
  postLexemeForm,
  postLexemeSense,
  postProperty,
  postStatement,
  putLabel,
  searchEntities,
} from '../api.js'
import { login, logout, userId } from '../auth.js'

const fetchMock = vi.fn()

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  logout()
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

    const entityId = await postItem({})

    expect(entityId).toBe('Q1000')
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/v1/entities/items')
    expect(init.method).toBe('POST')
    // Logged out: identity comes from the bearer token only
    expect(init.headers['X-User-ID']).toBeUndefined()
    expect(init.headers['Authorization']).toBeUndefined()
    expect(init.headers['X-Edit-Summary']).toBeTruthy()
  })

  it('unwraps entity_id from the data envelope', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ success: true, data: { entity_id: 'Q7', revision_id: 3 } })
    )
    expect(await postItem({})).toBe('Q7')
  })

  it('throws with status and body on failure', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ message: 'boom' }, 500))
    await expect(postItem({})).rejects.toThrow(/500/)
  })
})

describe('putLabel', () => {
  it('PUTs language and value to the label endpoint', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ hash: 'abc' }))

    await putLabel('Q42', 'en', 'Universe')

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/v1/entities/Q42/labels/en')
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body)).toEqual({ language: 'en', value: 'Universe' })
    expect(init.headers['X-User-ID']).toBeUndefined()
  })

  it('sends only the bearer token (no X-User-ID) when logged in', async () => {
    fetchMock.mockImplementation(async (url) => {
      const body =
        url === '/v1/auth/login'
          ? { token: 'tok', user_id: 42, username: 'ada' }
          : { success: true, data: { entity_id: 'Q1', revision_id: 1 } }
      return jsonResponse(body)
    })
    await login('ada', 'secret')
    fetchMock.mockClear()

    await postItem({})

    const init = fetchMock.mock.calls[0][1]
    expect(init.headers['Authorization']).toBe('Bearer tok')
    // The API derives the user id from the token and rejects a client-sent
    // one that disagrees, so it must not be sent alongside the token
    expect(init.headers['X-User-ID']).toBeUndefined()
  })

  it('never sends an X-User-ID that disagrees with the token', async () => {
    fetchMock.mockImplementation(async (url) => {
      const body =
        url === '/v1/auth/login'
          ? { token: 'tok', user_id: 42, username: 'ada' }
          : { success: true, data: { entity_id: 'Q1', revision_id: 1 } }
      return jsonResponse(body)
    })
    await login('ada', 'secret')
    // A stale user id left behind by another account: the API answers 403
    // "X-User-ID does not match token", which would block every edit
    userId.value = 999
    fetchMock.mockClear()

    await postItem({})

    expect(fetchMock.mock.calls[0][1].headers['X-User-ID']).toBeUndefined()
  })

  it('sends X-User-ID when there is no token, for a server without auth', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ success: true, data: { entity_id: 'Q1', revision_id: 1 } })
    )
    // No token: the id can only come from the header
    userId.value = 7

    await postItem({})

    const init = fetchMock.mock.calls[0][1]
    expect(init.headers['X-User-ID']).toBe('7')
    expect(init.headers['Authorization']).toBeUndefined()
  })
})

describe('postStatement', () => {
  it('posts the claim body to the statements endpoint', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ success: true, data: {} }))

    const claim = { mainsnak: { snaktype: 'value', property: 'P31' } }
    await postStatement('Q42', { claim })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/v1/entities/Q42/statements')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ claim })
  })
})

describe('deleteStatement', () => {
  it('DELETEs the statement addressed by hash', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ success: true }))

    await deleteStatement('Q42', '5105433794040195521')

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(
      '/v1/entities/Q42/statements/5105433794040195521'
    )
    expect(init.method).toBe('DELETE')
    expect(init.headers['X-Edit-Summary']).toBeTruthy()
  })

  it('throws with the server error when the delete fails', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ message: 'not found' }, 404))

    await expect(deleteStatement('Q42', '123')).rejects.toThrow(/404/)
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

    const propertyId = await postProperty({})

    expect(propertyId).toBe('P30000')
    expect(fetchMock.mock.calls[0][0]).toBe('/v1/entities/properties')
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(fetchMock.mock.calls[0][1].headers['X-User-ID']).toBeUndefined()
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

describe('lexeme form and sense creation', () => {
  it('posts a new sense with its gloss', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ id: 'L42', rev_id: 3, data: { revision: {} } })
    )

    const body = { glosses: { en: { language: 'en', value: 'to move quickly' } } }
    const result = await postLexemeSense('L42', body)

    expect(result).toBe('L42')
    expect(fetchMock.mock.calls[0][0]).toBe('/v1/entities/lexemes/L42/senses')
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(body)
  })

  it('posts a new form with its representation and grammatical features', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ id: 'L42', rev_id: 4, data: { revision: {} } })
    )

    const body = {
      representations: { en: { language: 'en', value: 'answers' } },
      grammaticalFeatures: ['Q110786'],
    }
    await postLexemeForm('L42', body)

    expect(fetchMock.mock.calls[0][0]).toBe('/v1/entities/lexemes/L42/forms')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(body)
  })

  it('raises on a rejected sense', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'gloss required' }, 400))

    await expect(
      postLexemeSense('L42', { glosses: {} })
    ).rejects.toThrow(/400/)
  })
})

describe('entity data URLs', () => {
  it('points at the JSON and RDF representations of an entity', () => {
    expect(entityJsonUrl('Q42')).toBe('/v1/entities/Q42.json')
    expect(entityRdfUrl('Q42')).toBe('/v1/entities/Q42.ttl')
  })

  it('escapes ids that need it', () => {
    expect(entityJsonUrl('L42')).toBe('/v1/entities/L42.json')
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

  it('preserves every hash when several large hashes are adjacent', async () => {
    // Regression: the regex used to consume the delimiter before the next
    // hash, so the second hash was parsed as a number and rounded
    const hashes = ['15043976472407168515', '11852207546045822495', '211101557983833924']
    const raw = `{"id":"Q1","rev_id":1,"data":{"revision":{"hashes":{"statements":[${hashes.join(
      ','
    )}],"aliases":{"en":["3479604806168766037","9089341576056635688"]}}}}}`
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      text: () => Promise.resolve(raw),
      json: () => Promise.resolve(JSON.parse(raw)),
    })

    const item = await getItem('Q1')

    expect(item.data.revision.hashes.statements).toEqual(hashes)
    expect(item.data.revision.hashes.aliases.en).toEqual([
      '3479604806168766037',
      '9089341576056635688',
    ])
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

describe('getDescription', () => {
  it('GETs the description endpoint and returns the value', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ value: 'A test description' }))

    const value = await getDescription('Q42', 'en')

    expect(fetchMock.mock.calls[0][0]).toBe('/v1/entities/Q42/descriptions/en')
    expect(value).toBe('A test description')
  })

  it('returns null on 404', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ message: 'not found' }, 404))
    expect(await getDescription('Q42', 'de')).toBeNull()
  })
})

describe('getAliases', () => {
  it('GETs the aliases endpoint and returns the list', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ aliases: ['foo', 'bar'] }))

    const aliases = await getAliases('Q42', 'en')

    expect(fetchMock.mock.calls[0][0]).toBe('/v1/entities/Q42/aliases/en')
    expect(aliases).toEqual(['foo', 'bar'])
  })

  it('returns an empty list on 404', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ message: 'not found' }, 404))
    expect(await getAliases('Q42', 'sv')).toEqual([])
  })
})

describe('getEntityTerms', () => {
  it('GETs the per-language terms endpoint and returns the terms', async () => {
    const terms = { language: 'en', label: 'A', description: 'B', aliases: ['C'] }
    fetchMock.mockResolvedValue(jsonResponse(terms))

    expect(await getEntityTerms('Q42', 'en')).toEqual(terms)
    expect(fetchMock.mock.calls[0][0]).toBe('/v1/entities/Q42/terms/en')
  })

  it('returns empty terms on 404', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ message: 'not found' }, 404))

    expect(await getEntityTerms('Q42', 'de')).toEqual({
      language: 'de',
      label: '',
      description: '',
      aliases: [],
    })
  })
})

describe('searchEntities', () => {
  it('GETs the search endpoint with the query and paging', async () => {
    const body = { hits: [{ entity_id: 'Q42' }], estimated_total_hits: 1 }
    fetchMock.mockResolvedValue(jsonResponse(body))

    expect(await searchEntities('douglas', { limit: 5, offset: 10 })).toEqual(body)
    expect(fetchMock.mock.calls[0][0]).toBe('/v1/search?q=douglas&limit=5&offset=10')
  })

  it('searches every type when no type is given', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ hits: [] }))

    await searchEntities('douglas')

    expect(fetchMock.mock.calls[0][0]).not.toContain('type=')
  })

  it('passes the entity type filter on', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ hits: [] }))

    await searchEntities('douglas', { type: 'lexeme' })

    expect(fetchMock.mock.calls[0][0]).toBe('/v1/search?q=douglas&limit=20&offset=0&type=lexeme')
  })

  it('encodes the query', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ hits: [] }))

    await searchEntities('douglas adams & co')

    expect(fetchMock.mock.calls[0][0]).toContain('q=douglas+adams+%26+co')
  })
})
