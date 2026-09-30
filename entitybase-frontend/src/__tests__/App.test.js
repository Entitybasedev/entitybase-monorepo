import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

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
  postItem: vi.fn(),
  postProperty: vi.fn(),
  postLexeme: vi.fn(),
  postStatement: vi.fn(),
  putLabel: vi.fn(),
}))

vi.mock('../api.js', () => apiMocks)

import App from '../App.vue'

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
  const wrapper = mount(App)
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  window.history.replaceState(null, '', '/')
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('App', () => {
  it('renders the create form and disables the button without a label', async () => {
    const wrapper = await mountApp()

    expect(wrapper.find('[data-testid="create-item-section"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="item-section"]').exists()).toBe(false)

    const button = wrapper.find('[data-testid="create-item-button"]')
    expect(button.attributes('disabled')).toBeDefined()

    await wrapper.find('[data-testid="item-label-input"]').setValue('Universe')
    expect(button.attributes('disabled')).toBeUndefined()
  })

  it('loads an item from the ?entity= query param on mount', async () => {
    window.history.replaceState(null, '', '/?entity=Q42')
    apiMocks.getItem.mockResolvedValue(itemPayload('Q42', 'Douglas Adams'))
    apiMocks.getLabel.mockResolvedValue('Douglas Adams')
    apiMocks.getDescription.mockResolvedValue('The author of the Hitchhiker trilogy')
    apiMocks.getAliases.mockResolvedValue(['Douglas Noel Adams'])

    const wrapper = await mountApp()

    expect(apiMocks.getItem).toHaveBeenCalledWith('Q42')
    expect(apiMocks.getLabel).toHaveBeenCalledWith('Q42', 'en')
    expect(wrapper.find('[data-testid="item-label"]').text()).toBe('Douglas Adams')
    expect(wrapper.find('[data-testid="item-description"]').text()).toBe(
      'The author of the Hitchhiker trilogy'
    )
    expect(wrapper.find('[data-testid="item-alias"]').text()).toBe('Douglas Noel Adams')
  })

  it('creates an item: posts item, sets label, then loads it', async () => {
    apiMocks.postItem.mockResolvedValue('Q1000')
    apiMocks.putLabel.mockResolvedValue({ hash: 'x' })
    apiMocks.getItem.mockResolvedValue(itemPayload('Q1000', 'E2E Item'))
    apiMocks.getLabel.mockResolvedValue('E2E Item')

    const wrapper = await mountApp()
    await wrapper.find('[data-testid="item-label-input"]').setValue('E2E Item')
    await wrapper.find('[data-testid="user-id-input"]').setValue('90001')
    await wrapper.find('[data-testid="create-item-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.postItem).toHaveBeenCalledWith({}, 90001)
    expect(apiMocks.putLabel).toHaveBeenCalledWith('Q1000', 'en', 'E2E Item', 90001)
    expect(apiMocks.getItem).toHaveBeenCalledWith('Q1000')

    const itemSection = wrapper.find('[data-testid="item-section"]')
    expect(itemSection.exists()).toBe(true)
    expect(wrapper.find('[data-testid="item-label"]').text()).toBe('E2E Item')
    expect(wrapper.find('[data-testid="no-statements"]').exists()).toBe(true)
  })

  it('adds a statement and renders property and value', async () => {
    window.history.replaceState(null, '', '/?entity=Q1')
    apiMocks.getItem
      .mockResolvedValueOnce(itemPayload('Q1', 'Test', []))
      .mockResolvedValueOnce(itemPayload('Q1', 'Test', [777]))
    apiMocks.getLabel.mockResolvedValue('Test')
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
    const [, body, userId] = apiMocks.postStatement.mock.calls[0]
    expect(body.claim.mainsnak.property).toBe('P31')
    expect(body.claim.mainsnak.datavalue).toEqual({
      value: { id: 'Q5' },
      type: 'wikibase-item',
    })
    expect(body.claim.type).toBe('statement')
    expect(userId).toBe(90001)

    const statement = wrapper.find('[data-testid="statement"]')
    expect(statement.exists()).toBe(true)
    expect(wrapper.find('[data-testid="statement-property"]').text()).toBe('P31')
    expect(wrapper.find('[data-testid="statement-value"]').text()).toBe('Q5')
  })

  it('shows the error banner when item creation fails', async () => {
    apiMocks.postItem.mockRejectedValue(new Error('POST failed: 500'))

    const wrapper = await mountApp()
    await wrapper.find('[data-testid="item-label-input"]').setValue('X')
    await wrapper.find('[data-testid="create-item-button"]').trigger('click')
    await flushPromises()

    const banner = wrapper.find('[data-testid="error-banner"]')
    expect(banner.exists()).toBe(true)
    expect(banner.text()).toContain('500')
  })

  it('updates the URL with ?entity=<id> after creating an item', async () => {
    apiMocks.postItem.mockResolvedValue('Q1234')
    apiMocks.putLabel.mockResolvedValue({ hash: 'x' })
    apiMocks.getItem.mockResolvedValue(itemPayload('Q1234', 'Named'))

    const wrapper = await mountApp()
    await wrapper.find('[data-testid="item-label-input"]').setValue('Named')
    await wrapper.find('[data-testid="create-item-button"]').trigger('click')
    await flushPromises()

    expect(window.location.search).toBe('?tab=entities&entity=Q1234')
  })
})

describe('App > create property', () => {
  it('posts a property, sets its label, and loads it', async () => {
    apiMocks.postProperty.mockResolvedValue('P30000')
    apiMocks.putLabel.mockResolvedValue({ hash: 'x' })
    apiMocks.getItem.mockResolvedValue(itemPayload('P30000', 'instance of'))
    apiMocks.getLabel.mockResolvedValue('instance of')

    const wrapper = await mountApp()
    await wrapper.find('[data-testid="property-label-input"]').setValue('instance of')
    await wrapper.find('[data-testid="create-property-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.postProperty).toHaveBeenCalledWith({}, 90001)
    expect(apiMocks.putLabel).toHaveBeenCalledWith('P30000', 'en', 'instance of', 90001)
    expect(apiMocks.getItem).toHaveBeenCalledWith('P30000')
    expect(wrapper.find('[data-testid="item-label"]').text()).toBe('instance of')
    expect(window.location.search).toBe('?tab=entities&entity=P30000')
  })
})

describe('App > create lexeme', () => {
  it('posts a lexeme with lemmas and loads it', async () => {
    apiMocks.postLexeme.mockResolvedValue('L77')
    apiMocks.getItem.mockResolvedValue(itemPayload('L77', 'answer'))
    apiMocks.getLabel.mockResolvedValue('')

    const wrapper = await mountApp()
    await wrapper.find('[data-testid="lemma-input"]').setValue('answer')
    await wrapper.find('[data-testid="lexeme-language-input"]').setValue('Q1860')
    await wrapper.find('[data-testid="lexeme-category-input"]').setValue('Q1084')
    await wrapper.find('[data-testid="create-lexeme-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.postLexeme).toHaveBeenCalledWith(
      {
        type: 'lexeme',
        lemmas: { en: { language: 'en', value: 'answer' } },
        language: 'Q1860',
        lexical_category: 'Q1084',
      },
      90001
    )
    expect(apiMocks.getItem).toHaveBeenCalledWith('L77')
    expect(wrapper.find('[data-testid="item-section"]').exists()).toBe(true)
    expect(window.location.search).toBe('?tab=entities&entity=L77')
  })
})

describe('App > entity history', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/?entity=Q1')
    apiMocks.getItem.mockResolvedValue(itemPayload('Q1', 'Test', []))
    apiMocks.getLabel.mockResolvedValue('Test')
    apiMocks.getDescription.mockResolvedValue(null)
    apiMocks.getAliases.mockResolvedValue([])
  })

  it('loads and renders the revision history', async () => {
    apiMocks.getEntityHistory.mockResolvedValue([
      { revision_id: 2, created_at: '2026-01-02T00:00:00Z', user_id: 90001, edit_summary: 'Added label' },
      { revision_id: 1, created_at: '2026-01-01T00:00:00Z', user_id: 90001, edit_summary: '' },
    ])

    const wrapper = await mountApp()
    await flushPromises()

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
    apiMocks.getEntityRevision.mockResolvedValue(itemPayload('Q1', 'Old label'))

    const wrapper = await mountApp()
    await flushPromises()
    await wrapper.find('[data-testid="history-view"]').trigger('click')
    await flushPromises()

    expect(apiMocks.getEntityRevision).toHaveBeenCalledWith('Q1', 2)
    expect(wrapper.find('[data-testid="revision-banner"]').text()).toContain('Viewing revision 2')

    await wrapper.find('[data-testid="back-to-current"]').trigger('click')
    await flushPromises()
    expect(apiMocks.getItem).toHaveBeenCalledWith('Q1')
    expect(wrapper.find('[data-testid="revision-banner"]').exists()).toBe(false)
  })

  it('shows a diff against the previous revision', async () => {
    apiMocks.getEntityHistory.mockResolvedValue([
      { revision_id: 2, created_at: '', user_id: 1, edit_summary: 'edit' },
      { revision_id: 1, created_at: '', user_id: 1, edit_summary: 'create' },
    ])
    apiMocks.getEntityRevision
      .mockResolvedValueOnce(itemPayload('Q1', 'Test', [11]))
      .mockResolvedValueOnce(itemPayload('Q1', 'Test', [10]))
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

    const wrapper = await mountApp()
    await flushPromises()
    await wrapper.find('[data-testid="history-diff"]').trigger('click')
    await flushPromises()

    expect(apiMocks.getEntityRevision).toHaveBeenCalledWith('Q1', 2)
    expect(apiMocks.getEntityRevision).toHaveBeenCalledWith('Q1', 1)
    const diffView = wrapper.find('[data-testid="diff-view"]')
    expect(diffView.exists()).toBe(true)
    expect(wrapper.find('[data-testid="diff-added"]').text()).toContain('P31: Q5')
    expect(wrapper.find('[data-testid="diff-removed"]').text()).toContain('− P31: Q5')
  })
})
