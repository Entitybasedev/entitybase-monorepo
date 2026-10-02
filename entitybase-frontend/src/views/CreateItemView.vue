<template>
  <section class="card card-body mb-3" data-testid="create-item-section">
    <h2>Create item</h2>
    <section v-if="!isLoggedIn" class="login-required" data-testid="login-required">
      <p>You need to log in to create entities.</p>
      <router-link to="/login" data-testid="login-required-link">Log in</router-link>
    </section>
    <template v-else>
      <form class="row" @submit.prevent="createItem">
        <label for="label-input">Label</label>
        <select
          class="form-select form-select-sm"
          style="width: auto"
          data-testid="item-lang-select"
          v-model="labelLanguage"
        >
          <option v-for="l in SUPPORTED_LANGUAGES" :key="l.code" :value="l.code">
            {{ l.code }}
          </option>
        </select>
        <input
          id="label-input"
          v-model="newLabel"
          data-testid="item-label-input"
          placeholder="Universe"
          @keyup.enter="createItem"
        />
        <button type="submit" class="btn btn-primary btn-sm" :disabled="!newLabel || creating" data-testid="create-item-button" @click="createItem">
          {{ creating ? 'Creating…' : 'Create item' }}
        </button>
      </form>
    </template>
    <section v-if="error" class="alert alert-danger" data-testid="error-banner">{{ error }}</section>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { postItem, putLabel } from '../api.js'
import { SUPPORTED_LANGUAGES, language } from '../settings.js'
import { isLoggedIn } from '../auth.js'

const router = useRouter()
const newLabel = ref('')
const labelLanguage = ref(language.value)
const creating = ref(false)
const error = ref('')

async function createItem() {
  if (creating.value) return
  creating.value = true
  error.value = ''
  try {
    const entityId = await postItem({})
    await putLabel(entityId, labelLanguage.value, newLabel.value)
    await router.push({ path: '/', query: { entity: entityId } })
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    creating.value = false
  }
}
</script>
