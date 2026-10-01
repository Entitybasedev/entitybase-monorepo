import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const authMocks = vi.hoisted(() => ({
  login: vi.fn(),
  register: vi.fn(),
}))

vi.mock('../auth.js', async () => {
  const { ref, computed } = await import('vue')
  return {
    login: authMocks.login,
    register: authMocks.register,
    userId: ref(0),
    username: ref(''),
    token: ref(''),
    isLoggedIn: computed(() => false),
    logout: vi.fn(),
    authHeaders: vi.fn(() => ({})),
  }
})

import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import UserMenu from '../components/UserMenu.vue'
import router from '../router.js'

async function mountView(view) {
  const wrapper = mount(view, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

beforeEach(async () => {
  vi.resetAllMocks()
  await router.push('/login').then(() => router.isReady())
})

describe('LoginView', () => {
  it('submits credentials and navigates home on success', async () => {
    authMocks.login.mockResolvedValue({ token: 't', user_id: 42, username: 'ada' })

    const wrapper = await mountView(LoginView)
    expect(wrapper.text()).toContain('Log in')

    await wrapper.find('[data-testid="username-input"]').setValue('ada')
    await wrapper.find('[data-testid="password-input"]').setValue('secret')
    await wrapper.find('[data-testid="auth-form"]').trigger('submit')
    await flushPromises()

    expect(authMocks.login).toHaveBeenCalledWith('ada', 'secret')
    expect(authMocks.register).not.toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/')
    expect(wrapper.find('[data-testid="auth-error"]').exists()).toBe(false)
  })

  it('shows the backend error message on failure', async () => {
    authMocks.login.mockRejectedValue(
      new Error('POST /v1/auth/login failed: 401 Invalid username or password')
    )

    const wrapper = await mountView(LoginView)
    await wrapper.find('[data-testid="username-input"]').setValue('ada')
    await wrapper.find('[data-testid="password-input"]').setValue('wrong')
    await wrapper.find('[data-testid="auth-form"]').trigger('submit')
    await flushPromises()

    const error = wrapper.find('[data-testid="auth-error"]')
    expect(error.exists()).toBe(true)
    expect(error.text()).toContain('401')
  })

  it('links to the register page instead of toggling inline', async () => {
    const wrapper = await mountView(LoginView)

    const link = wrapper.find('[data-testid="auth-switch-link"]')
    expect(link.attributes('href')).toBe('/register')

    await link.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/register')
  })
})

describe('RegisterView', () => {
  it('registers an account and navigates home on success', async () => {
    authMocks.register.mockResolvedValue({ token: 't', user_id: 43, username: 'bob' })

    const wrapper = await mountView(RegisterView)
    expect(wrapper.text()).toContain('Register')

    await wrapper.find('[data-testid="username-input"]').setValue('bob')
    await wrapper.find('[data-testid="password-input"]').setValue('secret')
    await wrapper.find('[data-testid="auth-form"]').trigger('submit')
    await flushPromises()

    expect(authMocks.register).toHaveBeenCalledWith('bob', 'secret')
    expect(authMocks.login).not.toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('shows the backend error message on failure', async () => {
    authMocks.register.mockRejectedValue(
      new Error('POST /v1/auth/register failed: 400 Username already taken')
    )

    const wrapper = await mountView(RegisterView)
    await wrapper.find('[data-testid="username-input"]').setValue('ada')
    await wrapper.find('[data-testid="password-input"]').setValue('secret')
    await wrapper.find('[data-testid="auth-form"]').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[data-testid="auth-error"]').text()).toContain('400')
  })

  it('links back to the login page', async () => {
    const wrapper = await mountView(RegisterView)

    const link = wrapper.find('[data-testid="auth-switch-link"]')
    expect(link.attributes('href')).toBe('/login')

    await link.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/login')
  })
})

describe('UserMenu > logged out', () => {
  it('shows links to both the login and register pages', async () => {
    const wrapper = mount(UserMenu, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.find('[data-testid="user-menu-login"]').attributes('href')).toBe('/login')
    expect(wrapper.find('[data-testid="user-menu-register"]').attributes('href')).toBe(
      '/register'
    )
  })
})
