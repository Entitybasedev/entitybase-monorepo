<template>
  <section class="card card-body mb-3" data-testid="user-list-section">
    <h2>Users</h2>

    <section v-if="error" class="alert alert-danger" data-testid="user-list-error">
      {{ error }}
    </section>

    <table class="table table-striped history" data-testid="user-list-table">
      <tbody>
        <tr v-for="user in users" :key="user.user_id" data-testid="user-list-row">
          <td data-testid="user-list-id">{{ user.user_id }}</td>
          <td>
            <span
              v-if="user.user_id === 0"
              class="badge text-bg-warning"
              data-testid="user-list-import-badge"
            >Import</span>
            <span v-else data-testid="user-list-username">
              {{ user.username || '—' }}
            </span>
          </td>
          <td data-testid="user-list-created">{{ user.created_at || '—' }}</td>
          <td data-testid="user-list-activity">{{ user.last_activity || '—' }}</td>
        </tr>
        <tr v-if="!users.length && !loading" data-testid="user-list-empty">
          <td colspan="4" class="empty-row">No users found.</td>
        </tr>
      </tbody>
    </table>

    <div class="pagination d-flex gap-3 align-items-center" data-testid="user-list-pagination">
      <button
        class="btn btn-primary btn-sm"
        data-testid="user-list-prev"
        :disabled="page === 1 || loading"
        @click="goToPage(page - 1)"
      >← Prev</button>
      <span data-testid="user-list-page">Page {{ page }}</span>
      <button
        class="btn btn-primary btn-sm"
        data-testid="user-list-next"
        :disabled="!hasMore || loading"
        @click="goToPage(page + 1)"
      >Next →</button>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getUserList } from '../api.js'

const PAGE_SIZE = 10

const route = useRoute()
const router = useRouter()

const users = ref([])
const page = ref(1)
const hasMore = ref(false)
const loading = ref(false)
const error = ref('')

function goToPage(target) {
  if (target < 1) return
  page.value = target
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const body = await getUserList(PAGE_SIZE, (page.value - 1) * PAGE_SIZE)
    const rows = body?.users ?? []
    hasMore.value = rows.length === PAGE_SIZE
    users.value = rows
  } catch (e) {
    error.value = String(e.message || e)
    users.value = []
    hasMore.value = false
  } finally {
    loading.value = false
  }
}

watch(page, async () => {
  await router.replace({ query: { page: String(page.value) } })
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
.empty-row { color: #666; }
</style>
