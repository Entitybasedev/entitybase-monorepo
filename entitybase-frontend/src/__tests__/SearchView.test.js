import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const apiMocks = vi.hoisted(() => ({
  searchEntities: vi.fn().mockResolvedValue({ hits: [], estimated_total_hits: 0 }),
}))

vi.mock('../api.js', () => apiMocks)

import SearchView from '../views/SearchView.vue'
import router from '../router.js'

function searchResponse(hits, extra = {}) {
  return {
    query: 'douglas',
    type: '',
    index: 'entitybase',
    hits,
    estimated_total_hits: hits.length,
    limit: 20,
    offset: 0,
    processing_time_ms: 2,
    ...extra,
  }
}

function hit(overrides = {}) {
  return {
    entity_id: 'Q42',
    type: 'item',
    label: 'Douglas Adams',
    description: 'English writer',
    lastrevid: 7,
    ...overrides,
  }
}

async function mountView(path = '/search') {
  await router.push(path)
  const wrapper = mount(SearchView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

async function submitSearch(wrapper, term) {
  await wrapper.get('[data-testid="search-input"]').setValue(term)
  await wrapper.get('[data-testid="search-form"]').trigger('submit')
  await flushPromises()
}

beforeEach(async () => {
  vi.resetAllMocks()
  apiMocks.searchEntities.mockResolvedValue(searchResponse([]))
  await router.push('/').then(() => router.isReady())
})

describe('SearchView', () => {
  it('hints what can be searched before anything is typed', async () => {
    const wrapper = await mountView()

    expect(wrapper.find('[data-testid="search-hint"]').exists()).toBe(true)
    expect(apiMocks.searchEntities).not.toHaveBeenCalled()
  })

  it('searches what was typed and lists the hits', async () => {
    apiMocks.searchEntities.mockResolvedValue(searchResponse([hit()]))
    const wrapper = await mountView()

    await submitSearch(wrapper, 'douglas')

    expect(apiMocks.searchEntities).toHaveBeenCalledWith('douglas', {
      type: '',
      limit: 20,
      offset: 0,
    })
    const results = wrapper.findAll('[data-testid="search-result"]')
    expect(results).toHaveLength(1)
    expect(results[0].get('[data-testid="search-result-link"]').text()).toBe('Douglas Adams')
    expect(results[0].get('[data-testid="search-result-type"]').text()).toBe('item')
    expect(results[0].get('[data-testid="search-result-id"]').text()).toBe('Q42')
    expect(results[0].get('[data-testid="search-result-description"]').text()).toBe(
      'English writer'
    )
  })

  it('links a hit to its entity page', async () => {
    apiMocks.searchEntities.mockResolvedValue(searchResponse([hit()]))
    const wrapper = await mountView()

    await submitSearch(wrapper, 'douglas')

    expect(wrapper.get('[data-testid="search-result-link"]').attributes('href')).toBe(
      '/entity/Q42'
    )
  })

  it('falls back to the entity ID when an entity has no label', async () => {
    apiMocks.searchEntities.mockResolvedValue(
      searchResponse([hit({ label: '', description: '' })])
    )
    const wrapper = await mountView()

    await submitSearch(wrapper, 'q42')

    const result = wrapper.get('[data-testid="search-result"]')
    expect(result.get('[data-testid="search-result-link"]').text()).toBe('Q42')
    expect(result.find('[data-testid="search-result-description"]').exists()).toBe(false)
  })

  it('shows the type of every hit', async () => {
    apiMocks.searchEntities.mockResolvedValue(
      searchResponse([
        hit({ entity_id: 'P31', type: 'property', label: 'instance of' }),
        hit({ entity_id: 'L42', type: 'lexeme', label: 'answer' }),
      ])
    )
    const wrapper = await mountView()

    await submitSearch(wrapper, 'a')

    const types = wrapper
      .findAll('[data-testid="search-result-type"]')
      .map((node) => node.text())
    expect(types).toEqual(['property', 'lexeme'])
  })

  it('says so when nothing matches', async () => {
    const wrapper = await mountView()

    await submitSearch(wrapper, 'nothingmatchesthis')

    expect(wrapper.find('[data-testid="search-no-results"]').text()).toContain(
      'nothingmatchesthis'
    )
    expect(wrapper.find('[data-testid="search-results"]').exists()).toBe(false)
  })

  it('reports a failed search', async () => {
    apiMocks.searchEntities.mockRejectedValue(new Error('search failed: 503'))
    const wrapper = await mountView()

    await submitSearch(wrapper, 'douglas')

    expect(wrapper.get('[data-testid="search-error"]').text()).toContain('503')
    expect(wrapper.find('[data-testid="search-results"]').exists()).toBe(false)
  })

  it('does not search a blank query', async () => {
    const wrapper = await mountView()

    await submitSearch(wrapper, '   ')

    expect(apiMocks.searchEntities).not.toHaveBeenCalled()
  })

  it('filters by entity type and keeps it in the URL', async () => {
    apiMocks.searchEntities.mockResolvedValue(searchResponse([hit()]))
    const wrapper = await mountView()

    await submitSearch(wrapper, 'douglas')
    await wrapper.get('[data-testid="search-type-property"]').trigger('click')
    await flushPromises()

    expect(apiMocks.searchEntities).toHaveBeenLastCalledWith('douglas', {
      type: 'property',
      limit: 20,
      offset: 0,
    })
    expect(router.currentRoute.value.query).toEqual({ q: 'douglas', type: 'property' })
  })

  it('searches every type by default', async () => {
    const wrapper = await mountView()

    await submitSearch(wrapper, 'douglas')

    expect(router.currentRoute.value.query).toEqual({ q: 'douglas' })
    expect(wrapper.get('[data-testid="search-type-all"]').classes()).toContain('btn-secondary')
  })

  it('reads the query and type from the URL', async () => {
    apiMocks.searchEntities.mockResolvedValue(searchResponse([hit()]))
    await mountView('/search?q=douglas&type=lexeme')

    expect(apiMocks.searchEntities).toHaveBeenCalledWith('douglas', {
      type: 'lexeme',
      limit: 20,
      offset: 0,
    })
  })

  it('ignores an unknown type in the URL', async () => {
    await mountView('/search?q=douglas&type=user')

    expect(apiMocks.searchEntities).toHaveBeenCalledWith('douglas', {
      type: '',
      limit: 20,
      offset: 0,
    })
  })

  it('reports how many results there are', async () => {
    apiMocks.searchEntities.mockResolvedValue(
      searchResponse([hit(), hit({ entity_id: 'Q43' })], {
        estimated_total_hits: 57,
        processing_time_ms: 4,
      })
    )
    const wrapper = await mountView()

    await submitSearch(wrapper, 'douglas')

    expect(wrapper.get('[data-testid="search-summary-text"]').text()).toContain('2 of 57')
    expect(wrapper.get('[data-testid="search-summary-text"]').text()).toContain('4 ms')
  })

  it('pages through the results', async () => {
    apiMocks.searchEntities.mockResolvedValue(
      searchResponse([hit()], { estimated_total_hits: 45 })
    )
    const wrapper = await mountView()

    await submitSearch(wrapper, 'douglas')
    await wrapper.get('[data-testid="search-next"]').trigger('click')
    await flushPromises()

    expect(apiMocks.searchEntities).toHaveBeenLastCalledWith('douglas', {
      type: '',
      limit: 20,
      offset: 20,
    })

    await wrapper.get('[data-testid="search-prev"]').trigger('click')
    await flushPromises()

    expect(apiMocks.searchEntities).toHaveBeenLastCalledWith('douglas', {
      type: '',
      limit: 20,
      offset: 0,
    })
  })

  it('cannot page back from the first page', async () => {
    apiMocks.searchEntities.mockResolvedValue(
      searchResponse([hit()], { estimated_total_hits: 1 })
    )
    const wrapper = await mountView()

    await submitSearch(wrapper, 'douglas')

    expect(wrapper.get('[data-testid="search-prev"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-testid="search-next"]').attributes('disabled')).toBeDefined()
  })
})