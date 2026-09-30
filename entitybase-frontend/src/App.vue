<template>
  <main class="app">
    <h1>Entitybase</h1>
    <nav class="tabs" data-testid="nav">
      <button
        data-testid="nav-entities"
        :class="{ active: activeTab === 'entities' }"
        @click="showTab('entities')"
      >
        Entities
      </button>
      <button
        data-testid="nav-stream"
        :class="{ active: activeTab === 'stream' }"
        @click="showTab('stream')"
      >
        Change stream
      </button>
      <a
        data-testid="nav-docs"
        class="docs-link"
        href="https://entitybasedev.github.io/entitybase-monorepo/"
        target="_blank"
        rel="noopener noreferrer"
      >
        Docs ↗
      </a>
    </nav>

    <template v-if="activeTab === 'entities'">
    <section class="panel" data-testid="create-item-section">
      <h2>Create item</h2>
      <div class="row">
        <label for="label-input">Label (en)</label>
        <input
          id="label-input"
          v-model="newLabel"
          data-testid="item-label-input"
          placeholder="Universe"
        />
      </div>
      <div class="row">
        <label for="user-id-input">User ID</label>
        <input id="user-id-input" v-model.number="userId" data-testid="user-id-input" type="number" />
      </div>
      <button :disabled="!newLabel || creating" data-testid="create-item-button" @click="createItem">
        {{ creating ? 'Creating…' : 'Create item' }}
      </button>
    </section>

    <section class="panel" data-testid="create-property-section">
      <h2>Create property</h2>
      <div class="row">
        <label for="property-label-input">Label (en)</label>
        <input
          id="property-label-input"
          v-model="propertyLabel"
          data-testid="property-label-input"
          placeholder="instance of"
        />
      </div>
      <button
        :disabled="!propertyLabel || creatingProperty"
        data-testid="create-property-button"
        @click="createProperty"
      >
        {{ creatingProperty ? 'Creating…' : 'Create property' }}
      </button>
    </section>

    <section class="panel" data-testid="create-lexeme-section">
      <h2>Create lexeme</h2>
      <div class="row">
        <label for="lemma-input">Lemma (en)</label>
        <input id="lemma-input" v-model="lemma" data-testid="lemma-input" placeholder="answer" />
      </div>
      <div class="row">
        <label for="lexeme-language-input">Language QID</label>
        <input
          id="lexeme-language-input"
          v-model="lexemeLanguage"
          data-testid="lexeme-language-input"
          placeholder="Q1860"
        />
      </div>
      <div class="row">
        <label for="lexeme-category-input">Lexical category QID</label>
        <input
          id="lexeme-category-input"
          v-model="lexemeCategory"
          data-testid="lexeme-category-input"
          placeholder="Q1084"
        />
      </div>
      <button
        :disabled="!lemma || creatingLexeme"
        data-testid="create-lexeme-button"
        @click="createLexeme"
      >
        {{ creatingLexeme ? 'Creating…' : 'Create lexeme' }}
      </button>
    </section>

    <section v-if="error" class="error" data-testid="error-banner">{{ error }}</section>

    <section v-if="item" class="panel" data-testid="item-section">
      <h2>Entity {{ item.id }}</h2>
      <div class="row">
        <span class="field-name">Label</span>
        <span data-testid="item-label">{{ label }}</span>
      </div>
      <p>
        <a :href="`/?entity=${item.id}`" data-testid="item-permalink">Permalink</a>
      </p>

      <h3>Statements</h3>
      <form class="statement-form" data-testid="statement-form" @submit.prevent="addStatement">
        <div class="row">
          <label for="property-input">Property</label>
          <input id="property-input" v-model="stmtProperty" data-testid="statement-property-input" placeholder="P31" />
        </div>
        <div class="row">
          <label for="value-input">Value entity</label>
          <input id="value-input" v-model="stmtValue" data-testid="statement-value-input" placeholder="Q5" />
        </div>
        <button type="submit" :disabled="adding || !stmtProperty || !stmtValue" data-testid="add-statement-button">
          {{ adding ? 'Adding…' : 'Add statement' }}
        </button>
      </form>

      <ul data-testid="statement-list">
        <li v-for="s in statements" :key="s.id" data-testid="statement">
          <span class="field-name" data-testid="statement-property">{{ s.property }}</span>
          <span data-testid="statement-value">{{ s.value }}</span>
        </li>
        <li v-if="!statements.length" data-testid="no-statements">No statements yet.</li>
      </ul>
    </section>
    </template>
    <StreamView v-if="activeTab === 'stream'" />
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import StreamView from './components/stream/StreamView.vue'
import {
  getItem,
  getLabel,
  getSnak,
  getStatement,
  postStatement,
  postItem,
  postProperty,
  postLexeme,
  putLabel,
} from './api.js'

const activeTab = ref('entities')

function showTab(tab) {
  activeTab.value = tab
  window.history.replaceState(null, '', `/?tab=${tab}`)
}

const userId = ref(90001)
const newLabel = ref('')
const creating = ref(false)
const adding = ref(false)
const error = ref('')
const item = ref(null)

const stmtProperty = ref('')
const stmtValue = ref('')

