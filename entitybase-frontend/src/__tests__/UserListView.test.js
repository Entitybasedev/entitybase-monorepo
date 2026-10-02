import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const apiMocks = vi.hoisted(() => ({
  getUserList: vi.fn().mockResolvedValue({ users: [], count: 0 }),
}))

vi.mock('../api.js', () => apiMocks)

import UserListView from '../views/UserListView.vue'
import router from '../router.js'

function userRow(id, username = '') {
  return { user_id: id, username, created_at: '2026-01-01', last_activity: '2026-10-01' }
}

async function mountView(path = '/list-users') {
  await router.push(path)
  const wrapper = mount(UserListView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

beforeEach(async () => {
  vi.resetAllMocks()
  apiMocks.getUserList.mockResolvedValue({ users: [], count: 0 })
  await router.push('/').then(() => router.isReady())
})

describe('UserListView', () => {
  it('lists users with username, created and activity', async () => {
    apiMocks.getUserList.mockResolvedValue({
      users: [userRow(90001, 'ada'), userRow(90002, 'bob')],
      count: 2,
    })

    const wrapper = await mountView()

    expect(apiMocks.getUserList).toHaveBeenCalledWith(10, 0)
    const rows = wrapper.findAll('[data-testid="user-list-row"]')
    expect(rows).toHaveLength(2)
    const usernames = wrapper.findAll('[data-testid="user-list-username"]')
    expect(usernames[0].text()).toBe('ada')
    expect(wrapper.find('[data-testid="user-list-created"]').text()).toBe('2026-01-01')
    expect(wrapper.find('[data-testid="user-list-activity"]').text()).toBe('2026-10-01')
  })

  it('shows the import badge for the import user (0)', async () => {
    apiMocks.getUserList.mockResolvedValue({
      users: [userRow(0, 'import')],
      count: 1,
    })

    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="user-list-import-badge"]').text()).toBe('Import')
    expect(wrapper.find('[data-testid="user-list-username"]').exists()).toBe(false)
  })

  it('paginates: next goes to page 2 with offset 10, prev returns', async () => {
    apiMocks.getUserList.mockResolvedValue({
      users: Array.from({ length: 10 }, (_, i) => userRow(i + 1, `u${i}`)),
      count: 10,
    })

    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="user-list-prev"]').attributes('disabled')).toBeDefined()

    await wrapper.find('[data-testid="user-list-next"]').trigger('click')
    await flushPromises()

    expect(apiMocks.getUserList).toHaveBeenLastCalledWith(10, 10)
    expect(wrapper.find('[data-testid="user-list-page"]').text()).toBe('Page 2')
    expect(wrapper.find('[data-testid="user-list-prev"]').attributes('disabled')).toBeUndefined()
  })

  it('shows an empty state when there are no users', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="user-list-empty"]').exists()).toBe(true)
  })

  it('shows an error banner when loading fails', async () => {
    apiMocks.getUserList.mockRejectedValue(
      new Error('GET user list failed: 500 boom')
    )

    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="user-list-error"]').text()).toContain('500')
  })
})
