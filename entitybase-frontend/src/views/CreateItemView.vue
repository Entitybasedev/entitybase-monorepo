<template>
  <section class="card card-body mb-3" data-testid="create-item-section">
    <h2>Create item</h2>
    <section v-if="!isLoggedIn" class="login-required" data-testid="login-required">
      <p>You need to log in to create entities.</p>
      <router-link to="/login" data-testid="login-required-link">Log in</router-link>
    </section>
    <template v-else>
      <div class="row">
        <label for="label-input">Label (en)</label>
        <input
          id="label-input"
          v-model="newLabel"
          data-testid="item-label-input"
          placeholder="Universe"
        />
      </div>
      <button class="btn btn-primary btn-sm" :disabled="!newLabel || creating" data-testid="create-item-button" @click="createItem">
        {{ creating ? 'Creating…' : 'Create item' }}
      </button>
    </template>
    <section v-if="error" class="alert alert-danger" data-testid="error-banner">{{ error }}</section>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { postItem, putLabel } from '../api.js'
import { language } from '../settings.js'
import { isLoggedIn } from '../auth.js'

const router = useRouter()
const newLabel = ref('')
const creating = ref(false)
const error = ref('')

async function createItem() {
  creating.value = true
  error.value = ''
  try {
    const entityId = await postItem({})
    await putLabel(entityId, language.value, newLabel.value)
    await router.push({ path: '/', query: { entity: entityId } })
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    creating.value = false
  }
}
</script>
