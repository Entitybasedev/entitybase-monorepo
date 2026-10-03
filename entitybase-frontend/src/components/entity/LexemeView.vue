<template>
  <div>
    <div class="row">
      <span class="field-name">Lemmas</span>
      <ul class="lexeme-values" data-testid="lexeme-lemmas">
        <li
          v-for="(lemma, lang) in lemmas"
          :key="lang"
          data-testid="lexeme-lemma-row"
        >
          <span class="lang-code">{{ lang }}</span>
          <span data-testid="lexeme-lemma">{{ lemma.value }}</span>
        </li>
        <li v-if="!lemmas.length" data-testid="lexeme-no-lemmas">No lemmas.</li>
      </ul>
    </div>
    <div class="row">
      <span class="field-name">Language</span>
      <span data-testid="lexeme-language">{{ lexemeLanguageLabel || '—' }}</span>
    </div>
    <div class="row">
      <span class="field-name">Lexical category</span>
      <span data-testid="lexeme-category">{{ lexemeCategoryLabel || '—' }}</span>
    </div>

    <h3>Senses</h3>
    <div
      v-for="sense in senses"
      :key="sense.id"
      class="lexeme-block"
      data-testid="lexeme-sense"
    >
      <div class="field-name">{{ sense.id }}</div>
      <ul class="lexeme-values" data-testid="lexeme-sense-glosses">
        <li
          v-for="(gloss, lang) in sense.glosses"
          :key="lang"
          data-testid="lexeme-gloss-row"
        >
          <span class="lang-code">{{ lang }}</span>
          <span data-testid="lexeme-gloss">{{ gloss.value }}</span>
        </li>
      </ul>
      <StatementGroups
        :groups="sense.statementGroups"
        testid="lexeme-sense-statements"
      />
    </div>
    <p v-if="!senses.length" data-testid="lexeme-no-senses">No senses.</p>

    <h3>Forms</h3>
    <div
      v-for="form in forms"
      :key="form.id"
      class="lexeme-block"
      data-testid="lexeme-form"
    >
      <div class="field-name">{{ form.id }}</div>
      <ul class="lexeme-values" data-testid="lexeme-form-representations">
        <li
          v-for="(representation, lang) in form.representations"
          :key="lang"
          data-testid="lexeme-representation-row"
        >
          <span class="lang-code">{{ lang }}</span>
          <span data-testid="lexeme-representation">{{ representation.value }}</span>
        </li>
      </ul>
      <div v-if="form.grammaticalFeatureLabels.length" class="row">
        <span class="field-name">Grammatical features</span>
        <span data-testid="lexeme-grammatical-features">
          {{ form.grammaticalFeatureLabels.join(', ') }}
        </span>
      </div>
      <StatementGroups
        :groups="form.statementGroups"
        testid="lexeme-form-statements"
      />
    </div>
    <p v-if="!forms.length" data-testid="lexeme-no-forms">No forms.</p>

    <StatementSection
      :entity-id="entityId"
      :hashes="hashes"
      @error="$emit('error', $event)"
      @reload="$emit('reload')"
    />
  </div>
</template>

<script setup>
// A lexeme: lemmas per language plus its language and lexical category,
// then senses and forms, each of which can carry its own statements.
import { computed, ref, watch } from 'vue'
import { getLexemeForms, getLexemeSenses } from '../../api.js'
import { useEntityLabels } from '../../composables/useEntityLabels.js'
import StatementGroups from './StatementGroups.vue'
import StatementSection from './StatementSection.vue'

const props = defineProps({
  entityId: { type: String, required: true },
  // Revision data of the lexeme (carries lemmas, language, category)
  revision: { type: Object, default: () => ({}) },
  hashes: { type: Array, default: () => [] },
})

defineEmits(['error', 'reload'])

const { humanLabel } = useEntityLabels()

const senses = ref([])
const forms = ref([])

const lemmas = computed(() => props.revision?.lemmas ?? {})
const lexemeLanguage = computed(() => props.revision?.language ?? '')
const lexemeCategory = computed(
  () => props.revision?.lexical_category ?? props.revision?.lexicalCategory ?? ''
)

const lexemeLanguageLabel = ref('')
const lexemeCategoryLabel = ref('')

// Claims carried inline by a sense or a form, grouped like entity statements
async function groupClaims(claims) {
  const groups = []
  for (const [property, claimList] of Object.entries(claims ?? {})) {
    const rows = await Promise.all(
      (claimList ?? []).map(async (claim) => {
        const dv = claim?.mainsnak?.datavalue
        const valueId = dv?.type === 'wikibase-item' ? (dv.value?.id ?? '') : ''
        const value = valueId || (dv?.value != null ? String(dv.value) : '')
        const valueLabel = valueId ? await humanLabel(valueId) : ''
        return { value, valueLabel }
      })
    )
    groups.push({
      property,
      propertyLabel: await humanLabel(property),
      statements: rows,
    })
  }
  return groups
}

async function load() {
  senses.value = []
  forms.value = []
  lexemeLanguageLabel.value = lexemeLanguage.value
    ? await humanLabel(lexemeLanguage.value)
    : ''
  lexemeCategoryLabel.value = lexemeCategory.value
    ? await humanLabel(lexemeCategory.value)
    : ''
  try {
    const [senseRows, formRows] = await Promise.all([
      getLexemeSenses(props.entityId),
      getLexemeForms(props.entityId),
    ])
    senses.value = await Promise.all(
      (senseRows ?? []).map(async (sense) => ({
        id: sense.id,
        glosses: sense.glosses ?? {},
        statementGroups: await groupClaims(sense.claims),
      }))
    )
    forms.value = await Promise.all(
      (formRows ?? []).map(async (form) => ({
        id: form.id,
        representations: form.representations ?? {},
        grammaticalFeatureLabels: await Promise.all(
          // The API serialises this field under its alias
          (form.grammaticalFeatures ?? form.grammatical_features ?? []).map((feature) =>
            humanLabel(feature)
          )
        ),
        statementGroups: await groupClaims(form.claims),
      }))
    )
  } catch (e) {
    // A missing or failing senses/forms endpoint must not blank the page;
    // the lemmas above are still shown.
    console.warn('Could not load lexeme senses/forms:', e)
  }
}

watch(() => props.entityId, load, { immediate: true })
</script>

<style scoped>
.lexeme-values { list-style: none; padding: 0; margin: 0; }
.lexeme-values li { display: flex; gap: .75rem; align-items: baseline; }
.lexeme-block { margin-bottom: 1rem; }
</style>