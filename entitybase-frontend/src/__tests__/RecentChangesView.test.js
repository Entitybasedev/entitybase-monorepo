import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const apiMocks = vi.hoisted(() => ({
  getRecentChanges: vi.fn().mockResolvedValue([]),
}))

vi.mock('../api.js', () => apiMocks)

import RecentChangesView from '../views/RecentChangesView.vue'
import router from '../router.js'

function entry(id, changeType, entityId = 'Q42') {
  return {
    id,
    created_at: '2026-10-01T12:00:00Z',
    user_id: 90001,
    activity_type: 'entity_edit',
    change_type: changeType,
    entity_id: entityId,
    revision_id: id,
    edit_summary: 'did a thing',
  }
}

async function mountView(path = '/recent') {
  await router.push(path)
  const wrapper = mount(RecentChangesView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

beforeEach(async () => {
  vi.resetAllMocks()
  apiMocks.getRecentChanges.mockResolvedValue([])
  await router.push('/').then(() => router.isReady())
})

describe('RecentChangesView', () => {
  it('renders rows with humanized change types', async () => {
    apiMocks.getRecentChanges.mockResolvedValue([
      entry(2, 'label_update'),
      entry(1, 'statement_add'),
    ])

    const wrapper = await mountView()

    expect(apiMocks.getRecentChanges).toHaveBeenCalledWith(50, 0)
    const rows = wrapper.findAll('[data-testid="recent-row"]')
    expect(rows).toHaveLength(2)
    const types = wrapper.findAll('[data-testid="recent-type"]')
    expect(types[0].text()).toBe('Label edited')
    expect(types[1].text()).toBe('New statement')
    expect(wrapper.find('[data-testid="recent-summary"]').text()).toBe('did a thing')
  })

  it('links to the entity of each row', async () => {
    apiMocks.getRecentChanges.mockResolvedValue([entry(1, 'entity_create', 'Q7')])

    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="recent-entity"]').attributes('href')).toBe(
      '/?entity=Q7'
    )
  })

  it('falls back to a generic label for unknown change types', async () => {
    apiMocks.getRecentChanges.mockResolvedValue([entry(1, 'weird_new_type')])

    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="recent-type"]').text()).toBe('Edit')
  })

  it('refreshes on button click', async () => {
    const wrapper = await mountView()

    apiMocks.getRecentChanges.mockResolvedValue([entry(1, 'label_update')])
    await wrapper.find('[data-testid="recent-refresh"]').trigger('click')
    await flushPromises()

    expect(apiMocks.getRecentChanges).toHaveBeenCalledTimes(2)
    expect(wrapper.findAll('[data-testid="recent-row"]')).toHaveLength(1)
  })

  it('shows an error banner when loading fails', async () => {
    apiMocks.getRecentChanges.mockRejectedValue(
      new Error('GET recentchanges failed: 500 boom')
    )

    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="recent-error"]').text()).toContain('500')
  })

  it('appends rows on load more', async () => {
    apiMocks.getRecentChanges.mockResolvedValueOnce(
      Array.from({ length: 50 }, (_, i) => entry(i + 1, 'label_update'))
    )
    const wrapper = await mountView()
    expect(wrapper.findAll('[data-testid="recent-row"]')).toHaveLength(50)

    apiMocks.getRecentChanges.mockResolvedValueOnce([entry(51, 'label_update')])
    await wrapper.find('[data-testid="recent-more"]').trigger('click')
    await flushPromises()

    expect(apiMocks.getRecentChanges).toHaveBeenLastCalledWith(50, 50)
    expect(wrapper.findAll('[data-testid="recent-row"]')).toHaveLength(51)
  })
})
