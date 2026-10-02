<template>
  <section class="card card-body mb-3" data-testid="history-section">
    <h2>History: {{ entityId }}</h2>

    <div v-if="viewingRevision" class="alert alert-warning" data-testid="revision-banner">
      Viewing revision {{ viewingRevision }} —
      <a href="#" data-testid="back-to-current" @click.prevent="backToCurrent">back to current</a>
    </div>

    <table class="table table-striped history" data-testid="history-list">
      <tbody>
        <tr v-for="entry in history" :key="entry.revision_id" data-testid="history-row">
          <td data-testid="history-revision">{{ entry.revision_id }}</td>
          <td data-testid="history-timestamp">{{ entry.created_at }}</td>
          <td data-testid="history-user">{{ entry.user_id }}</td>
          <td data-testid="history-summary">{{ entry.edit_summary || '—' }}</td>
          <td>
            <button class="btn btn-primary btn-sm" data-testid="history-view" @click="viewRevision(entry.revision_id)">View</button>
            <button class="btn btn-primary btn-sm"
              v-if="canDiff(entry.revision_id)"
              data-testid="history-diff"
              @click="diffWithPrevious(entry.revision_id)"
            >Diff vs previous</button>
          </td>
        </tr>
        <tr v-if="!history.length && !loading" data-testid="history-empty">
          <td colspan="5" class="empty-row">No revisions recorded yet.</td>
        </tr>
      </tbody>
    </table>
    <button
      v-if="history.length >= historyOffset"
      data-testid="history-more"
      @click="loadMoreHistory"
    >Load more</button>

    <div v-if="diff" class="card card-body mb-3" data-testid="diff-view">
      <h3>Diff: revision {{ diff.newRev }} vs {{ diff.oldRev }}</h3>
      <p v-if="!diff.hasChanges" data-testid="diff-no-changes">No changes between these revisions.</p>
      <template v-else>
        <h4>Labels</h4>
        <ul>
          <li v-for="d in diff.labels" :key="'l' + d.lang" :data-testid="'diff-' + d.status">
            {{ d.lang }}: <span class="diff-old">{{ d.old ?? '—' }}</span> →
            <span class="diff-new">{{ d.new ?? '—' }}</span>
          </li>
        </ul>
        <h4>Descriptions</h4>
        <ul>
          <li v-for="d in diff.descriptions" :key="'d' + d.lang">
            {{ d.lang }}: <span class="diff-old">{{ d.old ?? '—' }}</span> →
            <span class="diff-new">{{ d.new ?? '—' }}</span>
          </li>
        </ul>
        <h4>Aliases</h4>
        <ul>
          <li v-for="a in diff.aliases" :key="'a' + a.lang">
            {{ a.lang }}:
            <span v-for="added in a.added" :key="added" class="diff-new" data-testid="diff-added">
              +{{ added }}
            </span>
            <span v-for="removed in a.removed" :key="removed" class="diff-old" data-testid="diff-removed">
              −{{ removed }}
            </span>
          </li>
        </ul>
        <h4>Statements</h4>
        <ul>
          <li v-for="st in diff.statements.added" :key="'sa' + st.property + st.value">
            <span class="diff-new" data-testid="diff-added">+ {{ st.property }}: {{ st.value }}</span>
          </li>
          <li v-for="st in diff.statements.removed" :key="'sr' + st.property + st.value">
            <span class="diff-old" data-testid="diff-removed">− {{ st.property }}: {{ st.value }}</span>
          </li>
        </ul>
      </template>
      <button class="btn btn-primary btn-sm" data-testid="diff-close" @click="diff = null">Close diff</button>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  getEntityHistory,
  getEntityRevision,
  getStatement,
  getSnak,
  resolveAliases as resolveAliasHashes,
  resolveDescriptions as resolveDescriptionHashes,
  resolveLabels as resolveLabelHashes,
} from '../api.js'
import { computeEntityDiff } from '../entityDiff.js'

const route = useRoute()

const entityId = computed(() => String(route.params.entityId ?? ''))

const history = ref([])
const historyOffset = ref(0)
const loading = ref(false)
const error = ref('')
const viewingRevision = ref(null)
const diff = ref(null)
const HISTORY_PAGE = 20

function canDiff(revisionId) {
  const idx = history.value.findIndex((e) => e.revision_id === revisionId)
  return idx >= 0 && idx + 1 < history.value.length
}

async function loadHistory(offset = 0) {
  loading.value = true
  error.value = ''
  try {
    const entries = (await getEntityHistory(entityId.value, HISTORY_PAGE, offset)) ?? []
    if (offset === 0) {
      history.value = entries
    } else {
      history.value = [...history.value, ...entries]
    }
    historyOffset.value = offset + entries.length
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    loading.value = false
  }
}

function loadMoreHistory() {
  return loadHistory(historyOffset.value)
}

async function viewRevision(revisionId) {
  error.value = ''
  try {
    await getEntityRevision(entityId.value, revisionId)
    viewingRevision.value = revisionId
  } catch (e) {
    error.value = String(e.message || e)
  }
}

function backToCurrent() {
  viewingRevision.value = null
}

async function diffWithPrevious(revisionId) {
  error.value = ''
  diff.value = null
  try {
    const idx = history.value.findIndex((e) => e.revision_id === revisionId)
    const older = history.value[idx + 1]
    const [newRev, oldRev] = await Promise.all([
      getEntityRevision(entityId.value, revisionId),
      getEntityRevision(entityId.value, older.revision_id),
    ])
    const result = await computeEntityDiff(oldRev, newRev, {
      resolveLabels: resolveLabelHashes,
      resolveDescriptions: resolveDescriptionHashes,
      resolveAliases: resolveAliasHashes,
      getStatement,
      getSnak,
    })
    diff.value = { ...result, oldRev: older.revision_id, newRev: revisionId }
  } catch (e) {
    error.value = String(e.message || e)
  }
}

onMounted(() => {
  return loadHistory(0)
})
</script>

<style>
.empty-row { color: #666; }
</style>
