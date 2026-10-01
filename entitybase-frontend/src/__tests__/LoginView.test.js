import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const authMocks = vi.hoisted(() => ({
  login: vi.fn(),
  register: vi.fn(),
}))

vi.mock('../auth.js', () => ({
  login: authMocks.login,
  register: authMocks.register,
  userId: { value: 0 },
  username: { value: '' },
  token: { value: '' },
  isLoggedIn: { value: false },
  logout: vi.fn(),
  authHeaders: vi.fn(() => ({})),
}))

import LoginView from '../views/LoginView.vue'
import router from '../router.js'

async function mountView() {
  const wrapper = mount(LoginView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

beforeEach(async () => {
  vi.clearAllMocks()
  await router.push('/login').then(() => router.isReady())
})

describe('LoginView', () => {
  it('submits credentials and navigates home on success', async () => {
    authMocks.login.mockResolvedValue({ token: 't', user_id: 42, username: 'ada' })

    const wrapper = await mountView()
    await wrapper.find('[data-testid="username-input"]').setValue('ada')
    await wrapper.find('[data-testid="password-input"]').setValue('secret')
    await wrapper.find('[data-testid="login-form"]').trigger('submit')
    await flushPromises()

    expect(authMocks.login).toHaveBeenCalledWith('ada', 'secret')
    expect(router.currentRoute.value.path).toBe('/')
    expect(wrapper.find('[data-testid="login-error"]').exists()).toBe(false)
  })

  it('shows the backend error message on failure', async () => {
    authMocks.login.mockRejectedValue(new Error('POST /v1/auth/login failed: 401 Invalid username or password'))

    const wrapper = await mountView()
    await wrapper.find('[data-testid="username-input"]').setValue('ada')
    await wrapper.find('[data-testid="password-input"]').setValue('wrong')
    await wrapper.find('[data-testid="login-form"]').trigger('submit')
    await flushPromises()

    const error = wrapper.find('[data-testid="login-error"]')
    expect(error.exists()).toBe(true)
    expect(error.text()).toContain('401')
  })

  it('toggles to register mode and calls register', async () => {
    authMocks.register.mockResolvedValue({ token: 't', user_id: 43, username: 'bob' })

    const wrapper = await mountView()
    await wrapper.find('[data-testid="login-toggle-mode"]').trigger('click')
    expect(wrapper.text()).toContain('Register')

    await wrapper.find('[data-testid="username-input"]').setValue('bob')
    await wrapper.find('[data-testid="password-input"]').setValue('secret')
    await wrapper.find('[data-testid="login-form"]').trigger('submit')
    await flushPromises()

    expect(authMocks.register).toHaveBeenCalledWith('bob', 'secret')
  })
})
