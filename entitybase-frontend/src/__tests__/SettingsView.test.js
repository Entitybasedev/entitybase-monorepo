import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { fallbackChain, language, showQid } from '../settings.js'
import { logout } from '../auth.js'
import { loginState, logoutState } from './helpers'

const apiMocks = vi.hoisted(() => ({
  getUserSettings: vi.fn().mockResolvedValue({}),
  putUserSettings: vi.fn().mockResolvedValue({ stored: true }),
}))

vi.mock('../api.js', () => apiMocks)

import SettingsView from '../views/SettingsView.vue'
import router from '../router.js'

async function mountSettings(userId = '42') {
  await router.push(`/${userId}/settings`)
  const wrapper = mount(SettingsView, {
    global: { plugins: [router] },
    props: { userId: Number(userId) },
  })
  await flushPromises()
  return wrapper
}

beforeEach(async () => {
  vi.resetAllMocks()
  apiMocks.getUserSettings.mockResolvedValue({})
  apiMocks.putUserSettings.mockResolvedValue({ stored: true })
  logout()
  language.value = 'en'
  fallbackChain.value = []
  await router.push('/').then(() => router.isReady())
})

describe('SettingsView', () => {
  it('loads and shows the stored fallback chain', async () => {
    loginState(42)
    apiMocks.getUserSettings.mockResolvedValue({
      ui: { language: 'sv', fallbackChain: ['da', 'sv'] },
    })

    const wrapper = await mountSettings('42')

    expect(apiMocks.getUserSettings).toHaveBeenCalledWith(42)
    const chips = wrapper.findAll('[data-testid="settings-fallback-chip"]')
    expect(chips).toHaveLength(2)
    expect(chips[0].text()).toContain('da')
    logoutState()
  })

  it('adds and removes fallback languages locally', async () => {
    loginState(42)
    const wrapper = await mountSettings('42')

    await wrapper.find('[data-testid="settings-fallback-add-select"]').setValue('da')
    expect(fallbackChain.value).toEqual(['da'])

    await wrapper.find('[data-testid="settings-fallback-remove-da"]').trigger('click')
    expect(fallbackChain.value).toEqual([])
    logoutState()
  })

  it('saves settings for the signed-in user', async () => {
    loginState(42)
    const wrapper = await mountSettings('42')
    await wrapper.find('[data-testid="settings-fallback-add-select"]').setValue('sv')
    await wrapper.find('[data-testid="settings-save"]').trigger('click')
    await flushPromises()

    expect(apiMocks.putUserSettings).toHaveBeenCalledWith(42, {
      ui: { language: 'en', fallbackChain: ['sv'] },
    })
    expect(wrapper.find('[data-testid="settings-saved"]').text()).toBe('Settings saved.')
    logoutState()
  })

  it('loads and saves the signed-in user settings, not the route user', async () => {
    // Somebody else's settings page: the API would answer 403
    loginState(42)
    const wrapper = await mountSettings('90099')

    expect(apiMocks.getUserSettings).toHaveBeenCalledWith(42)
    expect(apiMocks.getUserSettings).not.toHaveBeenCalledWith(90099)

    await wrapper.find('[data-testid="settings-save"]').trigger('click')
    await flushPromises()
    expect(apiMocks.putUserSettings).toHaveBeenCalledWith(42, {
      ui: { language: 'en', fallbackChain: [] },
    })
    logoutState()
  })

  it('keeps settings in the browser when not logged in', async () => {
    // No token means no account to read or write; the API would answer 401
    const wrapper = await mountSettings('42')

    expect(wrapper.find('[data-testid="settings-not-logged-in"]').exists()).toBe(true)
    expect(apiMocks.getUserSettings).not.toHaveBeenCalled()

    await wrapper.find('[data-testid="settings-fallback-add-select"]').setValue('sv')
    await wrapper.find('[data-testid="settings-save"]').trigger('click')
    await flushPromises()

    expect(apiMocks.putUserSettings).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="settings-saved"]').text()).toContain(
      'this browser'
    )
    // The choice is still remembered locally
    expect(JSON.parse(localStorage.getItem('entitybase.fallbackChain'))).toEqual(['sv'])
    fallbackChain.value = []
  })

  it('shows an error when saving fails', async () => {
    loginState(42)
    apiMocks.putUserSettings.mockRejectedValue(
      new Error('PUT user settings 42 failed: 500 boom')
    )

    const wrapper = await mountSettings('42')
    await wrapper.find('[data-testid="settings-save"]').trigger('click')
    await flushPromises()

    const error = wrapper.find('[data-testid="settings-error"]')
    expect(error.exists()).toBe(true)
    expect(error.text()).toContain('500')
    logoutState()
  })

  it('has the language select and persists it to localStorage', async () => {
    loginState(42)
    const wrapper = await mountSettings('42')

    const select = wrapper.find('[data-testid="settings-language-select"]')
    expect(select.exists()).toBe(true)

    await select.setValue('de')
    expect(localStorage.getItem('entitybase.language')).toBe('de')
    language.value = 'en'
    logoutState()
  })

  it('has the show-IDs toggle and persists it to localStorage', async () => {
    loginState(42)
    const wrapper = await mountSettings('42')

    const toggle = wrapper.find('[data-testid="settings-show-qid-toggle"]')
    expect(toggle.exists()).toBe(true)

    await toggle.setValue(true)
    expect(localStorage.getItem('entitybase.showQid')).toBe('true')
    showQid.value = false
    logoutState()
  })
})
