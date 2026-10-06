import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { loginState, logoutState } from './helpers'

const apiMocks = vi.hoisted(() => ({
  getItem: vi.fn(),
  entityJsonUrl: (id) => `/v1/entities/${id}.json`,
  entityNormalizedJsonUrl: (id) => `/v1/entities/${id}.njson`,
  entityRdfUrl: (id) => `/v1/entities/${id}.ttl`,
  getStatement: vi.fn(),
  getSnak: vi.fn(),
  getLabelWithFallback: vi.fn().mockResolvedValue(null),
  getDescriptionWithFallback: vi.fn().mockResolvedValue(null),
  getAliasesWithFallback: vi.fn().mockResolvedValue([]),
  getLabel: vi.fn(),
  getDescription: vi.fn(),
  getAliases: vi.fn(),
  getUserSettings: vi.fn().mockResolvedValue({}),
  getLexemeSenses: vi.fn(),
  getLexemeForms: vi.fn(),
  postLexemeSense: vi.fn().mockResolvedValue('L42'),
  postLexemeForm: vi.fn().mockResolvedValue('L42'),
  deleteStatement: vi.fn(),
  postStatement: vi.fn(),
}))

vi.mock('../api.js', () => apiMocks)

import EntitiesView from '../views/EntitiesView.vue'
import router from '../router.js'

function lexemePayload(id = 'L42') {
  return {
    id,
    rev_id: 2,
    data: {
      schema: '4.0.0',
      revision: {
        id,
        entity_type: 'lexeme',
        lemmas: { en: { language: 'en', value: 'answer' }, sv: { language: 'sv', value: 'svar' } },
        language: 'Q1860',
        lexical_category: 'Q1084',
        hashes: { statements: [] },
      },
    },
  }
}

async function mountAt(path, mocks = {}) {
  Object.assign(apiMocks, mocks)
  await router.push(path)
  const wrapper = mount(EntitiesView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  window.history.replaceState(null, '', '/')
})

