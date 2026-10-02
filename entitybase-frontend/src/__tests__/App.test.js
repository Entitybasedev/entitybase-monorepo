import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { language, showQid } from '../settings.js'
import { loginState } from './helpers'

enableAutoUnmount(afterEach)

const apiMocks = vi.hoisted(() => ({
  getItem: vi.fn(),
  getLabel: vi.fn(),
  getDescription: vi.fn(),
  getAliases: vi.fn(),
  getSnak: vi.fn(),
  getStatement: vi.fn(),
  getEntityHistory: vi.fn(),
  getEntityRevision: vi.fn(),
  getStreamTopics: vi.fn(),
  getStreamHealth: vi.fn(),
  resolveLabels: vi.fn(),
  resolveDescriptions: vi.fn(),
  resolveAliases: vi.fn(),
  getLabelWithFallback: vi.fn().mockResolvedValue(null),
  getDescriptionWithFallback: vi.fn().mockResolvedValue(null),
  getAliasesWithFallback: vi.fn().mockResolvedValue([]),
  getUserSettings: vi.fn().mockResolvedValue({}),
  putUserSettings: vi.fn().mockResolvedValue({ stored: true }),
  postItem: vi.fn(),
  postProperty: vi.fn(),
  postLexeme: vi.fn(),
  postStatement: vi.fn(),
  putLabel: vi.fn(),
  putDescription: vi.fn(),
  putAliases: vi.fn(),
  getRecentChanges: vi.fn(),
  getEntityList: vi.fn(),
}))

vi.mock('../api.js', () => apiMocks)

import App from '../App.vue'
import router from '../router.js'
import { logout } from '../auth.js'

function itemPayload(id, label, statementHashes = []) {
  return {
    id,
    rev_id: 1,
    data: {
      schema: '4.0.0',
      hash: 123456789,
      created_at: '2025-01-01T00:00:00Z',
      revision: {
        id,
        hashes: { statements: statementHashes },
      },
    },
  }
}

