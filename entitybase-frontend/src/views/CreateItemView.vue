<template>
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
    <div v-if="!isLoggedIn" class="row">
      <label for="user-id-input">User ID</label>
      <input id="user-id-input" v-model.number="userId" data-testid="user-id-input" type="number" />
    </div>
    <button :disabled="!newLabel || creating" data-testid="create-item-button" @click="createItem">
      {{ creating ? 'Creating…' : 'Create item' }}
    </button>
    <section v-if="error" class="error" data-testid="error-banner">{{ error }}</section>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { postItem, putLabel } from '../api.js'
import { language } from '../settings.js'
import { isLoggedIn, userId as authUserId } from '../auth.js'

const router = useRouter()
const userId = ref(authUserId.value || 90001)
const newLabel = ref('')
const creating = ref(false)
const error = ref('')

async function createItem() {
  creating.value = true
  error.value = ''
  try {
    const entityId = await postItem({}, userId.value)
    await putLabel(entityId, language.value, newLabel.value, userId.value)
    await router.push({ path: '/', query: { entity: entityId } })
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    creating.value = false
  }
}
</script>
