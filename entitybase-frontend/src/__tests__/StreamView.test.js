import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import StreamView from '../components/stream/StreamView.vue'

const apiMocks = vi.hoisted(() => ({
  getStreamTopics: vi.fn(),
  getStreamHealth: vi.fn(),
}))

vi.mock('../api.js', () => apiMocks)

function jsonResponse(body) {
  const text = JSON.stringify(body)
  return {
    ok: true,
    status: 200,
    text: () => Promise.resolve(text),
    json: () => Promise.resolve(body),
  }
}

class MockEventSource {
  static instances = []
  constructor(url) {
    this.url = url
    this.onopen = null
    this.onmessage = null
    this.onerror = null
    this.closed = false
    MockEventSource.instances.push(this)
  }
  close() {
    this.closed = true
  }
  open() {
    this.onopen?.()
  }
  receive(data) {
    this.onmessage?.({ data })
  }
  fail() {
    this.onerror?.()
  }
}

beforeEach(() => {
  MockEventSource.instances = []
  vi.stubGlobal('EventSource', MockEventSource)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

async function mountStream() {
  const wrapper = mount(StreamView)
  await flushPromises()
  return wrapper
}

describe('StreamView', () => {
  it('fetches topics and health on mount and selects entity_change', async () => {
    apiMocks.getStreamTopics.mockResolvedValue(['entity_change', 'entity_diff'])
    apiMocks.getStreamHealth.mockResolvedValue({
      status: 'ok',
      kafka: 'connected',
      backend_type: 'redpanda',
    })

    const wrapper = await mountStream()

    expect(apiMocks.getStreamTopics).toHaveBeenCalled()
    expect(apiMocks.getStreamHealth).toHaveBeenCalled()
    expect(wrapper.find('[data-testid="stream-topic-select"]').element.value).toBe(
      'entity_change'
    )
    expect(wrapper.find('[data-testid="stream-status"]').text()).toContain('ok')
  })

  it('connects to the stream and renders incoming messages as text', async () => {
    apiMocks.getStreamTopics.mockResolvedValue(['entity_change'])
    apiMocks.getStreamHealth.mockResolvedValue({ status: 'ok', kafka: 'connected' })

    const wrapper = await mountStream()
    await flushPromises()

    const source = MockEventSource.instances.at(-1)
    expect(source.url).toBe('/v1/streams/entity_change')
    source.open()
    source.receive(
      '{"data":{"entity_id":"Q1000","revision_id":1,"change_type":"edit"}}'
    )
    await flushPromises()

    const feed = wrapper.find('[data-testid="stream-feed"]')
    expect(feed.text()).toContain('Q1000')
  })

  it('applies offset, since and limit query params on reconnect', async () => {
    apiMocks.getStreamTopics.mockResolvedValue(['entity_change'])
    apiMocks.getStreamHealth.mockResolvedValue({ status: 'ok', kafka: 'connected' })

    const wrapper = await mountStream()
    await flushPromises()

    await wrapper.find('[data-testid="stream-offset-input"]').setValue('5')
    await wrapper
      .find('[data-testid="stream-since-input"]')
      .setValue('2026-03-05T12:00:00Z')
    await wrapper.find('[data-testid="stream-limit-input"]').setValue('10')
    await wrapper.find('[data-testid="stream-reconnect"]').trigger('click')
    await flushPromises()

    const source = MockEventSource.instances.at(-1)
    expect(source.url).toBe(
      '/v1/streams/entity_change?offset=5&since=2026-03-05T12:00:00Z&limit=10'
    )
  })

  it('pause stops buffering messages', async () => {
    apiMocks.getStreamTopics.mockResolvedValue(['entity_change'])
    apiMocks.getStreamHealth.mockResolvedValue({ status: 'ok', kafka: 'connected' })

    const wrapper = await mountStream()
    await flushPromises()

    await wrapper.find('[data-testid="stream-pause"]').setValue(true)

    const source = MockEventSource.instances.at(-1)
    source.open()
    source.receive('{"first":true}')
    source.receive('{"second":true}')
    await flushPromises()

    expect(wrapper.find('[data-testid="stream-feed"]').text()).not.toContain('first')
  })

  it('clear empties the feed', async () => {
    apiMocks.getStreamTopics.mockResolvedValue(['entity_change'])
    apiMocks.getStreamHealth.mockResolvedValue({ status: 'ok', kafka: 'connected' })

    const wrapper = await mountStream()
    await flushPromises()

    const source = MockEventSource.instances.at(-1)
    source.open()
    source.receive('{"a":1}')
    await flushPromises()
    expect(wrapper.find('[data-testid="stream-feed"]').text()).toContain('"a"')

    await wrapper.find('[data-testid="stream-clear"]').trigger('click')
    expect(wrapper.find('[data-testid="stream-feed"]').text()).not.toContain('"a"')
  })

  it('shows an error when topics cannot be loaded', async () => {
    apiMocks.getStreamTopics.mockRejectedValue(new Error('connection refused'))

    const wrapper = await mountStream()

    const errorBanner = wrapper.find('[data-testid="stream-error"]')
    expect(errorBanner.exists()).toBe(true)
    expect(errorBanner.text()).toContain('connection refused')
  })

  it('pretty print reformats incoming JSON', async () => {
    apiMocks.getStreamTopics.mockResolvedValue(['entity_change'])
    apiMocks.getStreamHealth.mockResolvedValue({ status: 'ok', kafka: 'connected' })

    const wrapper = await mountStream()
    await flushPromises()

    await wrapper.find('[data-testid="stream-pretty-print"]').setValue(true)

    const source = MockEventSource.instances.at(-1)
    source.open()
    source.receive('{"entity_id":"Q1000"}')
    await flushPromises()

    const feed = wrapper.find('[data-testid="stream-feed"]').text()
    expect(feed).toContain('{\n  "entity_id": "Q1000"\n}')
  })
})
