import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { language, showQid } from '../settings.js'
import { loginState, logoutState } from './helpers'

enableAutoUnmount(afterEach)

const apiMocks = vi.hoisted(() => ({
  getItem: vi.fn(),
  entityJsonUrl: (id) => `/v1/entities/${id}.json`,
  entityRdfUrl: (id) => `/v1/entities/${id}.ttl`,
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
  deleteStatement: vi.fn(),
  putLabel: vi.fn(),
  putDescription: vi.fn(),
  putAliases: vi.fn(),
  getRecentChanges: vi.fn(),
  getEntityList: vi.fn(),
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
  getDeduplicationStats: vi.fn().mockResolvedValue({}),
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

  it('loads account settings only when logged in', async () => {
    // Settings belong to an account, so an anonymous visitor must not read
    // another user's (the API answers 401 without a token)
    await router.push('/?entity=Q42')
    apiMocks.getItem.mockResolvedValue(itemPayload('Q42', 'Douglas Adams'))
    apiMocks.getLabelWithFallback.mockResolvedValue('Douglas Adams')

    const anonymous = await mountApp()

    expect(apiMocks.getUserSettings).not.toHaveBeenCalled()
    anonymous.unmount()

    loginState(90007)
    const signedIn = await mountApp()

    expect(apiMocks.getUserSettings).toHaveBeenCalledWith(90007)
    signedIn.unmount()
    logoutState()
  })

  it('links to the entity history page', async () => {
    await router.push('/?entity=Q42')
    apiMocks.getItem.mockResolvedValue(itemPayload('Q42', 'Douglas Adams'))
    apiMocks.getLabelWithFallback.mockResolvedValue('Douglas Adams')

    const wrapper = await mountApp()
    const link = wrapper.find('[data-testid="item-history-link"]')
    expect(link.attributes('href')).toBe('/Q42/history')
  })

  it('links to the JSON and RDF representations of the entity', async () => {
    await router.push('/?entity=Q42')
    apiMocks.getItem.mockResolvedValue(itemPayload('Q42', 'Douglas Adams'))
    apiMocks.getLabelWithFallback.mockResolvedValue('Douglas Adams')

    const wrapper = await mountApp()
    const json = wrapper.find('[data-testid="item-json-link"]')
    const rdf = wrapper.find('[data-testid="item-rdf-link"]')
    expect(json.attributes('href')).toBe('/v1/entities/Q42.json')
    expect(rdf.attributes('href')).toBe('/v1/entities/Q42.ttl')
    // Raw data is served by the API, so it opens in a new tab
    expect(json.attributes('target')).toBe('_blank')
    expect(rdf.attributes('target')).toBe('_blank')
  })

  it('links to the all-terms page', async () => {
    await router.push('/?entity=Q42')
    apiMocks.getItem.mockResolvedValue(itemPayload('Q42', 'Douglas Adams'))
    apiMocks.getLabelWithFallback.mockResolvedValue('Douglas Adams')

    const wrapper = await mountApp()
    const link = wrapper.find('[data-testid="item-terms-link"]')
    expect(link.attributes('href')).toBe('/Q42/terms')
  })

  it('saves the label in the language chosen in the editor', async () => {
    loginState(90001)
    await router.push('/?entity=Q42')
    apiMocks.getItem
      .mockResolvedValueOnce(itemPayload('Q42', 'Old'))
      .mockResolvedValueOnce(itemPayload('Q42', 'Old'))
    apiMocks.getLabelWithFallback.mockResolvedValue('Old')
    // First load is the draft for the default editor language (en: none yet),
    // second load happens when the editor language switches to sv
    apiMocks.getLabel
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce('Gammal')
    apiMocks.putLabel.mockResolvedValue({ hash: 'x' })

    const wrapper = await mountApp()
    await wrapper.find('[data-testid="edit-label-button"]').trigger('click')
    await flushPromises()
    // Switching the editor language loads the existing term in that language
    await wrapper.find('[data-testid="label-lang-select"]').setValue('sv')
    await flushPromises()
    expect(wrapper.find('[data-testid="label-edit-input"]').element.value).toBe('Gammal')

    await wrapper.find('[data-testid="label-edit-input"]').setValue('Ny')
    await wrapper.find('[data-testid="save-label-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.putLabel).toHaveBeenCalledWith('Q42', 'sv', 'Ny')
  })

  it('saves the description in the language chosen in the editor', async () => {
    loginState(90001)
    await router.push('/?entity=Q42')
    apiMocks.getItem
      .mockResolvedValueOnce(itemPayload('Q42', 'T'))
      .mockResolvedValueOnce(itemPayload('Q42', 'T'))
    apiMocks.getLabelWithFallback.mockResolvedValue('T')
    apiMocks.getDescriptionWithFallback.mockResolvedValue('Old description')
    apiMocks.getDescription
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce('Gammal beskrivning')
    apiMocks.putDescription.mockResolvedValue({ hash: 'x' })

    const wrapper = await mountApp()
    await wrapper.find('[data-testid="edit-description-button"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="description-lang-select"]').setValue('sv')
    await flushPromises()
    expect(wrapper.find('[data-testid="description-edit-input"]').element.value).toBe(
      'Gammal beskrivning'
    )

    await wrapper.find('[data-testid="description-edit-input"]').setValue('Ny beskrivning')
    await wrapper.find('[data-testid="save-description-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.putDescription).toHaveBeenCalledWith('Q42', 'sv', 'Ny beskrivning')
  })

  it('shows the entity type badge for items, properties and lexemes', async () => {
    for (const [id, expected] of [['Q1', 'Item'], ['P2', 'Property'], ['L3', 'Lexeme']]) {
      await router.push(`/?entity=${id}`)
      apiMocks.getItem.mockResolvedValueOnce(itemPayload(id, 'X'))
      apiMocks.getLabelWithFallback.mockResolvedValue('X')

      const wrapper = await mountApp()
      expect(wrapper.find('[data-testid="item-type-badge"]').text()).toBe(expected)
      // The heading shows the ID; the type only appears in the badge
      const heading = wrapper.find('h1')
      expect(heading.element.childNodes[0].textContent.trim()).toBe(id)
      expect(heading.find('[data-testid="item-type-badge"]').exists()).toBe(true)
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
    apiMocks.getAliases
      .mockResolvedValueOnce(['Doug', 'Douglas Noel Adams'])
      .mockResolvedValue(['Doug', 'Douglas Noel Adams'])
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

    // Statements are grouped under an anchored property header
    expect(wrapper.find('[data-testid="statement-group"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="statement-group"]').attributes('id')).toBe('P31')
    expect(wrapper.find('[data-testid="statement"]').attributes('id')).toBe('P31-1')
  })

  it('groups statements by property with anchors per group and statement', async () => {
    loginState(90001)
    await router.push('/entity/Q1')
    apiMocks.getItem
      .mockResolvedValueOnce(itemPayload('Q1', 'Test', [777, 888, 999]))
      .mockResolvedValueOnce(itemPayload('Q1', 'Test', [777, 888, 999]))
    apiMocks.getLabelWithFallback.mockResolvedValue('Test')
    apiMocks.getStatement
      .mockResolvedValueOnce({
        schema: '1.0',
        hash: 777,
        statement: { id: 'S1', mainsnak: 551, type: 'statement', rank: 'normal' },
      })
      .mockResolvedValueOnce({
        schema: '1.0',
        hash: 888,
        statement: { id: 'S2', mainsnak: 552, type: 'statement', rank: 'normal' },
      })
      .mockResolvedValueOnce({
        schema: '1.0',
        hash: 999,
        statement: { id: 'S3', mainsnak: 553, type: 'statement', rank: 'normal' },
      })
    apiMocks.getSnak.mockImplementation(async (hash) => ({
      snaktype: 'value',
      property: hash === 553 ? 'P17' : 'P31',
      datavalue: {
        value: { id: hash === 552 ? 'Q30' : 'Q5' },
        type: 'wikibase-item',
      },
    }))
    apiMocks.getLabelWithFallback.mockImplementation(async (id) => {
      if (id === 'P31') return 'instance of'
      if (id === 'P17') return 'country'
      if (id === 'Q5') return 'human'
      if (id === 'Q30') return 'USA'
      return ''
    })

    const wrapper = await mountApp()
    await flushPromises()

    const groups = wrapper.findAll('[data-testid="statement-group"]')
    expect(groups).toHaveLength(2)
    expect(groups[0].attributes('id')).toBe('P31')
    expect(groups[0].find('[data-testid="statement-property"]').text()).toBe('instance of')
    expect(groups[0].find('[data-testid="statement-group-count"]').text()).toBe('2')
    expect(groups[1].attributes('id')).toBe('P17')

    const p31Statements = groups[0].findAll('[data-testid="statement"]')
    expect(p31Statements).toHaveLength(2)
    expect(p31Statements[0].attributes('id')).toBe('P31-1')
    expect(p31Statements[1].attributes('id')).toBe('P31-2')
    expect(p31Statements[1].find('[data-testid="statement-value"]').text()).toBe('USA')
  })

  it('edits a statement value by removing it and adding the new value', async () => {
    loginState(90001)
    await router.push('/entity/Q1')
    apiMocks.getItem
      .mockResolvedValueOnce(itemPayload('Q1', 'Test', [777]))
      .mockResolvedValueOnce(itemPayload('Q1', 'Test', [888]))
    apiMocks.getLabelWithFallback.mockResolvedValue('Test')
    apiMocks.getStatement.mockResolvedValue({
      schema: '1.0',
      hash: 777,
      statement: { id: 'S1', mainsnak: 555, type: 'statement', rank: 'normal' },
    })
    apiMocks.getSnak.mockResolvedValue({
      snaktype: 'value',
      property: 'P31',
      datavalue: { value: { id: 'Q5' }, type: 'wikibase-item' },
    })
    apiMocks.deleteStatement.mockResolvedValue({ success: true })
    apiMocks.postStatement.mockResolvedValue({ success: true })

    const wrapper = await mountApp()
    await flushPromises()

    // The editor starts prefilled with the current value
    await wrapper.find('[data-testid="statement-edit-button"]').trigger('click')
    await flushPromises()
    const input = wrapper.find('[data-testid="statement-edit-input"]')
    expect(input.element.value).toBe('Q5')

    await input.setValue('Q30')
    await wrapper.find('[data-testid="statement-save-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.deleteStatement).toHaveBeenCalledWith('Q1', '777')
    expect(apiMocks.postStatement).toHaveBeenCalledTimes(1)
    const [, body] = apiMocks.postStatement.mock.calls[0]
    expect(body.claim.mainsnak.property).toBe('P31')
    expect(body.claim.mainsnak.datavalue).toEqual({
      value: { id: 'Q30' },
      type: 'wikibase-item',
    })
    expect(wrapper.find('[data-testid="statement-edit-input"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="error-banner"]').exists()).toBe(false)
  })

  it('removes a statement', async () => {
    loginState(90001)
    await router.push('/entity/Q1')
    apiMocks.getItem
      .mockResolvedValueOnce(itemPayload('Q1', 'Test', [777]))
      .mockResolvedValueOnce(itemPayload('Q1', 'Test', []))
    apiMocks.getLabelWithFallback.mockResolvedValue('Test')
    apiMocks.getStatement.mockResolvedValue({
      schema: '1.0',
      hash: 777,
      statement: { id: 'S1', mainsnak: 555, type: 'statement', rank: 'normal' },
    })
    apiMocks.getSnak.mockResolvedValue({
      snaktype: 'value',
      property: 'P31',
      datavalue: { value: { id: 'Q5' }, type: 'wikibase-item' },
    })
    apiMocks.deleteStatement.mockResolvedValue({ success: true })

    const wrapper = await mountApp()
    await flushPromises()

    await wrapper.find('[data-testid="statement-remove-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.deleteStatement).toHaveBeenCalledWith('Q1', '777')
    expect(wrapper.find('[data-testid="statement"]').exists()).toBe(false)
  })

  it('keeps the editor open and reports a failure when removing fails', async () => {
    loginState(90001)
    await router.push('/entity/Q1')
    apiMocks.getItem.mockResolvedValue(itemPayload('Q1', 'Test', [777]))
    apiMocks.getLabelWithFallback.mockResolvedValue('Test')
    apiMocks.getStatement.mockResolvedValue({
      schema: '1.0',
      hash: 777,
      statement: { id: 'S1', mainsnak: 555, type: 'statement', rank: 'normal' },
    })
    apiMocks.getSnak.mockResolvedValue({
      snaktype: 'value',
      property: 'P31',
      datavalue: { value: { id: 'Q5' }, type: 'wikibase-item' },
    })
    apiMocks.deleteStatement.mockRejectedValue(new Error('DELETE failed: 500'))

    const wrapper = await mountApp()
    await flushPromises()

    await wrapper.find('[data-testid="statement-remove-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="error-banner"]').text()).toContain(
      'Could not remove the statement'
    )
    // The statement is still listed, so nothing looks lost
    expect(wrapper.find('[data-testid="statement"]').exists()).toBe(true)
  })

  it('says so when the value is removed but re-adding it fails', async () => {
    loginState(90001)
    await router.push('/entity/Q1')
    apiMocks.getItem
      .mockResolvedValueOnce(itemPayload('Q1', 'Test', [777]))
      .mockResolvedValueOnce(itemPayload('Q1', 'Test', []))
    apiMocks.getLabelWithFallback.mockResolvedValue('Test')
    apiMocks.getStatement.mockResolvedValue({
      schema: '1.0',
      hash: 777,
      statement: { id: 'S1', mainsnak: 555, type: 'statement', rank: 'normal' },
    })
    apiMocks.getSnak.mockResolvedValue({
      snaktype: 'value',
      property: 'P31',
      datavalue: { value: { id: 'Q5' }, type: 'wikibase-item' },
    })
    apiMocks.deleteStatement.mockResolvedValue({ success: true })
    apiMocks.postStatement.mockRejectedValue(new Error('POST failed: 409'))

    const wrapper = await mountApp()
    await flushPromises()

    await wrapper.find('[data-testid="statement-edit-button"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="statement-edit-input"]').setValue('Q30')
    await wrapper.find('[data-testid="statement-save-button"]').trigger('click')
    await flushPromises()

    const banner = wrapper.find('[data-testid="error-banner"]').text()
    expect(banner).toContain('Statement removed, but adding')
    expect(banner).toContain('Q30')
    // The draft stays so the edit can be retried
    expect(wrapper.find('[data-testid="statement-edit-input"]').element.value).toBe('Q30')
  })

  it('hides the statement edit controls when logged out', async () => {
    await router.push('/entity/Q1')
    apiMocks.getItem.mockResolvedValue(itemPayload('Q1', 'Test', [777]))
    apiMocks.getLabelWithFallback.mockResolvedValue('Test')
    apiMocks.getStatement.mockResolvedValue({
      schema: '1.0',
      hash: 777,
      statement: { id: 'S1', mainsnak: 555, type: 'statement', rank: 'normal' },
    })
    apiMocks.getSnak.mockResolvedValue({
      snaktype: 'value',
      property: 'P31',
      datavalue: { value: { id: 'Q5' }, type: 'wikibase-item' },
    })

    const wrapper = await mountApp()
    await flushPromises()

    expect(wrapper.find('[data-testid="statement-edit-button"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="statement-remove-button"]').exists()).toBe(false)
  })

  it('opens the alias editor only once the existing aliases are loaded', async () => {
    // Regression: a slow load used to resolve after the user had typed and
    // reset the draft, so the typed aliases were lost on save
    loginState(90001)
    await router.push('/entity/Q42')
    apiMocks.getItem.mockResolvedValue(itemPayload('Q42', 'T'))
    apiMocks.getLabelWithFallback.mockResolvedValue('T')
    apiMocks.getAliasesWithFallback.mockResolvedValue([])

    let resolveAliases
    apiMocks.getAliases.mockReturnValue(
      new Promise((resolve) => {
        resolveAliases = resolve
      })
    )

    const wrapper = await mountApp()
    await wrapper.find('[data-testid="edit-aliases-button"]').trigger('click')

    // The editor stays closed while the existing aliases are loading
    expect(wrapper.find('[data-testid="aliases-edit-input"]').exists()).toBe(false)

    resolveAliases(['from server'])
    await flushPromises()

    const input = wrapper.find('[data-testid="aliases-edit-input"]')
    expect(input.exists()).toBe(true)
    expect(wrapper.findAll('[data-testid="alias-slugs"] [class*="chip"]')).toHaveLength(1)

    // Typing now sticks: the draft is not reset by the (already finished) load
    await input.setValue('typed alias')
    await input.trigger('keyup.enter')
    expect(wrapper.findAll('[data-testid="alias-slugs"] [class*="chip"]')).toHaveLength(2)
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
