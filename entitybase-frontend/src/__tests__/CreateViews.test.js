import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const apiMocks = vi.hoisted(() => ({
  postItem: vi.fn(),
  postProperty: vi.fn(),
  postLexeme: vi.fn(),
  putLabel: vi.fn(),
  getUserSettings: vi.fn().mockResolvedValue({}),
  getItem: vi.fn(),
  getLabelWithFallback: vi.fn().mockResolvedValue(null),
  getDescriptionWithFallback: vi.fn().mockResolvedValue(null),
  getAliasesWithFallback: vi.fn().mockResolvedValue([]),
  getEntityHistory: vi.fn().mockResolvedValue([]),
  getStatement: vi.fn(),
  getSnak: vi.fn(),
  postStatement: vi.fn(),
  getEntityList: vi.fn(),
  getRecentChanges: vi.fn(),
  getGeneralStats: vi.fn().mockResolvedValue({
    date: '2026-10-01',
    total_items: 1,
    total_properties: 1,
    total_lexemes: 1,
    total_statements: 1,
    total_terms: 1,
  }),
  getEditStats: vi.fn().mockResolvedValue({
    edits_7d: 0,
    edits_30d: 0,
    edits_total: 0,
  }),
}))

vi.mock('../api.js', () => apiMocks)

import App from '../App.vue'
import router from '../router.js'
import { loginState, logoutState } from './helpers'

async function mountApp(path = '/') {
  await router.push(path)
  const wrapper = mount(App, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

beforeEach(async () => {
  vi.clearAllMocks()
  logoutState()
  await router.push('/').then(() => router.isReady())
})

afterEach(() => {
  logoutState()
})

describe('Create menu', () => {
  it('links to the three create pages', async () => {
    const wrapper = await mountApp()

    expect(wrapper.find('[data-testid="create-menu-item"]').attributes('href')).toBe(
      '/create-item'
    )
    expect(
      wrapper.find('[data-testid="create-menu-property"]').attributes('href')
    ).toBe('/create-property')
    expect(
      wrapper.find('[data-testid="create-menu-lexeme"]').attributes('href')
    ).toBe('/create-lexeme')
  })
})

describe('CreateItemView', () => {
  it('requires login: shows a log-in hint instead of the form', async () => {
    const wrapper = await mountApp('/create-item')

    expect(wrapper.find('[data-testid="item-label-input"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="login-required"]').exists()).toBe(true)
    expect(
      wrapper.find('[data-testid="login-required-link"]').attributes('href')
    ).toBe('/login')
  })

  it('creates an item and navigates to the entity view', async () => {
    loginState(90001)
    apiMocks.postItem.mockResolvedValue('Q500')
    apiMocks.putLabel.mockResolvedValue({ hash: 'x' })
    apiMocks.getEntityHistory.mockResolvedValue([])

    const wrapper = await mountApp('/create-item')
    await wrapper.find('[data-testid="item-label-input"]').setValue('E2E')
    await wrapper.find('[data-testid="create-item-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.postItem).toHaveBeenCalledWith({})
    expect(apiMocks.putLabel).toHaveBeenCalledWith('Q500', 'en', 'E2E')
    expect(router.currentRoute.value.path).toBe('/entity/Q500')
  })

  it('creates the label in the language chosen in the select', async () => {
    loginState(90001)
    apiMocks.postItem.mockResolvedValue('Q501')
    apiMocks.putLabel.mockResolvedValue({ hash: 'x' })

    const wrapper = await mountApp('/create-item')
    await wrapper.find('[data-testid="item-lang-select"]').setValue('sv')
    await wrapper.find('[data-testid="item-label-input"]').setValue('E2E sv')
    await wrapper.find('[data-testid="create-item-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.putLabel).toHaveBeenCalledWith('Q501', 'sv', 'E2E sv')
  })
})

describe('CreatePropertyView', () => {
  it('creates a property and navigates to the entity view', async () => {
    loginState(90001)
    apiMocks.postProperty.mockResolvedValue('P300')
    apiMocks.putLabel.mockResolvedValue({ hash: 'x' })
    apiMocks.getEntityHistory.mockResolvedValue([])

    const wrapper = await mountApp('/create-property')
    await wrapper.find('[data-testid="property-label-input"]').setValue('instance of')
    await wrapper.find('[data-testid="create-property-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.postProperty).toHaveBeenCalledWith({})
    expect(router.currentRoute.value.path).toBe('/entity/P300')
  })
})

describe('CreateLexemeView', () => {
  it('creates a lexeme and navigates to the entity view', async () => {
    loginState(90001)
    apiMocks.postLexeme.mockResolvedValue('L50')
    apiMocks.getEntityHistory.mockResolvedValue([])

    const wrapper = await mountApp('/create-lexeme')
    await wrapper.find('[data-testid="lemma-input"]').setValue('answer')
    await wrapper.find('[data-testid="create-lexeme-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.postLexeme).toHaveBeenCalledWith({
      type: 'lexeme',
      lemmas: { en: { language: 'en', value: 'answer' } },
      language: 'Q1860',
      lexical_category: 'Q1084',
    })
    expect(router.currentRoute.value.path).toBe('/entity/L50')
  })
})
