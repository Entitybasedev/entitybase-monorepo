<template>
  <section class="card card-body mb-3" data-testid="search-section">
    <h2>Search</h2>

    <form class="search-form" data-testid="search-form" @submit.prevent="runSearch">
      <input
        v-model="query"
        class="form-control"
        type="search"
        name="q"
        autocomplete="off"
        placeholder="Search labels, descriptions and aliases"
        aria-label="Search query"
        data-testid="search-input"
      />
      <button
        class="btn btn-primary"
        type="submit"
        :disabled="!query.trim() || loading"
        data-testid="search-submit"
      >
        {{ loading ? 'Searching…' : 'Search' }}
      </button>
    </form>

    <nav class="search-types" data-testid="search-types">
      <button
        v-for="option in TYPE_OPTIONS"
        :key="option.value"
        type="button"
        class="btn btn-sm"
        :class="entityType === option.value ? 'btn-secondary' : 'btn-outline-secondary'"
        :data-testid="`search-type-${option.value || 'all'}`"
        @click="selectType(option.value)"
      >
        {{ option.label }}
      </button>
    </nav>

    <section
      v-if="error"
      class="alert alert-danger"
      data-testid="search-error"
    >
      {{ error }}
    </section>

    <p v-else-if="searched && !loading && !hits.length" class="empty-row" data-testid="search-no-results">
      Nothing found for “{{ submittedQuery }}”.
    </p>

    <p v-else-if="!searched" class="empty-row" data-testid="search-hint">
      Search for an entity by label, description or alias.
    </p>

    <ul v-if="hits.length" class="search-results" data-testid="search-results">
      <li
        v-for="hit in hits"
        :key="hit.entity_id"
        class="search-result"
        data-testid="search-result"
      >
        <router-link
          class="search-result-label"
          :to="`/entity/${hit.entity_id}`"
          data-testid="search-result-link"
        >
          {{ hit.label || hit.entity_id }}
        </router-link>
        <span class="badge text-bg-secondary" data-testid="search-result-type">
          {{ typeLabel(hit.type) }}
        </span>
        <span class="search-result-id" data-testid="search-result-id">{{ hit.entity_id }}</span>
        <p v-if="hit.description" class="search-result-description" data-testid="search-result-description">
          {{ hit.description }}
        </p>
      </li>
    </ul>

    <footer v-if="searched" class="search-summary" data-testid="search-summary">
      <span data-testid="search-summary-text">
        {{ hits.length }} of {{ total }} {{ total === 1 ? 'result' : 'results' }}
        <template v-if="took"> in {{ took }} ms</template>
      </span>
      <div class="pagination">
        <button
          class="btn btn-outline-secondary btn-sm"
          :disabled="!canPageBack || loading"
          data-testid="search-prev"
          @click="goToOffset(offset - LIMIT)"
        >← Prev</button>
        <button
          class="btn btn-outline-secondary btn-sm"
          :disabled="!canPageForward || loading"
          data-testid="search-next"
          @click="goToOffset(offset + LIMIT)"
        >Next →</button>
      </div>
    </footer>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { searchEntities } from '../api.js'

const LIMIT = 20

const TYPE_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'item', label: 'Items' },
  { value: 'property', label: 'Properties' },
  { value: 'lexeme', label: 'Lexemes' },
]

const TYPE_LABELS = { item: 'item', property: 'property', lexeme: 'lexeme' }

const route = useRoute()
const router = useRouter()

const query = ref(typeof route.query.q === 'string' ? route.query.q : '')
const submittedQuery = ref('')
const entityType = ref(typeof route.query.type === 'string' ? route.query.type : '')
if (entityType.value && !TYPE_LABELS[entityType.value]) entityType.value = ''

const hits = ref([])
const total = ref(0)
const took = ref(0)
const offset = ref(0)
const loading = ref(false)
const error = ref('')
const searched = ref(false)

const canPageBack = computed(() => offset.value > 0)
const canPageForward = computed(() => offset.value + LIMIT < total.value)

function typeLabel(type) {
  return TYPE_LABELS[type] ?? 'entity'
}

async function load(searchTerm) {
  if (!searchTerm.trim()) {
    hits.value = []
    total.value = 0
    took.value = 0
    searched.value = false
    error.value = ''
    return
  }

  loading.value = true
  error.value = ''
  try {
    const body = await searchEntities(searchTerm, {
      type: entityType.value,
      limit: LIMIT,
      offset: offset.value,
    })
    hits.value = body?.hits ?? []
    total.value = body?.estimated_total_hits ?? hits.value.length
    took.value = body?.processing_time_ms ?? 0
    searched.value = true
  } catch (e) {
    error.value = String(e.message || e)
    hits.value = []
    total.value = 0
    searched.value = true
  } finally {
    loading.value = false
  }
}

async function runSearch() {
  const term = query.value.trim()
  if (!term) return
  submittedQuery.value = term
  offset.value = 0
  await pushUrl(term)
  await load(term)
}

async function selectType(type) {
  if (type === entityType.value) return
  entityType.value = type
  offset.value = 0
  await pushUrl(submittedQuery.value)
  await load(submittedQuery.value)
}

async function goToOffset(target) {
  if (target < 0) return
  offset.value = target
  await pushUrl(submittedQuery.value)
  await load(submittedQuery.value)
}

// Keep the search shareable: the query and the active type live in the URL
async function pushUrl(term) {
  const nextQuery = {}
  if (term) nextQuery.q = term
  if (entityType.value) nextQuery.type = entityType.value
  await router.replace({ query: nextQuery })
}

watch(
  () => route.query.q,
  async (term) => {
    const value = typeof term === 'string' ? term : ''
    if (value === submittedQuery.value) return
    query.value = value
    submittedQuery.value = value
    offset.value = 0
    await load(value)
  }
)

if (query.value.trim()) {
  submittedQuery.value = query.value.trim()
  load(submittedQuery.value)
}
</script>

<style>
.search-form { display: flex; gap: 0.5rem; }
.search-types { display: flex; gap: 0.5rem; margin: 0.75rem 0; flex-wrap: wrap; }
.search-results { list-style: none; padding: 0; margin: 0; }
.search-result { padding: 0.6rem 0; border-bottom: 1px solid #eee; }
.search-result-label { font-weight: 600; margin-right: 0.5rem; }
.search-result-id { color: #666; font-size: 0.9rem; }
.search-result-description { margin: 0.2rem 0 0; color: #444; }
.search-summary { display: flex; justify-content: space-between; align-items: center; margin-top: 1rem; }
.empty-row { color: #666; }
</style>