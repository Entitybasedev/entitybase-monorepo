<template>
  <section class="card card-body mb-3" data-testid="create-property-section">
    <h2>Create property</h2>
    <section v-if="!isLoggedIn" class="login-required" data-testid="login-required">
      <p>You need to log in to create entities.</p>
      <router-link to="/login" data-testid="login-required-link">Log in</router-link>
    </section>
    <template v-else>
      <form class="row" @submit.prevent="createProperty">
        <label for="property-label-input">Label (en)</label>
        <input
          id="property-label-input"
          v-model="propertyLabel"
          data-testid="property-label-input"
          placeholder="instance of"
          @keyup.enter="createProperty"
        />
        <button type="submit" class="btn btn-primary btn-sm"
          :disabled="!propertyLabel || creatingProperty"
          data-testid="create-property-button"
          @click="createProperty"
        >
          {{ creatingProperty ? 'Creating…' : 'Create property' }}
        </button>
      </form>
    </template>
    <section v-if="error" class="alert alert-danger" data-testid="error-banner">{{ error }}</section>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { postProperty, putLabel } from '../api.js'
import { language } from '../settings.js'
import { isLoggedIn } from '../auth.js'

const router = useRouter()
const propertyLabel = ref('')
const creatingProperty = ref(false)
const error = ref('')

async function createProperty() {
  if (creatingProperty.value) return
  creatingProperty.value = true
  error.value = ''
  try {
    const entityId = await postProperty({})
    await putLabel(entityId, language.value, propertyLabel.value)
    await router.push({ path: '/', query: { entity: entityId } })
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    creatingProperty.value = false
  }
}
</script>
