import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import App from '../src/App.vue'

describe('App.vue', () => {
  it('renders logo and title', () => {
    const wrapper = mount(App)
    expect(wrapper.find('h1').text()).toBe('Entitybase Orchestrator')
  })

  it('renders all sections', () => {
    const wrapper = mount(App)
    const sections = wrapper.findAll('section')
    expect(sections.length).toBe(3) // Infrastructure, Event Streaming, Workers (no separate Services)
  })

  it('renders infrastructure section', () => {
    const wrapper = mount(App)
    const h2s = wrapper.findAll('h2')
    expect(h2s[0].text()).toBe('Infrastructure')
  })

  it('renders event streaming section', () => {
    const wrapper = mount(App)
    const h2s = wrapper.findAll('h2')
    expect(h2s[1].text()).toBe('Event Streaming')
  })

  it('renders workers section', () => {
    const wrapper = mount(App)
    const h2s = wrapper.findAll('h2')
    expect(h2s[2].text()).toBe('Workers')
  })
})