async function mountApp() {
  const wrapper = mount(App, { global: { plugins: [router] } })
  await router.isReady()
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  window.history.replaceState(null, '', '/')
  logout()
  return router.push('/').then(() => router.isReady())
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('App', () => {
  it('loads an item from the ?entity= query param on mount', async () => {
    await router.push('/?entity=Q42')
    apiMocks.getItem.mockResolvedValue(itemPayload('Q42', 'Douglas Adams'))
    apiMocks.getLabelWithFallback.mockResolvedValue('Douglas Adams')
    apiMocks.getDescriptionWithFallback.mockResolvedValue('The author of the Hitchhiker trilogy')
    apiMocks.getAliasesWithFallback.mockResolvedValue(['Douglas Noel Adams'])

    const wrapper = await mountApp()

    expect(apiMocks.getItem).toHaveBeenCalledWith('Q42')
    expect(apiMocks.getLabelWithFallback).toHaveBeenCalledWith('Q42', ['en'])
    expect(wrapper.find('[data-testid="item-label"]').text()).toBe('Douglas Adams')
    expect(wrapper.find('[data-testid="item-description"]').text()).toBe(
      'The author of the Hitchhiker trilogy'
    )
    expect(wrapper.find('[data-testid="item-alias"]').text()).toBe('Douglas Noel Adams')
  })

  it('links to the entity history page', async () => {
    await router.push('/?entity=Q42')
    apiMocks.getItem.mockResolvedValue(itemPayload('Q42', 'Douglas Adams'))
    apiMocks.getLabelWithFallback.mockResolvedValue('Douglas Adams')

    const wrapper = await mountApp()
    const link = wrapper.find('[data-testid="item-history-link"]')
    expect(link.attributes('href')).toBe('/Q42/history')
  })

  it('shows the entity type badge for items, properties and lexemes', async () => {
    for (const [id, expected] of [['Q1', 'Item'], ['P2', 'Property'], ['L3', 'Lexeme']]) {
      await router.push(`/?entity=${id}`)
      apiMocks.getItem.mockResolvedValueOnce(itemPayload(id, 'X'))
      apiMocks.getLabelWithFallback.mockResolvedValue('X')

      const wrapper = await mountApp()
      expect(wrapper.find('[data-testid="item-type-badge"]').text()).toBe(expected)
      expect(wrapper.find('h2').text()).toContain(`${expected} ${id}`)
    }
  })

  it('edits the label: edit input, save, reload', async () => {
    loginState(90001)
    await router.push('/?entity=Q42')
    apiMocks.getItem
      .mockResolvedValueOnce(itemPayload('Q42', 'Old'))
      .mockResolvedValueOnce(itemPayload('Q42', 'New'))
    apiMocks.getLabelWithFallback
      .mockResolvedValueOnce('Old')
      .mockResolvedValueOnce('New')
    apiMocks.putLabel.mockResolvedValue({ hash: 'x' })
    apiMocks.getEntityHistory.mockResolvedValue([])

    const wrapper = await mountApp()
    await wrapper.find('[data-testid="edit-label-button"]').trigger('click')

    const input = wrapper.find('[data-testid="label-edit-input"]')
    expect(input.exists()).toBe(true)
    await input.setValue('New')
    await wrapper.find('[data-testid="save-label-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.putLabel).toHaveBeenCalledWith('Q42', 'en', 'New')
    expect(wrapper.find('[data-testid="item-label"]').text()).toBe('New')
  })

  it('edits the description: edit input, save, reload', async () => {
    loginState(90001)
    await router.push('/?entity=Q42')
    apiMocks.getItem
      .mockResolvedValueOnce(itemPayload('Q42', 'T'))
      .mockResolvedValueOnce(itemPayload('Q42', 'T'))
    apiMocks.getLabelWithFallback.mockResolvedValue('T')
    apiMocks.getDescriptionWithFallback
      .mockResolvedValueOnce('Old description')
      .mockResolvedValueOnce('New description')
    apiMocks.putDescription.mockResolvedValue({ hash: 'x' })
    apiMocks.getEntityHistory.mockResolvedValue([])

    const wrapper = await mountApp()
    await wrapper.find('[data-testid="edit-description-button"]').trigger('click')

    const input = wrapper.find('[data-testid="description-edit-input"]')
    expect(input.exists()).toBe(true)
    await input.setValue('New description')
    await wrapper.find('[data-testid="save-description-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.putDescription).toHaveBeenCalledWith('Q42', 'en', 'New description')
    expect(wrapper.find('[data-testid="item-description"]').text()).toBe('New description')
  })

  it('hides the edit buttons when logged out', async () => {
    await router.push('/?entity=Q42')
    apiMocks.getItem.mockResolvedValue(itemPayload('Q42', 'Douglas Adams'))
    apiMocks.getLabelWithFallback.mockResolvedValue('Douglas Adams')

    const wrapper = await mountApp()
    expect(wrapper.find('[data-testid="edit-label-button"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="edit-description-button"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="edit-aliases-button"]').exists()).toBe(false)
  })

  it('edits aliases: enter commits slugs, x removes them, save persists', async () => {
    loginState(90001)
    await router.push('/?entity=Q42')
    apiMocks.getItem
      .mockResolvedValueOnce(itemPayload('Q42', 'T'))
      .mockResolvedValueOnce(itemPayload('Q42', 'T'))
    apiMocks.getLabelWithFallback.mockResolvedValue('T')
    apiMocks.getAliasesWithFallback
      .mockResolvedValueOnce(['Doug', 'Douglas Noel Adams'])
      .mockResolvedValueOnce(['Doug', 'DNA'])
    apiMocks.putAliases.mockResolvedValue({ hashes: [] })
    apiMocks.getEntityHistory.mockResolvedValue([])

    const wrapper = await mountApp()
    const chips = wrapper.findAll('[data-testid="item-alias"]')
    expect(chips).toHaveLength(2)

    await wrapper.find('[data-testid="edit-aliases-button"]').trigger('click')
    // Existing aliases appear as committed slugs; input starts empty
    expect(wrapper.findAll('[data-testid="alias-slugs"] [class*="chip"]')).toHaveLength(2)
    const input = wrapper.find('[data-testid="aliases-edit-input"]')
    expect(input.element.value).toBe('')

    // Enter commits a slug and clears the input
    await input.setValue('DNA')
    await input.trigger('keyup.enter')
    expect(input.element.value).toBe('')
    // Duplicate (case-insensitive) is not added again
    await input.setValue('dna')
    await input.trigger('keyup.enter')
    const slugs = wrapper.findAll('[data-testid="alias-slugs"] [class*="chip"]')
    expect(slugs).toHaveLength(3)

    // x removes a committed slug
    await wrapper.find('[data-testid="alias-remove-Douglas Noel Adams"]').trigger('click')
    expect(wrapper.findAll('[data-testid="alias-slugs"] [class*="chip"]')).toHaveLength(2)

    // Save persists the committed slugs
    await wrapper.find('[data-testid="save-aliases-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.putAliases).toHaveBeenCalledWith('Q42', 'en', ['Doug', 'DNA'])
    expect(wrapper.findAll('[data-testid="item-alias"]')).toHaveLength(2)
  })

  it('adds a statement and renders human-readable property and value', async () => {
    loginState(90001)
    await router.push('/?entity=Q1')
    apiMocks.getItem
      .mockResolvedValueOnce(itemPayload('Q1', 'Test', []))
      .mockResolvedValueOnce(itemPayload('Q1', 'Test', [777]))
    apiMocks.getLabelWithFallback.mockImplementation(async (id) => {
      if (id === 'P31') return 'instance of'
      if (id === 'Q5') return 'human'
      return ''
    })
    apiMocks.getStatement.mockResolvedValue({
      schema: '1.0',
      hash: 777,
      statement: {
        id: 'S1',
        mainsnak: 555,
        type: 'statement',
        rank: 'normal',
      },
    })
    apiMocks.getSnak.mockResolvedValue({
      snaktype: 'value',
      property: 'P31',
      datavalue: { value: { id: 'Q5' }, type: 'wikibase-item' },
    })
    apiMocks.postStatement.mockResolvedValue({ success: true })

    const wrapper = await mountApp()
    await flushPromises()
    expect(wrapper.find('[data-testid="item-section"]').exists()).toBe(true)

    await wrapper.find('[data-testid="statement-property-input"]').setValue('P31')
    await wrapper.find('[data-testid="statement-value-input"]').setValue('Q5')
    await wrapper.find('[data-testid="statement-form"]').trigger('submit')
    await flushPromises()

    expect(apiMocks.postStatement).toHaveBeenCalledTimes(1)
    expect(apiMocks.getSnak).toHaveBeenCalledWith(555)
    const [, body] = apiMocks.postStatement.mock.calls[0]
    expect(body.claim.mainsnak.property).toBe('P31')
    expect(body.claim.mainsnak.datavalue).toEqual({
      value: { id: 'Q5' },
      type: 'wikibase-item',
    })
    expect(body.claim.type).toBe('statement')

    const statement = wrapper.find('[data-testid="statement"]')
    expect(statement.exists()).toBe(true)
    expect(wrapper.find('[data-testid="statement-property"]').text()).toBe('instance of')
    expect(wrapper.find('[data-testid="statement-value"]').text()).toBe('human')
  })

  it('shows a log-in hint instead of the statement form when logged out', async () => {
    await router.push('/?entity=Q1')
    apiMocks.getItem.mockResolvedValue(itemPayload('Q1', 'Test'))
    apiMocks.getLabelWithFallback.mockResolvedValue('Test')

    const wrapper = await mountApp()
    expect(wrapper.find('[data-testid="statement-form"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="login-required-edit"]').exists()).toBe(true)
  })
})

describe('App > show QID toggle', () => {
  beforeEach(async () => {
    await router.push('/?entity=Q42')
    language.value = 'en'
    showQid.value = false
    apiMocks.getItem.mockResolvedValue(itemPayload('Q42', 'Douglas Adams'))
    apiMocks.getLabelWithFallback.mockResolvedValue('Douglas Adams')
    apiMocks.getDescription.mockResolvedValue(null)
    apiMocks.getAliases.mockResolvedValue([])
  })

  it('appends the QID to the label when the setting is on', async () => {
    const wrapper = await mountApp()
    await flushPromises()

    expect(wrapper.find('[data-testid="item-label"]').text()).toBe('Douglas Adams')

    showQid.value = true
    await flushPromises()
    expect(wrapper.find('[data-testid="item-label"]').text()).toBe('Douglas Adams (Q42)')
    showQid.value = false
  })
})
