<template>
  <section class="panel" data-testid="entity-list-section">
    <h2>Entity list</h2>

    <div class="row" data-testid="entity-list-controls">
      <label for="entity-type-select">Type</label>
      <select
        id="entity-type-select"
        data-testid="entity-type-select"
        v-model="entityType"
      >
        <option value="item">Items</option>
        <option value="property">Properties</option>
        <option value="lexeme">Lexemes</option>
      </select>
    </div>

    <section v-if="error" class="error" data-testid="entity-list-error">{{ error }}</section>

    <table class="history" data-testid="entity-list-table">
      <tbody>
        <tr v-for="entry in entities" :key="entry.entity_id" data-testid="entity-list-row">
          <td>
            <router-link
              data-testid="entity-list-link"
              :to="{ path: '/', query: { entity: entry.entity_id } }"
            >
              {{ entry.entity_id }}
            </router-link>
          </td>
          <td data-testid="entity-list-label">{{ entry.label || '—' }}</td>
          <td data-testid="entity-list-revision">rev {{ entry.head_revision_id }}</td>
        </tr>
        <tr v-if="!entities.length && !loading" data-testid="entity-list-empty">
          <td colspan="3" class="empty-row">No {{ typeLabel }} found.</td>
        </tr>
      </tbody>
    </table>

    <div class="pagination" data-testid="entity-list-pagination">
      <button
        data-testid="entity-list-prev"
        :disabled="page === 1 || loading"
        @click="goToPage(page - 1)"
      >← Prev</button>
      <span data-testid="entity-list-page">Page {{ page }}</span>
      <button
        data-testid="entity-list-next"
        :disabled="!hasMore || loading"
        @click="goToPage(page + 1)"
      >Next →</button>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getEntityList, getLabelWithFallback } from '../api.js'
import { fallbackChain, language } from '../settings.js'

const PAGE_SIZE = 10

const TYPE_LABELS = { item: 'items', property: 'properties', lexeme: 'lexemes' }

const route = useRoute()
const router = useRouter()

const entityType = ref(typeof route.query.type === 'string' ? route.query.type : 'item')
if (!TYPE_LABELS[entityType.value]) entityType.value = 'item'
const entities = ref([])
const page = ref(1)
const hasMore = ref(false)
const loading = ref(false)
const error = ref('')

const typeLabel = computed(() => TYPE_LABELS[entityType.value] ?? 'entities')

function entityQuery() {
  return (page.value - 1) * PAGE_SIZE
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const body = await getEntityList(entityType.value, PAGE_SIZE, entityQuery())
    const rows = body?.entities ?? []
    hasMore.value = rows.length === PAGE_SIZE
    const chain = [language.value, ...fallbackChain.value]
    entities.value = await Promise.all(
      rows.map(async (entry) => ({
        ...entry,
        label: (await getLabelWithFallback(entry.entity_id, chain)) ?? '',
      }))
    )
  } catch (e) {
    error.value = String(e.message || e)
    entities.value = []
    hasMore.value = false
  } finally {
    loading.value = false
  }
}

function goToPage(target) {
  if (target < 1) return
  page.value = target
}

// Keep type and page shareable in the URL
watch([entityType, page], async () => {
  await router.replace({
    query: { type: entityType.value, page: String(page.value) },
  })
  await load()
})

onMounted(() => {
  const queryPage = Number(route.query.page)
  if (Number.isFinite(queryPage) && queryPage > 0) {
    page.value = queryPage
  }
  return load()
})
</script>

<style>
.pagination { display: flex; gap: 1rem; align-items: center; }
.empty-row { color: #666; }
</style>
