import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { fallbackChain } from '../settings.js'

const apiMocks = vi.hoisted(() => ({
  getItem: vi.fn(),
  getEntityTerms: vi.fn(),
}))

vi.mock('../api.js', () => apiMocks)

import App from '../App.vue'
import router from '../router.js'

function itemPayload(id, hashes) {
  return {
    id,
    rev_id: 1,
    data: {
      schema: '4.0.0',
      hash: 123456789,
      created_at: '2025-01-01T00:00:00Z',
      revision: { id, hashes },
    },
  }
}

async function mountAt(path) {
  await router.push(path)
  const wrapper = mount(App, { global: { plugins: [router] } })
  await router.isReady()
  await flushPromises()
  return wrapper
}

// Two-letter language codes aa..bs in sorted order (45 codes)
const LETTERS = 'abcdefghijklmnopqrstuvwxyz'
const MANY_LANGS = Array.from({ length: 45 }, (_, i) => LETTERS[i / 26 | 0] + LETTERS[i % 26])

beforeEach(() => {
  vi.clearAllMocks()
  fallbackChain.value = []
  window.history.replaceState(null, '', '/')
  return router.push('/').then(() => router.isReady())
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('EntityTermsView', () => {
  it('defaults to the fallback-chain languages with placeholders for missing terms', async () => {
    apiMocks.getItem.mockResolvedValue(
      itemPayload('Q42', {
        labels: { en: '1', sv: '2', de: '3' },
        descriptions: { en: '4' },
        aliases: { en: ['5', '6'] },
      })
    )
    apiMocks.getEntityTerms.mockImplementation(async (_id, lang) => ({
      language: lang,
      label: lang === 'en' ? 'Douglas Adams' : '',
      description: lang === 'en' ? 'Author' : '',
      aliases: lang === 'en' ? ['DNA'] : [],
    }))

    const wrapper = await mountAt('/Q42/terms')

    expect(apiMocks.getItem).toHaveBeenCalledWith('Q42')
    expect(apiMocks.getEntityTerms).toHaveBeenCalledWith('Q42', 'en')

    // Only the chain language (en by default) is shown
    const rows = wrapper.findAll('[data-testid="terms-row"]')
    expect(rows).toHaveLength(1)
    expect(wrapper.find('[data-testid="terms-lang"]').text()).toBe('en')
    expect(wrapper.find('[data-testid="terms-label"]').text()).toBe('Douglas Adams')
    expect(wrapper.find('[data-testid="terms-description"]').text()).toBe('Author')
    expect(wrapper.find('[data-testid="terms-alias"]').text()).toBe('DNA')
    expect(wrapper.find('[data-testid="terms-count"]').text()).toBe('Showing 1 of 3 languages')
  })

  it('shows all languages paginated when toggled', async () => {
    apiMocks.getItem.mockResolvedValue(
      itemPayload('Q42', {
        labels: Object.fromEntries(MANY_LANGS.map((l) => [l, '1'])),
      })
    )
    apiMocks.getEntityTerms.mockImplementation(async (_id, lang) => ({
      language: lang,
      label: `L-${lang}`,
      description: '',
      aliases: [],
    }))

    const wrapper = await mountAt('/Q42/terms')

    await wrapper.find('[data-testid="terms-toggle-all"]').trigger('click')
    await flushPromises()

    expect(wrapper.findAll('[data-testid="terms-row"]')).toHaveLength(20)
    expect(wrapper.find('[data-testid="terms-page-info"]').text()).toBe('Page 1 / 3')
    expect(wrapper.find('[data-testid="terms-lang"]').text()).toBe('aa')

    await wrapper.find('[data-testid="terms-next-page"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="terms-page-info"]').text()).toBe('Page 2 / 3')
    expect(wrapper.find('[data-testid="terms-lang"]').text()).toBe('au')

    // Prev goes back
    await wrapper.find('[data-testid="terms-prev-page"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="terms-page-info"]').text()).toBe('Page 1 / 3')

    // Toggling back to chain-only view
    await wrapper.find('[data-testid="terms-toggle-all"]').trigger('click')
    await flushPromises()
    expect(wrapper.findAll('[data-testid="terms-row"]')).toHaveLength(1)
  })

  it('renders placeholders for an entity without terms', async () => {
    apiMocks.getItem.mockResolvedValue(itemPayload('Q42', {}))

    const wrapper = await mountAt('/Q42/terms')

    // Chain mode shows the interface language as a placeholder row
    const rows = wrapper.findAll('[data-testid="terms-row"]')
    expect(rows).toHaveLength(1)
    expect(wrapper.find('[data-testid="terms-lang"]').text()).toBe('en')
    expect(wrapper.find('[data-testid="terms-label"]').text()).toBe('—')
    expect(wrapper.find('[data-testid="terms-count"]').text()).toBe(
      'Showing 1 of 0 languages'
    )

    // Showing all languages yields the empty table state
    await wrapper.find('[data-testid="terms-toggle-all"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="no-terms"]').exists()).toBe(true)
  })

  it('links back to the entity page', async () => {
    apiMocks.getItem.mockResolvedValue(itemPayload('Q42', {}))

    const wrapper = await mountAt('/Q42/terms')

    expect(wrapper.find('[data-testid="back-to-entity-link"]').attributes('href')).toBe(
      '/?entity=Q42'
    )
  })
})
