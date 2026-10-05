<template>
  <section class="card card-body mb-3" data-testid="dashboard-section">
    <h2>Dashboard</h2>
    <section v-if="error" class="alert alert-danger" data-testid="error-banner">{{ error }}</section>

    <div v-if="loaded" class="row row-cols-2 row-cols-md-4 row-cols-lg-7 g-3">
      <div class="col">
        <div class="stat-card">
          <div class="stat-value" data-testid="dashboard-edits-7d">{{ edits?.edits_7d ?? '—' }}</div>
          <div class="stat-label">Edits (7 days)</div>
        </div>
      </div>
      <div class="col">
        <div class="stat-card">
          <div class="stat-value" data-testid="dashboard-edits-30d">{{ edits?.edits_30d ?? '—' }}</div>
          <div class="stat-label">Edits (30 days)</div>
        </div>
      </div>
      <div class="col">
        <div class="stat-card">
          <div class="stat-value" data-testid="dashboard-items">{{ stats?.total_items ?? '—' }}</div>
          <div class="stat-label">Items</div>
        </div>
      </div>
      <div class="col">
        <div class="stat-card">
          <div class="stat-value" data-testid="dashboard-properties">{{ stats?.total_properties ?? '—' }}</div>
          <div class="stat-label">Properties</div>
        </div>
      </div>
      <div class="col">
        <div class="stat-card">
          <div class="stat-value" data-testid="dashboard-lexemes">{{ stats?.total_lexemes ?? '—' }}</div>
          <div class="stat-label">Lexemes</div>
        </div>
      </div>
      <div class="col">
        <div class="stat-card">
          <div class="stat-value" data-testid="dashboard-statements">{{ stats?.total_statements ?? '—' }}</div>
          <div class="stat-label">Statements</div>
        </div>
      </div>
      <div class="col">
        <div class="stat-card">
          <div class="stat-value" data-testid="dashboard-terms">{{ stats?.total_terms ?? '—' }}</div>
          <div class="stat-label">Terms</div>
        </div>
      </div>
    </div>
    <p v-else data-testid="dashboard-loading">Loading statistics…</p>

    <p>
      <router-link to="/statistics" data-testid="dashboard-statistics-link">
        Detailed statistics →
      </router-link>
      ·
      <!-- DokuWiki is a separate service on its own origin, so a plain link -->
      <a
        :href="dokuwikiUrl"
        target="_blank"
        rel="noopener"
        data-testid="dashboard-dokuwiki-link"
      >Write it up in the wiki →</a>
    </p>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getEditStats, getGeneralStats } from '../api.js'

const error = ref('')
const stats = ref(null)
const edits = ref(null)
const loaded = ref(false)

// Where the DokuWiki with the Entitybase plugin is served; the wiki is a
// separate service, so this is an absolute URL rather than a route.
const dokuwikiUrl = import.meta.env.VITE_DOKUWIKI_URL || 'http://localhost:8082'

async function load() {
  error.value = ''
  try {
    const [generalStats, editStats] = await Promise.all([
      getGeneralStats(),
      getEditStats(),
    ])
    stats.value = generalStats
    edits.value = editStats
    loaded.value = true
  } catch (e) {
    error.value = String(e.message || e)
  }
}

onMounted(load)
</script>

<style scoped>
.stat-card {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: .5rem;
  padding: .75rem 1rem;
  text-align: center;
}
.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.2;
}
.stat-label {
  color: #555;
  font-size: .85rem;
}
</style>
