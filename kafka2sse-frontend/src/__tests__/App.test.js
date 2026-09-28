import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import App from '../App.vue'

describe('App.vue', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(App)
  })

  afterEach(() => {
    wrapper.unmount()
  })

  it('renders the title', () => {
    expect(wrapper.text()).toContain('Kafka2SSE')
  })

  it('has backend URL input', () => {
    const input = wrapper.find('input[type="text"]')
    expect(input.exists()).toBe(true)
  })

  it('has stream select', () => {
    const select = wrapper.find('select')
    expect(select.exists()).toBe(true)
  })

  it('has pretty print checkbox', () => {
    const checkbox = wrapper.find('input[type="checkbox"]')
    expect(checkbox.exists()).toBe(true)
  })

  it('has pause checkbox', () => {
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    const pauseCheckbox = checkboxes.find(() => 
      wrapper.html().includes('Pause')
    )
    expect(pauseCheckbox.exists()).toBe(true)
  })

  it('has copy button', () => {
    const buttons = wrapper.findAll('button')
    const copyButton = buttons.find(b => b.text() === 'Copy')
    expect(copyButton.exists()).toBe(true)
  })

  it('has clear button', () => {
    const buttons = wrapper.findAll('button')
    const clearButton = buttons.find(b => b.text() === 'Clear')
    expect(clearButton.exists()).toBe(true)
  })

  it('has refresh streams button', () => {
    const buttons = wrapper.findAll('button')
    const refreshButton = buttons.find(b => b.text() === 'Refresh Topics')
    expect(refreshButton.exists()).toBe(true)
  })

  it('has feed pre element', () => {
    const feed = wrapper.find('pre.feed')
    expect(feed.exists()).toBe(true)
  })
})
