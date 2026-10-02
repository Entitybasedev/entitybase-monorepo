import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const apiMocks = vi.hoisted(() => ({
  getEntityHistory: vi.fn(),
  getEntityRevision: vi.fn(),
  getStatement: vi.fn(),
  getSnak: vi.fn(),
  resolveLabels: vi.fn(),
  resolveDescriptions: vi.fn(),
  resolveAliases: vi.fn(),
}))

vi.mock('../api.js', () => apiMocks)

import EntityHistoryView from '../views/EntityHistoryView.vue'
import router from '../router.js'

let current = null

async function mountHistory(entityId = 'Q1') {
  await router.push(`/${entityId}/history`)
  const wrapper = mount(EntityHistoryView, { global: { plugins: [router] } })
  await flushPromises()
  current = wrapper
  return wrapper
}

beforeEach(async () => {
  vi.clearAllMocks()
  await router.push('/').then(() => router.isReady())
})

afterEach(() => {
  // Unmount: otherwise lingering instances keep watching the router
  if (current) current.unmount()
  current = null
})

describe('EntityHistoryView', () => {
  it('loads and renders the revision history', async () => {
    apiMocks.getEntityHistory.mockResolvedValue([
      { revision_id: 2, created_at: '2026-01-02T00:00:00Z', user_id: 90001, edit_summary: 'Added label' },
      { revision_id: 1, created_at: '2026-01-01T00:00:00Z', user_id: 90001, edit_summary: '' },
    ])

    const wrapper = await mountHistory('Q1')

    expect(apiMocks.getEntityHistory).toHaveBeenCalledWith('Q1', 20, 0)
    const rows = wrapper.findAll('[data-testid="history-row"]')
    expect(rows).toHaveLength(2)
    expect(wrapper.find('[data-testid="history-revision"]').text()).toBe('2')
    expect(wrapper.find('[data-testid="history-summary"]').text()).toBe('Added label')
  })

  it('views an old revision and goes back to current', async () => {
    apiMocks.getEntityHistory.mockResolvedValue([
      { revision_id: 2, created_at: '', user_id: 1, edit_summary: 'edit' },
      { revision_id: 1, created_at: '', user_id: 1, edit_summary: 'create' },
    ])
    apiMocks.getEntityRevision.mockResolvedValueOnce({ id: 'Q1', rev_id: 2, data: {} })

    const wrapper = await mountHistory('Q1')
    await wrapper.find('[data-testid="history-view"]').trigger('click')
    await flushPromises()

    expect(apiMocks.getEntityRevision).toHaveBeenCalledWith('Q1', 2)
    expect(wrapper.find('[data-testid="revision-banner"]').text()).toContain('Viewing revision 2')

    await wrapper.find('[data-testid="back-to-current"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="revision-banner"]').exists()).toBe(false)
  })

  it('shows a diff against the previous revision', async () => {
    apiMocks.getEntityHistory.mockResolvedValue([
      { revision_id: 2, created_at: '', user_id: 1, edit_summary: 'edit' },
      { revision_id: 1, created_at: '', user_id: 1, edit_summary: 'create' },
    ])
    apiMocks.getEntityRevision
      .mockResolvedValueOnce({
        id: 'Q1',
        rev_id: 2,
        data: { revision: { hashes: { labels: {}, descriptions: {}, aliases: {}, statements: [11] } } },
      })
      .mockResolvedValueOnce({
        id: 'Q1',
        rev_id: 1,
        data: { revision: { hashes: { labels: {}, descriptions: {}, aliases: {}, statements: [10] } } },
      })
    apiMocks.getStatement.mockResolvedValue({
      schema: '1.0',
      hash: 11,
      statement: {
        mainsnak: { property: 'P31', datavalue: { value: { id: 'Q5' }, type: 'wikibase-item' } },
        type: 'statement',
        rank: 'normal',
      },
    })
    apiMocks.getSnak.mockResolvedValue({
      property: 'P31',
      datavalue: { value: { id: 'Q5' }, type: 'wikibase-item' },
    })

    const wrapper = await mountHistory('Q1')
    await wrapper.find('[data-testid="history-diff"]').trigger('click')
    await flushPromises()
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/Q1/history/2/1')
    expect(apiMocks.getEntityRevision).toHaveBeenCalledWith('Q1', 2)
    expect(apiMocks.getEntityRevision).toHaveBeenCalledWith('Q1', 1)
    const diffView = wrapper.find('[data-testid="diff-view"]')
    expect(diffView.exists()).toBe(true)
    for (let i = 0; i < 10 && !wrapper.find('[data-testid="diff-added"]').exists(); i++) {
      await flushPromises()
    }
    expect(wrapper.find('[data-testid="diff-added"]').text()).toContain('P31: Q5')
    expect(wrapper.find('[data-testid="diff-removed"]').text()).toContain('− P31: Q5')
  })

  it('computes the diff when opening a shareable diff URL directly', async () => {
    apiMocks.getEntityHistory.mockResolvedValue([
      { revision_id: 2, created_at: '', user_id: 1, edit_summary: 'edit' },
      { revision_id: 1, created_at: '', user_id: 1, edit_summary: 'create' },
    ])
    apiMocks.getEntityRevision
      .mockResolvedValueOnce({
        id: 'Q1',
        rev_id: 2,
        data: { revision: { hashes: { labels: {}, descriptions: {}, aliases: {}, statements: [11] } } },
      })
      .mockResolvedValueOnce({
        id: 'Q1',
        rev_id: 1,
        data: { revision: { hashes: { labels: {}, descriptions: {}, aliases: {}, statements: [10] } } },
      })
    apiMocks.getStatement.mockResolvedValue({
      schema: '1.0',
      hash: 11,
      statement: {
        mainsnak: { property: 'P31', datavalue: { value: { id: 'Q5' }, type: 'wikibase-item' } },
        type: 'statement',
        rank: 'normal',
      },
    })
    apiMocks.getSnak.mockResolvedValue({
      property: 'P31',
      datavalue: { value: { id: 'Q5' }, type: 'wikibase-item' },
    })

    await router.push('/Q1/history/2/1')
    const wrapper = mount(EntityHistoryView, { global: { plugins: [router] } })
    await flushPromises()
    for (let i = 0; i < 10 && !wrapper.find('[data-testid="diff-added"]').exists(); i++) {
      await flushPromises()
    }

    expect(wrapper.find('[data-testid="diff-view"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="diff-added"]').text()).toContain('P31: Q5')

    // Closing returns to the plain history URL
    await wrapper.find('[data-testid="diff-close"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/Q1/history')
    expect(wrapper.find('[data-testid="diff-view"]').exists()).toBe(false)
  })

  it('shows an empty state when the entity has no revisions', async () => {
    apiMocks.getEntityHistory.mockResolvedValue([])

    const wrapper = await mountHistory('Q1')
    expect(wrapper.find('[data-testid="history-empty"]').exists()).toBe(true)
  })
})
