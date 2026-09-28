import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const apiMocks = vi.hoisted(() => ({
  getItem: vi.fn(),
  getLabel: vi.fn(),
  getStatement: vi.fn(),
  postItem: vi.fn(),
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

    const wrapper = await mountApp()

    expect(apiMocks.getItem).toHaveBeenCalledWith('Q42')
    expect(apiMocks.getLabel).toHaveBeenCalledWith('Q42', 'en')
    expect(wrapper.find('[data-testid="item-label"]').text()).toBe('Douglas Adams')
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
        mainsnak: {
          snaktype: 'value',
          property: 'P31',
          datavalue: { value: { id: 'Q5' }, type: 'wikibase-item' },
        },
        type: 'statement',
        rank: 'normal',
      },
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

    expect(window.location.search).toBe('?entity=Q1234')
  })
})
