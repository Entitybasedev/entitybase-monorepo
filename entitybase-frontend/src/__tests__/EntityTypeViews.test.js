import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { loginState } from './helpers'

const apiMocks = vi.hoisted(() => ({
  getItem: vi.fn(),
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