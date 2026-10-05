import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { valueInputFor, valueInputForId } from '../components/property_types/index.js'
import ItemValueInput from '../components/property_types/ItemValueInput.vue'
import StringValueInput from '../components/property_types/StringValueInput.vue'
import { propertyTypeLabel } from '../property_types/labels.js'

const ITEM_TYPE = {
  id: 'wikibase-item',
  label: 'Item',
  value_kind: 'entity',
  value_label: 'Value item',
  value_placeholder: 'Q5',
}
const STRING_TYPE = {
  id: 'string',
  label: 'String',
  value_kind: 'text',
  value_label: 'Value',
  value_placeholder: 'a short text',
}

describe('property type registry', () => {
  it('maps each datatype to its own value input', () => {
    expect(valueInputFor(ITEM_TYPE)).toBe(ItemValueInput)
    expect(valueInputFor(STRING_TYPE)).toBe(StringValueInput)
  })

  it('looks a component up by bare datatype id', () => {
    expect(valueInputForId('string')).toBe(StringValueInput)
    expect(valueInputForId('wikibase-item')).toBe(ItemValueInput)
  })

  it('falls back to the value kind for a type with no component yet', () => {
    const future = { id: 'quantity', value_kind: 'text' }

    expect(valueInputFor(future)).toBe(StringValueInput)
  })

  it('returns nothing for an unknown type', () => {
    expect(valueInputFor({ id: 'mystery', value_kind: 'other' })).toBeNull()
    expect(valueInputFor(null)).toBeNull()
    expect(valueInputForId('mystery')).toBeNull()
  })
})

describe('property type labels', () => {
  it('names the types it knows and passes anything else through', () => {
    expect(propertyTypeLabel('wikibase-item')).toBe('Item')
    expect(propertyTypeLabel('string')).toBe('String')
    expect(propertyTypeLabel('quantity')).toBe('quantity')
    expect(propertyTypeLabel('')).toBe('')
  })
})

describe('ItemValueInput', () => {
  it('accepts an entity id', async () => {
    const wrapper = mount(ItemValueInput, {
      props: { modelValue: 'Q5' },
    })

    expect(wrapper.find('[data-testid="statement-value-input-error"]').exists()).toBe(
      false
    )
  })

  it('rejects something that is not an entity id', async () => {
    const wrapper = mount(ItemValueInput, {
      props: { modelValue: 'not an id' },
    })

    expect(wrapper.find('[data-testid="statement-value-input-error"]').text()).toContain(
      'not an entity id'
    )
  })

  it('emits the typed value', async () => {
    const wrapper = mount(ItemValueInput, { props: { modelValue: '' } })

    await wrapper.find('[data-testid="statement-value-input"]').setValue('Q42')

    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['Q42'])
  })
})

describe('StringValueInput', () => {
  it('accepts free text', async () => {
    const wrapper = mount(StringValueInput, {
      props: { modelValue: 'a short text' },
    })

    expect(wrapper.find('[data-testid="statement-value-input-error"]').exists()).toBe(
      false
    )
  })

  it('warns about a very long value', async () => {
    const wrapper = mount(StringValueInput, {
      props: { modelValue: 'x'.repeat(300) },
    })

    expect(wrapper.find('[data-testid="statement-value-input-error"]').text()).toContain(
      '250'
    )
  })
})