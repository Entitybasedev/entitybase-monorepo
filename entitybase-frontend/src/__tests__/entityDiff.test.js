import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { computeEntityDiff } from '../entityDiff.js'

const resolvers = {
  resolveLabels: vi.fn(),
  resolveDescriptions: vi.fn(),
  resolveAliases: vi.fn(),
  getStatement: vi.fn(),
  getSnak: vi.fn(),
}

function revisionPayload(hashes) {
  return { id: 'Q1', rev_id: 1, data: { revision: { hashes } } }
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('computeEntityDiff', () => {
  it('reports no changes when both revisions have identical empty hashes', async () => {
    const diff = await computeEntityDiff(revisionPayload({}), revisionPayload({}), resolvers)
    expect(diff.hasChanges).toBe(false)
    expect(diff.labels).toEqual([])
    expect(diff.statements.added).toEqual([])
    expect(diff.statements.removed).toEqual([])
  })

  it('detects an added label', async () => {
    resolvers.resolveLabels.mockResolvedValue({ '111': 'Universe' })
    const oldRev = revisionPayload({ labels: {} })
    const newRev = revisionPayload({ labels: { en: 111 } })

    const diff = await computeEntityDiff(oldRev, newRev, resolvers)

    expect(resolvers.resolveLabels).toHaveBeenCalledWith([111])
    expect(diff.labels).toEqual([
      { lang: 'en', status: 'added', old: null, new: 'Universe' },
    ])
    expect(diff.hasChanges).toBe(true)
  })

  it('detects a changed and a removed label', async () => {
    resolvers.resolveLabels
      .mockResolvedValueOnce({ '1': 'Old', '2': 'Gone' }) // old revision labels
      .mockResolvedValueOnce({ '1': 'New' }) // new revision labels
    const oldRev = revisionPayload({ labels: { en: 1, de: 2 } })
    const newRev = revisionPayload({ labels: { en: 1 } })

    const diff = await computeEntityDiff(oldRev, newRev, resolvers)

    expect(diff.labels).toContainEqual({
      lang: 'en',
      status: 'changed',
      old: 'Old',
      new: 'New',
    })
    expect(diff.labels).toContainEqual({
      lang: 'de',
      status: 'removed',
      old: 'Gone',
      new: null,
    })
  })

  it('resolves descriptions the same way', async () => {
    resolvers.resolveDescriptions.mockResolvedValue({ '5': 'A thing' })
    const oldRev = revisionPayload({ descriptions: {} })
    const newRev = revisionPayload({ descriptions: { en: 5 } })

    const diff = await computeEntityDiff(oldRev, newRev, resolvers)

    expect(diff.descriptions).toEqual([
      { lang: 'en', status: 'added', old: null, new: 'A thing' },
    ])
  })

  it('reports added and removed aliases per language', async () => {
    resolvers.resolveAliases
      .mockResolvedValueOnce({ '7': 'Old alias' }) // old revision
      .mockResolvedValueOnce({ '8': 'New alias' }) // new revision
    const oldRev = revisionPayload({ aliases: { en: [7] } })
    const newRev = revisionPayload({ aliases: { en: [8] } })

    const diff = await computeEntityDiff(oldRev, newRev, resolvers)

    expect(diff.aliases).toEqual([
      { lang: 'en', added: ['New alias'], removed: ['Old alias'] },
    ])
  })

  it('reports added and removed statements with resolved values', async () => {
    resolvers.getStatement.mockImplementation((hash) =>
      Promise.resolve({
        schema: '1.0',
        hash,
        statement: {
          id: `S${hash}`,
          mainsnak: Number(hash) === 10 ? 20 : 21, // mainsnak is a snak hash
          type: 'statement',
          rank: 'normal',
        },
      })
    )
    resolvers.getSnak.mockImplementation((hash) =>
      Promise.resolve({
        snaktype: 'value',
        property: Number(hash) === 20 ? 'P31' : 'P279',
        datavalue: { value: { id: 'Q5' }, type: 'wikibase-item' },
      })
    )
    const oldRev = revisionPayload({ statements: [10] })
    const newRev = revisionPayload({ statements: [11] })

    const diff = await computeEntityDiff(oldRev, newRev, resolvers)

    expect(diff.statements.added).toEqual([{ property: 'P279', value: 'Q5' }])
    expect(diff.statements.removed).toEqual([{ property: 'P31', value: 'Q5' }])
    expect(diff.hasChanges).toBe(true)
  })

  it('identical non-empty revisions produce no changes', async () => {
    const hashes = {
      labels: { en: 1 },
      descriptions: { en: 2 },
      aliases: { en: [3] },
      statements: [4],
    }
    const oldRev = revisionPayload(hashes)
    const newRev = revisionPayload(hashes)
    resolvers.resolveLabels.mockResolvedValue({ '1': 'L' })
    resolvers.resolveDescriptions.mockResolvedValue({ '2': 'D' })
    resolvers.resolveAliases.mockResolvedValue({ '3': ['A'] })
    resolvers.getStatement.mockResolvedValue({
      schema: '1.0',
      hash: 4,
      statement: {
        mainsnak: { property: 'P31', datavalue: { value: { id: 'Q5' }, type: 'wikibase-item' } },
      },
    })

    const diff = await computeEntityDiff(oldRev, newRev, resolvers)

    expect(diff.hasChanges).toBe(false)
  })
})
