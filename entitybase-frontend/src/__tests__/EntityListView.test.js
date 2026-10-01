import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const apiMocks = vi.hoisted(() => ({
  getEntityList: vi.fn().mockResolvedValue({ entities: [], count: 0 }),
  getLabelWithFallback: vi.fn().mockResolvedValue(null),
}))

vi.mock('../api.js', () => apiMocks)

import EntityListView from '../views/EntityListView.vue'
import router from '../router.js'

function listRow(entityId, headRevision = 1, label = null) {
  return { entity_id: entityId, head_revision_id: headRevision }
}

async function mountView(path = '/list') {
  await router.push(path)
  const wrapper = mount(EntityListView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

beforeEach(async () => {
  vi.resetAllMocks()
  apiMocks.getEntityList.mockResolvedValue({ entities: [], count: 0 })
  apiMocks.getLabelWithFallback.mockResolvedValue(null)
  await router.push('/').then(() => router.isReady())
})

describe('EntityListView', () => {
  it('lists 10 items by default and labels them', async () => {
    const rows = Array.from({ length: 10 }, (_, i) => listRow(`Q${100 + i}`))
    apiMocks.getEntityList.mockResolvedValue({ entities: rows, count: 10 })
    apiMocks.getLabelWithFallback.mockResolvedValue('Universe')

    const wrapper = await mountView('/list?type=item&page=1')

    expect(apiMocks.getEntityList).toHaveBeenCalledWith('item', 10, 0)
    const links = wrapper.findAll('[data-testid="entity-list-link"]')
    expect(links).toHaveLength(10)
    expect(wrapper.find('[data-testid="entity-list-label"]').text()).toBe('Universe')
  })

  it('defaults to the item type when no query param is given', async () => {
    await mountView()
    expect(apiMocks.getEntityList).toHaveBeenCalledWith('item', 10, 0)
  })

  it('paginates: next goes to page 2 with offset 10, prev returns', async () => {
    apiMocks.getEntityList.mockResolvedValue({
      entities: Array.from({ length: 10 }, (_, i) => listRow(`Q${100 + i}`)),
      count: 10,
    })

    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="entity-list-prev"]').attributes('disabled')).toBeDefined()

    await wrapper.find('[data-testid="entity-list-next"]').trigger('click')
    await flushPromises()

    expect(apiMocks.getEntityList).toHaveBeenLastCalledWith('item', 10, 10)
    expect(wrapper.find('[data-testid="entity-list-page"]').text()).toBe('Page 2')
    expect(wrapper.find('[data-testid="entity-list-prev"]').attributes('disabled')).toBeUndefined()

    await wrapper.find('[data-testid="entity-list-prev"]').trigger('click')
    await flushPromises()
    expect(apiMocks.getEntityList).toHaveBeenLastCalledWith('item', 10, 0)
  })

  it('disables next when fewer than a full page is returned', async () => {
    apiMocks.getEntityList.mockResolvedValue({
      entities: [listRow('Q1')],
      count: 1,
    })

    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="entity-list-next"]').attributes('disabled')).toBeDefined()
  })

  it('switches the type filter and reloads', async () => {
    const wrapper = await mountView()
    apiMocks.getEntityList.mockResolvedValue({
      entities: [listRow('P31')],
      count: 1,
    })

    await wrapper.find('[data-testid="entity-type-select"]').setValue('property')
    await flushPromises()

    expect(apiMocks.getEntityList).toHaveBeenLastCalledWith('property', 10, 0)
    expect(router.currentRoute.value.query.type).toBe('property')
    expect(wrapper.find('[data-testid="entity-list-link"]').text()).toBe('P31')
  })

  it('shows an empty message when the type has no entities', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="entity-list-empty"]').exists()).toBe(true)
  })

  it('shows an error banner when loading fails', async () => {
    apiMocks.getEntityList.mockRejectedValue(
      new Error('GET entity list failed: 500 boom')
    )

    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="entity-list-error"]').text()).toContain('500')
  })
})