describe('LexemeView', () => {
  it('shows lemmas, language and lexical category instead of labels', async () => {
    apiMocks.getLabelWithFallback.mockImplementation(async (id) => {
      if (id === 'Q1860') return 'English'
      if (id === 'Q1084') return 'noun'
      return ''
    })
    apiMocks.getItem.mockResolvedValue(lexemePayload())
    apiMocks.getLexemeSenses.mockResolvedValue([])
    apiMocks.getLexemeForms.mockResolvedValue([])

    const wrapper = await mountAt('/entity/L42')

    const lemmas = wrapper.findAll('[data-testid="lexeme-lemma"]')
    expect(lemmas.map((n) => n.text())).toEqual(['answer', 'svar'])
    expect(wrapper.find('[data-testid="lexeme-language"]').text()).toBe('English')
    expect(wrapper.find('[data-testid="lexeme-category"]').text()).toBe('noun')

    // Labels/descriptions/aliases are not part of a lexeme
    expect(wrapper.find('[data-testid="item-label"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="edit-aliases-button"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="item-type-badge"]').text()).toBe('Lexeme')
  })

  it('renders senses with their glosses and statements', async () => {
    apiMocks.getLabelWithFallback.mockResolvedValue('')
    apiMocks.getItem.mockResolvedValue(lexemePayload())
    apiMocks.getLexemeSenses.mockResolvedValue([
      {
        id: 'L42-S1',
        glosses: { en: { language: 'en', value: 'reply; reaction to a question' } },
        claims: {
          P31: [
            {
              mainsnak: {
                snaktype: 'value',
                property: 'P31',
                datavalue: { value: { id: 'Q5' }, type: 'wikibase-item' },
              },
            },
          ],
        },
      },
    ])
    apiMocks.getLexemeForms.mockResolvedValue([])

    const wrapper = await mountAt('/entity/L42')

    expect(wrapper.find('[data-testid="lexeme-sense"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="lexeme-gloss"]').text()).toBe(
      'reply; reaction to a question'
    )
    // The sense's own statement is grouped under its property
    const senseStatements = wrapper.findAll(
      '[data-testid="lexeme-sense-statements"] [data-testid="statement-group"]'
    )
    expect(senseStatements).toHaveLength(1)
    expect(senseStatements[0].attributes('id')).toBe('P31')
  })

  it('renders forms with representations, features and statements', async () => {
    apiMocks.getLabelWithFallback.mockImplementation(async (id) =>
      id === 'Q110786' ? 'plural' : ''
    )
    apiMocks.getItem.mockResolvedValue(lexemePayload())
    apiMocks.getLexemeSenses.mockResolvedValue([])
    apiMocks.getLexemeForms.mockResolvedValue([
      {
        id: 'L42-F1',
        representations: { en: { language: 'en', value: 'answers' } },
        // The API serialises this field under its alias
        grammaticalFeatures: ['Q110786'],
        claims: {},
      },
    ])

    const wrapper = await mountAt('/entity/L42')

    expect(wrapper.find('[data-testid="lexeme-form"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="lexeme-representation"]').text()).toBe('answers')
    expect(wrapper.find('[data-testid="lexeme-grammatical-features"]').text()).toBe(
      'plural'
    )
  })

  it('shows empty states when a lexeme has no senses or forms', async () => {
    apiMocks.getLabelWithFallback.mockResolvedValue('')
    apiMocks.getItem.mockResolvedValue(lexemePayload())
    apiMocks.getLexemeSenses.mockResolvedValue([])
    apiMocks.getLexemeForms.mockResolvedValue([])

    const wrapper = await mountAt('/entity/L42')

    expect(wrapper.find('[data-testid="lexeme-no-senses"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="lexeme-no-forms"]').exists()).toBe(true)
  })

  it('offers no add buttons to anonymous visitors', async () => {
    logoutState()
    apiMocks.getLabelWithFallback.mockResolvedValue('')
    apiMocks.getItem.mockResolvedValue(lexemePayload())
    apiMocks.getLexemeSenses.mockResolvedValue([])
    apiMocks.getLexemeForms.mockResolvedValue([])

    const wrapper = await mountAt('/entity/L42')

    expect(wrapper.find('[data-testid="new-sense-button"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="new-form-button"]').exists()).toBe(false)
  })

  it('adds a sense from a gloss and its language', async () => {
    loginState(90001)
    apiMocks.getLabelWithFallback.mockResolvedValue('')
    apiMocks.getItem.mockResolvedValue(lexemePayload())
    apiMocks.getLexemeSenses.mockResolvedValue([])
    apiMocks.getLexemeForms.mockResolvedValue([])

    const wrapper = await mountAt('/entity/L42')
    await wrapper.find('[data-testid="new-sense-button"]').trigger('click')
    await wrapper.find('[data-testid="sense-gloss-lang-select"]').setValue('de')
    await wrapper.find('[data-testid="sense-gloss-input"]').setValue('schnell laufen')
    await wrapper.find('[data-testid="add-sense-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.postLexemeSense).toHaveBeenCalledWith('L42', {
      glosses: { de: { language: 'de', value: 'schnell laufen' } },
    })
    // The editor closes and the list is reloaded
    expect(wrapper.find('[data-testid="sense-gloss-input"]').exists()).toBe(false)
    logoutState()
  })

  it('refuses to add a sense without a gloss', async () => {
    loginState(90001)
    apiMocks.getLabelWithFallback.mockResolvedValue('')
    apiMocks.getItem.mockResolvedValue(lexemePayload())
    apiMocks.getLexemeSenses.mockResolvedValue([])
    apiMocks.getLexemeForms.mockResolvedValue([])

    const wrapper = await mountAt('/entity/L42')
    await wrapper.find('[data-testid="new-sense-button"]').trigger('click')
    await wrapper.find('[data-testid="sense-gloss-input"]').setValue('   ')
    await wrapper.find('[data-testid="add-sense-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.postLexemeSense).not.toHaveBeenCalled()
    logoutState()
  })

  it('surfaces a failed sense creation', async () => {
    loginState(90001)
    apiMocks.getLabelWithFallback.mockResolvedValue('')
    apiMocks.getItem.mockResolvedValue(lexemePayload())
    apiMocks.getLexemeSenses.mockResolvedValue([])
    apiMocks.getLexemeForms.mockResolvedValue([])
    apiMocks.postLexemeSense.mockRejectedValueOnce(new Error('400 gloss required'))

    const wrapper = await mountAt('/entity/L42')
    await wrapper.find('[data-testid="new-sense-button"]').trigger('click')
    await wrapper.find('[data-testid="sense-gloss-input"]').setValue('x')
    await wrapper.find('[data-testid="add-sense-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="add-sense-error"]').text()).toContain(
      'gloss required'
    )
    // The error also bubbles up to the view shell
    expect(wrapper.find('[data-testid="error-banner"]').text()).toContain(
      'gloss required'
    )
    logoutState()
  })

  it('adds a form with grammatical features entered as chips', async () => {
    loginState(90001)
    apiMocks.getLabelWithFallback.mockImplementation(async (id) =>
      id === 'Q110786' ? 'plural' : ''
    )
    apiMocks.getItem.mockResolvedValue(lexemePayload())
    apiMocks.getLexemeSenses.mockResolvedValue([])
    apiMocks.getLexemeForms.mockResolvedValue([])

    const wrapper = await mountAt('/entity/L42')
    await wrapper.find('[data-testid="new-form-button"]').trigger('click')
    await wrapper.find('[data-testid="form-representation-input"]').setValue('answers')

    const featureInput = wrapper.find(
      '[data-testid="form-grammatical-feature-input"]'
    )
    await featureInput.setValue('Q110786, Q146786')
    await featureInput.trigger('keyup.enter')
    await flushPromises()

    // Committed as chips, showing the resolved labels
    const chips = wrapper.findAll('[data-testid="form-grammatical-feature-chip-Q110786"]')
    expect(chips).toHaveLength(1)
    expect(chips[0].text()).toContain('plural')
    expect(
      wrapper.find('[data-testid="form-grammatical-feature-chip-Q146786"]').exists()
    ).toBe(true)

    await wrapper.find('[data-testid="add-form-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.postLexemeForm).toHaveBeenCalledWith('L42', {
      representations: { en: { language: 'en', value: 'answers' } },
      grammaticalFeatures: ['Q110786', 'Q146786'],
    })
    logoutState()
  })

  it('adds a form without grammatical features and can drop a chip again', async () => {
    loginState(90001)
    apiMocks.getLabelWithFallback.mockResolvedValue('')
    apiMocks.getItem.mockResolvedValue(lexemePayload())
    apiMocks.getLexemeSenses.mockResolvedValue([])
    apiMocks.getLexemeForms.mockResolvedValue([])

    const wrapper = await mountAt('/entity/L42')
    await wrapper.find('[data-testid="new-form-button"]').trigger('click')

    const featureInput = wrapper.find(
      '[data-testid="form-grammatical-feature-input"]'
    )
    await featureInput.setValue('Q110786')
    await featureInput.trigger('keyup.enter')
    await flushPromises()
    await wrapper
      .find('[data-testid="form-grammatical-feature-remove-Q110786"]')
      .trigger('click')

    await wrapper.find('[data-testid="form-representation-input"]').setValue('answer')
    await wrapper.find('[data-testid="add-form-button"]').trigger('click')
    await flushPromises()

    expect(apiMocks.postLexemeForm).toHaveBeenCalledWith('L42', {
      representations: { en: { language: 'en', value: 'answer' } },
      grammaticalFeatures: [],
    })
    logoutState()
  })
})

describe('PropertyView', () => {
  it('hides aliases for properties but keeps label and statements', async () => {
    loginState(90001)
    apiMocks.getLabelWithFallback.mockResolvedValue('instance of')
    apiMocks.getItem.mockResolvedValue({
      id: 'P31',
      rev_id: 1,
      data: { revision: { id: 'P31', entity_type: 'property', hashes: { statements: [] } } },
    })
    apiMocks.getLexemeSenses.mockResolvedValue([])
    apiMocks.getLexemeForms.mockResolvedValue([])

    const wrapper = await mountAt('/entity/P31')

    expect(wrapper.find('[data-testid="item-label"]').text()).toBe('instance of')
    expect(wrapper.find('[data-testid="edit-label-button"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="edit-aliases-button"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="item-type-badge"]').text()).toBe('Property')
    // Properties still get the statement section
    expect(wrapper.find('[data-testid="statement-form"]').exists()).toBe(true)
  })
})