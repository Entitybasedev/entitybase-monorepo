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
      <button class="btn btn-primary btn-sm" data-testid="diff-close" @click="closeDiff">Close diff</button>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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
const router = useRouter()

const entityId = computed(() => String(route.params.entityId ?? ''))

// Diff revisions come from the URL when present (/history/<new>/<old>)
const urlNewRev = computed(() => Number(route.params.newRev) || 0)
const urlOldRev = computed(() => Number(route.params.oldRev) || 0)
const hasUrlDiff = computed(() => urlNewRev.value > 0 && urlOldRev.value > 0)

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

// Diff buttons navigate to the shareable diff URL; the watcher computes
function diffWithPrevious(revisionId) {
  const idx = history.value.findIndex((e) => e.revision_id === revisionId)
  const older = history.value[idx + 1]
  if (!older) return
  return router.push(
    `/${entityId.value}/history/${revisionId}/${older.revision_id}`
  )
}

async function computeDiff(newRev, oldRev) {
  error.value = ''
  try {
    const [newRevData, oldRevData] = await Promise.all([
      getEntityRevision(entityId.value, newRev),
      getEntityRevision(entityId.value, oldRev),
    ])
    const result = await computeEntityDiff(oldRevData, newRevData, {
      resolveLabels: resolveLabelHashes,
      resolveDescriptions: resolveDescriptionHashes,
      resolveAliases: resolveAliasHashes,
      getStatement,
      getSnak,
    })
    diff.value = { ...result, oldRev, newRev }
  } catch (e) {
    error.value = String(e.message || e)
  }
}

function closeDiff() {
  diff.value = null
  if (hasUrlDiff.value) {
    return router.push(`/${entityId.value}/history`)
  }
}

// Compute (or clear) the diff when the diff URL changes
watch(hasUrlDiff, async () => {
  if (hasUrlDiff.value) {
    await computeDiff(urlNewRev.value, urlOldRev.value)
  } else {
    diff.value = null
  }
})

onMounted(async () => {
  await loadHistory(0)
  if (hasUrlDiff.value) {
    await computeDiff(urlNewRev.value, urlOldRev.value)
  }
})
</script>

<style>
.empty-row { color: #666; }
</style>