const propertyLabel = ref('')
const creatingProperty = ref(false)

const lemma = ref('')
const lexemeLanguage = ref('Q1860')
const lexemeCategory = ref('Q1084')
const creatingLexeme = ref(false)

const label = ref('')
const statements = ref([])

const entityData = computed(
  () => item.value?.data?.revision ?? item.value?.data ?? item.value ?? {}
)

function loadFromQuery() {
  const params = new URLSearchParams(window.location.search)
  const tab = params.get('tab')
  if (tab === 'stream') {
    activeTab.value = 'stream'
  } else if (tab === 'entities') {
    activeTab.value = 'entities'
  }
  const id = params.get('entity')
  if (id) {
    activeTab.value = 'entities'
    loadItem(id)
  }
}

async function loadItem(id) {
  error.value = ''
  label.value = ''
  statements.value = []
  try {
    item.value = await getItem(id)

    // Label values are stored hash-referenced; fetch via the labels endpoint
    label.value = (await getLabel(id, 'en')) ?? ''

    // Statement values are resolved per content hash; mainsnak is stored
    // as a snak hash and resolved via the snaks endpoint
    const hashes = entityData.value.hashes?.statements ?? []
    const fetched = await Promise.all(hashes.map((h) => getStatement(h)))
    const withSnaks = await Promise.all(
      fetched
        .map((res) => res.statement)
        .filter((stmt) => stmt && stmt.mainsnak)
        .map(async (stmt) => {
          const mainsnak =
            typeof stmt.mainsnak === 'object'
              ? stmt.mainsnak
              : await getSnak(stmt.mainsnak)
          if (!mainsnak) return null
          return { stmt, mainsnak }
        })
    )
    statements.value = withSnaks
      .filter(Boolean)
      .map(({ stmt, mainsnak }) => {
        const dv = mainsnak.datavalue
        const value =
          dv?.type === 'wikibase-item' ? (dv.value?.id ?? '?') : String(dv?.value ?? '?')
        return {
          id: stmt.id ?? mainsnak.hash ?? String(mainsnak.property),
          property: mainsnak.property,
          value,
        }
      })
  } catch (e) {
    error.value = String(e.message || e)
  }
}

async function createItem() {
  creating.value = true
  error.value = ''
  try {
    const entityId = await postItem({}, userId.value)
    await putLabel(entityId, 'en', newLabel.value, userId.value)
    window.history.replaceState(null, '', `/?tab=entities&entity=${encodeURIComponent(entityId)}`)
    await loadItem(entityId)
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    creating.value = false
  }
}

async function createProperty() {
  creatingProperty.value = true
  error.value = ''
  try {
    const entityId = await postProperty({}, userId.value)
    await putLabel(entityId, 'en', propertyLabel.value, userId.value)
    window.history.replaceState(null, '', `/?tab=entities&entity=${encodeURIComponent(entityId)}`)
    await loadItem(entityId)
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    creatingProperty.value = false
  }
}

async function createLexeme() {
  creatingLexeme.value = true
  error.value = ''
  try {
    const entityId = await postLexeme(
      {
        type: 'lexeme',
        lemmas: { en: { language: 'en', value: lemma.value } },
        language: lexemeLanguage.value,
        lexical_category: lexemeCategory.value,
      },
      userId.value
    )
    window.history.replaceState(null, '', `/?tab=entities&entity=${encodeURIComponent(entityId)}`)
    await loadItem(entityId)
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    creatingLexeme.value = false
  }
}

async function addStatement() {
  adding.value = true
  error.value = ''
  try {
    await postStatement(
      item.value.id,
      {
        claim: {
          id: crypto.randomUUID(),
          mainsnak: {
            snaktype: 'value',
            property: stmtProperty.value,
            datavalue: {
              value: { id: stmtValue.value },
              type: 'wikibase-item',
            },
          },
          type: 'statement',
          rank: 'normal',
        },
      },
      userId.value
    )
    stmtProperty.value = ''
    stmtValue.value = ''
    await loadItem(item.value.id)
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    adding.value = false
  }
}

onMounted(loadFromQuery)
</script>

<style>
.tabs { display: flex; gap: .5rem; margin-bottom: 1rem; }
.tabs button { padding: .4rem 1rem; border: 1px solid #ddd; background: #f5f5f5; border-radius: 6px; cursor: pointer; }
.tabs button.active { background: #007bff; color: white; border-color: #007bff; }
.tabs .docs-link { padding: .4rem 1rem; border: 1px solid #ddd; background: #f5f5f5; border-radius: 6px; text-decoration: none; color: #333; font-size: inherit; }
body { font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 40rem; }
.panel { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin: 1rem 0; }
.row { display: flex; gap: .5rem; margin: .5rem 0; align-items: center; }
.field-name { font-weight: 600; display: inline-block; min-width: 6rem; }
label { min-width: 8rem; }
input { padding: .25rem .5rem; }
button { padding: .35rem .8rem; cursor: pointer; }
.error { color: #b00020; padding: .5rem 1rem; border: 1px solid #b00020; border-radius: 8px; }
ul { list-style: none; padding-left: 0; }
li { padding: .25rem 0; }
</style>
