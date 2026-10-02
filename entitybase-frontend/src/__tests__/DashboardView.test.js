import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const apiMocks = vi.hoisted(() => ({
  getGeneralStats: vi.fn(),
  getEditStats: vi.fn(),
  getDeduplicationStats: vi.fn(),
}))

vi.mock('../api.js', () => apiMocks)

import DashboardView from '../views/DashboardView.vue'
import router from '../router.js'

async function mountView() {
  await router.push('/')
  const wrapper = mount(DashboardView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('DashboardView', () => {
  it('renders edit and entity counts as stat cards', async () => {
    apiMocks.getGeneralStats.mockResolvedValue({
      date: '2026-10-01',
      total_items: 42,
      total_properties: 7,
      total_lexemes: 3,
      total_statements: 1234,
      total_terms: 567,
    })
    apiMocks.getEditStats.mockResolvedValue({
      edits_7d: 11,
      edits_30d: 83,
      edits_total: 5000,
    })

    const wrapper = await mountView()

    expect(apiMocks.getGeneralStats).toHaveBeenCalled()
    expect(apiMocks.getEditStats).toHaveBeenCalled()
    expect(wrapper.find('[data-testid="dashboard-edits-7d"]').text()).toBe('11')
    expect(wrapper.find('[data-testid="dashboard-edits-30d"]').text()).toBe('83')
    expect(wrapper.find('[data-testid="dashboard-items"]').text()).toBe('42')
    expect(wrapper.find('[data-testid="dashboard-properties"]').text()).toBe('7')
    expect(wrapper.find('[data-testid="dashboard-lexemes"]').text()).toBe('3')
    expect(wrapper.find('[data-testid="dashboard-statements"]').text()).toBe('1234')
    expect(wrapper.find('[data-testid="dashboard-terms"]').text()).toBe('567')
  })

  it('links to the detailed statistics page', async () => {
    apiMocks.getGeneralStats.mockResolvedValue({})
    apiMocks.getEditStats.mockResolvedValue({})

    const wrapper = await mountView()

    const link = wrapper.find('[data-testid="dashboard-statistics-link"]')
    expect(link.attributes('href')).toBe('/statistics')
  })

  it('shows an error banner when the stats API fails', async () => {
    apiMocks.getGeneralStats.mockRejectedValue(new Error('boom'))

    const wrapper = await mountView()

    expect(wrapper.find('[data-testid="error-banner"]').text()).toContain('boom')
    expect(wrapper.find('[data-testid="dashboard-edits-7d"]').exists()).toBe(false)
  })
})
