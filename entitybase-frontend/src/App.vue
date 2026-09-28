<template>
  <main class="app">
    <h1>Entitybase</h1>

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

    <section v-if="error" class="error" data-testid="error-banner">{{ error }}</section>

    <section v-if="item" class="panel" data-testid="item-section">
      <h2>Item {{ item.id }}</h2>
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
          <span class="field-name">{{ s.property }}</span>
          <span data-testid="statement-value">{{ s.value }}</span>
        </li>
        <li v-if="!statements.length" data-testid="no-statements">No statements yet.</li>
      </ul>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getItem, getLabel, getStatement, postStatement, postItem, putLabel } from './api.js'

const userId = ref(90001)
const newLabel = ref('')
const creating = ref(false)
const adding = ref(false)
const error = ref('')
const item = ref(null)

const stmtProperty = ref('')
const stmtValue = ref('')

const label = ref('')
const statements = ref([])

const entityData = computed(
  () => item.value?.data?.revision ?? item.value?.data ?? item.value ?? {}
)

function loadFromQuery() {
  const id = new URLSearchParams(window.location.search).get('entity')
  if (id) loadItem(id)
}

async function loadItem(id) {
  error.value = ''
  label.value = ''
  statements.value = []
  try {
    item.value = await getItem(id)

    // Label values are stored hash-referenced; fetch via the labels endpoint
    label.value = (await getLabel(id, 'en')) ?? ''

    // Statement values are resolved per content hash
    const hashes = entityData.value.hashes?.statements ?? []
    const fetched = await Promise.all(hashes.map((h) => getStatement(h)))
    statements.value = fetched
      .map((res) => res.statement)
      .filter((stmt) => stmt && stmt.mainsnak)
      .map((stmt) => {
        const dv = stmt.mainsnak.datavalue
        const value =
          dv?.type === 'wikibase-item' ? (dv.value?.id ?? '?') : String(dv?.value ?? '?')
        return {
          id: stmt.id ?? stmt.mainsnak.hash ?? String(stmt.mainsnak.property),
          property: stmt.mainsnak.property,
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
    window.history.replaceState(null, '', `/?entity=${encodeURIComponent(entityId)}`)
    await loadItem(entityId)
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    creating.value = false
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
