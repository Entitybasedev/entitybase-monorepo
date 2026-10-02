<template>
  <section class="card card-body mb-3" data-testid="statistics-section">
    <h2>Statistics</h2>
    <section v-if="error" class="alert alert-danger" data-testid="error-banner">{{ error }}</section>
    <p v-else-if="!loaded" data-testid="statistics-loading">Loading statistics…</p>

    <template v-if="loaded">
      <h3>Edit activity</h3>
      <table class="table table-sm" data-testid="statistics-edits">
        <tbody>
          <tr data-testid="statistics-row">
            <td class="field-name">Edits (7 days)</td>
            <td data-testid="statistics-edits-7d">{{ format(edits?.edits_7d) }}</td>
          </tr>
          <tr data-testid="statistics-row">
            <td class="field-name">Edits (30 days)</td>
            <td data-testid="statistics-edits-30d">{{ format(edits?.edits_30d) }}</td>
          </tr>
          <tr data-testid="statistics-row">
            <td class="field-name">Edits (total)</td>
            <td data-testid="statistics-edits-total">{{ format(edits?.edits_total) }}</td>
          </tr>
        </tbody>
      </table>

      <h3>General statistics</h3>
      <p class="small text-muted" data-testid="statistics-date">
        Computed: {{ stats?.date }}
      </p>
      <table class="table table-sm" data-testid="statistics-general">
        <tbody>
          <tr v-for="row in generalRows" :key="row.label" data-testid="statistics-row">
            <td class="field-name">{{ row.label }}</td>
            <td data-testid="statistics-general-value">{{ format(row.value) }}</td>
          </tr>
        </tbody>
      </table>

      <h3>Terms by type</h3>
      <table class="table table-sm" data-testid="statistics-terms-by-type">
        <tbody>
          <tr
            v-for="[type, count] in sortedPairs(stats?.terms_by_type?.counts)"
            :key="type"
            data-testid="statistics-row"
          >
            <td class="field-name">{{ type }}</td>
            <td data-testid="statistics-terms-by-type-value">{{ format(count) }}</td>
          </tr>
          <tr v-if="!sortedPairs(stats?.terms_by_type?.counts).length">
            <td colspan="2">No terms yet.</td>
          </tr>
        </tbody>
      </table>

      <h3>Terms per language</h3>
      <table class="table table-sm" data-testid="statistics-terms-per-language">
        <tbody>
          <tr
            v-for="[lang, count] in sortedPairs(stats?.terms_per_language?.terms)"
            :key="lang"
            data-testid="statistics-row"
          >
            <td class="field-name">{{ lang }}</td>
            <td data-testid="statistics-terms-per-language-value">{{ format(count) }}</td>
          </tr>
          <tr v-if="!sortedPairs(stats?.terms_per_language?.terms).length">
            <td colspan="2">No terms yet.</td>
          </tr>
        </tbody>
      </table>

      <h3>Deduplication</h3>
      <table class="table table-sm" data-testid="statistics-deduplication">
        <thead>
          <tr>
            <th>Type</th>
            <th>Unique hashes</th>
            <th>Total refs</th>
            <th>Dedup factor</th>
            <th>Duplicates saved</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="[type, d] in sortedPairs(dedup)"
            :key="type"
            data-testid="statistics-row"
          >
            <td class="field-name" data-testid="statistics-deduplication-type">{{ type }}</td>
            <td data-testid="statistics-deduplication-unique">{{ format(d.unique_hashes) }}</td>
            <td>{{ format(d.total_ref_count) }}</td>
            <td data-testid="statistics-deduplication-factor">{{ dedupFactor(d.deduplication_factor) }}</td>
            <td data-testid="statistics-deduplication-saved">{{ format(d.space_saved) }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  getDeduplicationStats,
  getEditStats,
  getGeneralStats,
} from '../api.js'

const error = ref('')
const stats = ref(null)
const edits = ref(null)
const dedup = ref(null)
const loaded = ref(false)

function format(value) {
  if (value === undefined || value === null || value === '') return '—'
  return String(value)
}

function dedupFactor(factor) {
  if (factor === undefined || factor === null) return '—'
  return `${factor}%`
}

// Key/value pairs sorted by key for stable tables
function sortedPairs(record) {
  return Object.entries(record ?? {}).sort(([a], [b]) => a.localeCompare(b))
}

const generalRows = computed(() => [
  { label: 'Items', value: stats.value?.total_items },
  { label: 'Properties', value: stats.value?.total_properties },
  { label: 'Lexemes', value: stats.value?.total_lexemes },
  { label: 'Statements', value: stats.value?.total_statements },
  { label: 'Qualifiers', value: stats.value?.total_qualifiers },
  { label: 'References', value: stats.value?.total_references },
  { label: 'Sitelinks', value: stats.value?.total_sitelinks },
  { label: 'Terms', value: stats.value?.total_terms },
])

async function load() {
  error.value = ''
  try {
    const [generalStats, editStats, dedupStats] = await Promise.all([
      getGeneralStats(),
      getEditStats(),
      getDeduplicationStats(),
    ])
    stats.value = generalStats
    edits.value = editStats
    dedup.value = dedupStats
    loaded.value = true
  } catch (e) {
    error.value = String(e.message || e)
  }
}

onMounted(load)
</script>

<style scoped>
.table td.field-name { font-weight: 600; }
</style>
