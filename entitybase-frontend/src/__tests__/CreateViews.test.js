import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const apiMocks = vi.hoisted(() => ({
  postItem: vi.fn(),
  postProperty: vi.fn(),
  postLexeme: vi.fn(),
  putLabel: vi.fn(),
}))

vi.mock('../api.js', () => apiMocks)

import App from '../App.vue'
import router from '../router.js'
import { logout } from '../auth.js'

async function mountApp(path = '/') {
  await router.push(path)
  const wrapper = mount(App, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

beforeEach(async () => {
  vi.resetAllMocks()
  logout()
  await router.push('/').then(() => router.isReady())
})

describe('Create menu', () => {
  it('opens from the nav and links to the three create pages', async () => {
    const wrapper = await mountApp()

    expect(wrapper.find('[data-testid="create-menu"]').exists()).toBe(false)
    await wrapper.find('[data-testid="nav-create"]').trigger('click')

    const menu = wrapper.find('[data-testid="create-menu"]')
    expect(menu.exists()).toBe(true)
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

  it('navigates to the create item page', async () => {
    await mountApp()
    await router.push('/create-item')
    await flushPromises()

    const wrapper = mount(App, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.find('[data-testid="create-item-section"]').exists()).toBe(true)
  })
})

describe('CreateItemView', () => {
  it('creates an item and navigates to the entity view', async () => {
    apiMocks.postItem.mockResolvedValue('Q500')
    apiMocks.putLabel.mockResolvedValue({ hash: 'x' })

    const wrapper = await mountApp('/create-item')
    await wrapper.find('[data-testid="item-label-input"]').setValue('E2E')
    await wrapper.find('[data-testid="create-item-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.postItem).toHaveBeenCalledWith({}, 90001)
    expect(apiMocks.putLabel).toHaveBeenCalledWith('Q500', 'en', 'E2E', 90001)
    expect(router.currentRoute.value.path).toBe('/')
    expect(router.currentRoute.value.query.entity).toBe('Q500')
  })
})

describe('CreatePropertyView', () => {
  it('creates a property and navigates to the entity view', async () => {
    apiMocks.postProperty.mockResolvedValue('P300')
    apiMocks.putLabel.mockResolvedValue({ hash: 'x' })

    const wrapper = await mountApp('/create-property')
    await wrapper.find('[data-testid="property-label-input"]').setValue('instance of')
    await wrapper.find('[data-testid="create-property-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.postProperty).toHaveBeenCalledWith({}, 90001)
    expect(router.currentRoute.value.query.entity).toBe('P300')
  })
})

describe('CreateLexemeView', () => {
  it('creates a lexeme and navigates to the entity view', async () => {
    apiMocks.postLexeme.mockResolvedValue('L50')

    const wrapper = await mountApp('/create-lexeme')
    await wrapper.find('[data-testid="lemma-input"]').setValue('answer')
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
    expect(router.currentRoute.value.query.entity).toBe('L50')
  })
})
