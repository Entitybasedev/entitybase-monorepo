<template>
  <section class="panel" data-testid="recent-changes-section">
    <h2>Recent changes</h2>
    <button data-testid="recent-refresh" :disabled="loading" @click="refresh">
      {{ loading ? 'Loading…' : 'Refresh' }}
    </button>
    <section v-if="error" class="error" data-testid="recent-error">{{ error }}</section>

    <table class="history" data-testid="recent-table">
      <tbody>
        <tr v-for="entry in changes" :key="entry.id" data-testid="recent-row">
          <td data-testid="recent-time">{{ entry.created_at }}</td>
          <td>
            <span class="change-type" data-testid="recent-type">
              {{ changeLabel(entry) }}
            </span>
          </td>
          <td>
            <router-link
              v-if="entry.entity_id"
              data-testid="recent-entity"
              :to="{ path: '/', query: { entity: entry.entity_id } }"
            >
              {{ entry.entity_id }}
            </router-link>
          </td>
          <td data-testid="recent-user">{{ entry.user_id }}</td>
          <td data-testid="recent-summary">{{ entry.edit_summary || '—' }}</td>
        </tr>
        <tr v-if="!changes.length && !loading" data-testid="recent-empty">
          <td colspan="5" class="empty-row">No changes recorded yet.</td>
        </tr>
      </tbody>
    </table>

    <button
      v-if="changes.length >= limit"
      data-testid="recent-more"
      @click="loadMore"
    >Load more</button>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getRecentChanges } from '../api.js'

const CHANGES_PAGE = 50

const CHANGE_LABELS = {
  entity_create: 'New entity',
  label_update: 'Label edited',
  label_delete: 'Label removed',
  description_update: 'Description edited',
  description_delete: 'Description removed',
  aliases_update: 'Aliases edited',
  aliases_delete: 'Aliases removed',
  statement_add: 'New statement',
  statement_remove: 'Statement removed',
  statement_patch: 'Statement replaced',
  statements_batch: 'Statements edited',
  lexeme_update: 'Lexeme edited',
  entity_revert: 'Reverted',
  entity_lock: 'Locked',
  entity_unlock: 'Unlocked',
  thank_sent: 'Thanks',
}

const changes = ref([])
const limit = ref(CHANGES_PAGE)
const loading = ref(false)
const error = ref('')

function changeLabel(entry) {
  return (
    CHANGE_LABELS[entry.change_type]
    || CHANGE_LABELS[entry.activity_type]
    || 'Edit'
  )
}

async function load(offset = 0) {
  loading.value = true
  error.value = ''
  try {
    const entries = (await getRecentChanges(CHANGES_PAGE, offset)) ?? []
    if (offset === 0) {
      changes.value = entries
    } else {
      changes.value = [...changes.value, ...entries]
    }
    limit.value = offset + entries.length
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    loading.value = false
  }
}

function refresh() {
  return load(0)
}

function loadMore() {
  return load(changes.value.length)
}

onMounted(() => {
  return refresh()
})
</script>

<style>
.change-type { font-weight: 600; }
.empty-row { color: #666; }
</style>
