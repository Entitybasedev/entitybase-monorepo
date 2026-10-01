import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { fallbackChain, language } from '../settings.js'
import { logout } from '../auth.js'

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
    apiMocks.getUserSettings.mockResolvedValue({
      ui: { language: 'sv', fallbackChain: ['da', 'sv'] },
    })

    const wrapper = await mountSettings('42')

    expect(apiMocks.getUserSettings).toHaveBeenCalledWith(42)
    const chips = wrapper.findAll('[data-testid="settings-fallback-chip"]')
    expect(chips).toHaveLength(2)
    expect(chips[0].text()).toContain('da')
  })

  it('adds and removes fallback languages locally', async () => {
    const wrapper = await mountSettings('42')

    await wrapper.find('[data-testid="settings-fallback-add-select"]').setValue('da')
    expect(fallbackChain.value).toEqual(['da'])

    await wrapper.find('[data-testid="settings-fallback-remove-da"]').trigger('click')
    expect(fallbackChain.value).toEqual([])
  })

  it('saves settings for the route user', async () => {
    const wrapper = await mountSettings('42')
    await wrapper.find('[data-testid="settings-fallback-add-select"]').setValue('sv')
    await wrapper.find('[data-testid="settings-save"]').trigger('click')
    await flushPromises()

    expect(apiMocks.putUserSettings).toHaveBeenCalledWith(42, {
      ui: { language: 'en', fallbackChain: ['sv'] },
    })
    expect(wrapper.find('[data-testid="settings-saved"]').text()).toBe('Settings saved.')
  })

  it('shows an error when saving fails', async () => {
    apiMocks.putUserSettings.mockRejectedValue(
      new Error('PUT user settings 42 failed: 500 boom')
    )

    const wrapper = await mountSettings('42')
    await wrapper.find('[data-testid="settings-save"]').trigger('click')
    await flushPromises()

    const error = wrapper.find('[data-testid="settings-error"]')
    expect(error.exists()).toBe(true)
    expect(error.text()).toContain('500')
  })
})
