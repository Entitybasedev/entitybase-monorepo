import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const apiMocks = vi.hoisted(() => ({
  getGeneralStats: vi.fn(),
  getEditStats: vi.fn(),
  getDeduplicationStats: vi.fn(),
}))

vi.mock('../api.js', () => apiMocks)

import StatisticsView from '../views/StatisticsView.vue'
import router from '../router.js'

const GENERAL_STATS = {
  date: '2026-10-01',
  total_items: 42,
  total_properties: 7,
  total_lexemes: 3,
  total_statements: 1234,
  total_qualifiers: 55,
  total_references: 88,
  total_sitelinks: 9,
  total_terms: 200,
  terms_by_type: { counts: { aliases: 40, descriptions: 60, labels: 100 } },
  terms_per_language: { terms: { en: 150, sv: 50 } },
}

const DEDUP_STATS = {
  statements: {
    unique_hashes: 900,
    total_ref_count: 1234,
    deduplication_factor: 27.1,
    space_saved: 334,
  },
  terms: {
    unique_hashes: 150,
    total_ref_count: 200,
    deduplication_factor: 25,
    space_saved: 50,
  },
}

async function mountView() {
  await router.push('/statistics')
  const wrapper = mount(StatisticsView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('StatisticsView', () => {
  it('renders edit activity, general stats, terms and deduplication details', async () => {
    apiMocks.getGeneralStats.mockResolvedValue(GENERAL_STATS)
    apiMocks.getEditStats.mockResolvedValue({
      edits_7d: 11,
      edits_30d: 83,
      edits_total: 5000,
    })
    apiMocks.getDeduplicationStats.mockResolvedValue(DEDUP_STATS)

    const wrapper = await mountView()

    expect(apiMocks.getGeneralStats).toHaveBeenCalled()
    expect(apiMocks.getEditStats).toHaveBeenCalled()
    expect(apiMocks.getDeduplicationStats).toHaveBeenCalled()

    expect(wrapper.find('[data-testid="statistics-edits-7d"]').text()).toBe('11')
    expect(wrapper.find('[data-testid="statistics-edits-30d"]').text()).toBe('83')
    expect(wrapper.find('[data-testid="statistics-edits-total"]').text()).toBe('5000')

    expect(wrapper.find('[data-testid="statistics-date"]').text()).toBe(
      'Computed: 2026-10-01'
    )
    const general = wrapper.findAll(
      '[data-testid="statistics-general-value"]'
    )
    expect(general.map((c) => c.text())).toEqual([
      '42', '7', '3', '1234', '55', '88', '9', '200',
    ])

    const byType = wrapper.findAll(
      '[data-testid="statistics-terms-by-type-value"]'
    )
    expect(byType.map((c) => c.text())).toEqual(['40', '60', '100'])

    const perLang = wrapper.findAll(
      '[data-testid="statistics-terms-per-language-value"]'
    )
    expect(perLang.map((c) => c.text())).toEqual(['150', '50'])

    const dedupRows = wrapper.findAll('[data-testid="statistics-deduplication-type"]')
    expect(dedupRows.map((c) => c.text())).toEqual(['statements', 'terms'])
    expect(wrapper.find('[data-testid="statistics-deduplication-unique"]').text()).toBe('900')
    expect(wrapper.find('[data-testid="statistics-deduplication-factor"]').text()).toBe('27.1%')
  })

  it('shows an error banner when a stats API call fails', async () => {
    apiMocks.getGeneralStats.mockResolvedValue(GENERAL_STATS)
    apiMocks.getEditStats.mockResolvedValue({})
    apiMocks.getDeduplicationStats.mockRejectedValue(new Error('boom'))

    const wrapper = await mountView()

    expect(wrapper.find('[data-testid="error-banner"]').text()).toContain('boom')
    expect(wrapper.find('[data-testid="statistics-edits-7d"]').exists()).toBe(false)
  })
})
