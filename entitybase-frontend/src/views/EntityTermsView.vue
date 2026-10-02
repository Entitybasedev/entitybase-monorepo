<template>
  <section v-if="error" class="alert alert-danger" data-testid="error-banner">{{ error }}</section>
  <p v-if="loading" data-testid="terms-loading">Loading terms…</p>

  <section v-else class="card card-body mb-3" data-testid="terms-section">
    <h2>
      All terms {{ entityId }}
      <span class="badge text-bg-secondary" data-testid="terms-entity-id">{{ entityId }}</span>
    </h2>

    <div class="d-flex align-items-center gap-2 flex-wrap mb-2">
      <button
        class="btn btn-outline-secondary btn-sm"
        data-testid="terms-toggle-all"
        @click="toggleShowAll"
      >
        {{ showAll ? 'Show only my languages' : `Show all ${termLanguages.length} languages` }}
      </button>
      <span class="small text-muted" data-testid="terms-count">
        Showing {{ rows.length }} of {{ termLanguages.length }} languages
      </span>
      <template v-if="showAll && pageCount > 1">
        <button
          class="btn btn-outline-secondary btn-sm"
          data-testid="terms-prev-page"
          :disabled="page <= 1"
          @click="page--"
        >← Prev</button>
        <span class="small" data-testid="terms-page-info">Page {{ page }} / {{ pageCount }}</span>
        <button
          class="btn btn-outline-secondary btn-sm"
          data-testid="terms-next-page"
          :disabled="page >= pageCount"
          @click="page++"
        >Next →</button>
      </template>
    </div>

    <table class="table table-sm" data-testid="terms-table">
      <thead>
        <tr>
          <th>Language</th>
          <th>Label</th>
          <th>Description</th>
          <th>Aliases</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.lang" data-testid="terms-row">
          <td class="fw-bold" data-testid="terms-lang">{{ row.lang }}</td>
          <td data-testid="terms-label">{{ row.label || '—' }}</td>
          <td data-testid="terms-description">{{ row.description || '—' }}</td>
          <td data-testid="terms-aliases">
            <template v-if="row.aliases.length">
              <span
                v-for="alias in row.aliases"
                :key="alias"
                class="alias-chip"
                data-testid="terms-alias"
              >{{ alias }}</span>
            </template>
            <template v-else>—</template>
          </td>
        </tr>
        <tr v-if="!rows.length" data-testid="no-terms">
          <td colspan="4">No terms.</td>
        </tr>
      </tbody>
    </table>

    <p>
      <router-link :to="{ path: '/', query: { entity: entityId } }" data-testid="back-to-entity-link">
        Back to entity
      </router-link>
    </p>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getEntityTerms, getItem } from '../api.js'
import { fallbackChain, language } from '../settings.js'

// Languages per page when showing all terms
const PAGE_SIZE = 20

const route = useRoute()

const entityId = computed(() =>
  typeof route.params.entityId === 'string' ? route.params.entityId : ''
)

const error = ref('')
const loading = ref(false)
const showAll = ref(false)
const page = ref(1)

// Languages that have at least one term on the entity (from revision hashes)
const termLanguages = ref([])
// Fetched terms per language: { [lang]: { label, description, aliases } }
const termsByLang = ref({})

// Default view: interface language first, then the fallback chain
const chainLanguages = computed(() => [
  ...new Set([language.value, ...fallbackChain.value]),
])

const pageCount = computed(() =>
  Math.max(1, Math.ceil(termLanguages.value.length / PAGE_SIZE))
)

const pagedLanguages = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE
  return termLanguages.value.slice(start, start + PAGE_SIZE)
})

const visibleLanguages = computed(() =>
  showAll.value ? pagedLanguages.value : chainLanguages.value
)

const rows = computed(() =>
  visibleLanguages.value.map((lang) => ({
    lang,
    ...(termsByLang.value[lang] ?? { label: '', description: '', aliases: [] }),
  }))
)

// Fetch terms for languages not already loaded
async function loadRows(langs) {
  const missing = langs.filter((lang) => !(lang in termsByLang.value))
  await Promise.all(
    missing.map(async (lang) => {
      try {
        const terms = await getEntityTerms(entityId.value, lang)
        termsByLang.value = { ...termsByLang.value, [lang]: terms }
      } catch {
        termsByLang.value = {
          ...termsByLang.value,
          [lang]: { language: lang, label: '', description: '', aliases: [] },
        }
      }
    })
  )
}

// Available languages come from the entity's revision term hashes
async function load(id) {
  error.value = ''
  loading.value = true
  termLanguages.value = []
  termsByLang.value = {}
  page.value = 1
  try {
    const item = await getItem(id)
    const hashes = item?.data?.revision?.hashes ?? item?.data?.hashes ?? {}
    termLanguages.value = [
      ...new Set([
        ...Object.keys(hashes.labels ?? {}),
        ...Object.keys(hashes.descriptions ?? {}),
        ...Object.keys(hashes.aliases ?? {}),
      ]),
    ].sort((a, b) => a.localeCompare(b))
    await loadRows(visibleLanguages.value)
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    loading.value = false
  }
}

function toggleShowAll() {
  showAll.value = !showAll.value
  page.value = 1
}

onMounted(() => {
  if (entityId.value) load(entityId.value)
})

watch(entityId, (id) => {
  if (id) load(id)
})

watch(visibleLanguages, (langs) => {
  loadRows(langs)
})
</script>

<style scoped>
.alias-chip {
  display: inline-block;
  background: #eef6ff;
  border: 1px solid #b6d4fe;
  border-radius: 999px;
  padding: 0.1rem 0.6rem;
  margin-right: 0.35rem;
}
</style>
