<template>
  <section class="panel" data-testid="create-property-section">
    <h2>Create property</h2>
    <div class="row">
      <label for="property-label-input">Label (en)</label>
      <input
        id="property-label-input"
        v-model="propertyLabel"
        data-testid="property-label-input"
        placeholder="instance of"
      />
    </div>
    <div v-if="!isLoggedIn" class="row">
      <label for="user-id-input">User ID</label>
      <input id="user-id-input" v-model.number="userId" data-testid="user-id-input" type="number" />
    </div>
    <button
      :disabled="!propertyLabel || creatingProperty"
      data-testid="create-property-button"
      @click="createProperty"
    >
      {{ creatingProperty ? 'Creating…' : 'Create property' }}
    </button>
    <section v-if="error" class="error" data-testid="error-banner">{{ error }}</section>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { postProperty, putLabel } from '../api.js'
import { language } from '../settings.js'
import { isLoggedIn, userId as authUserId } from '../auth.js'

const router = useRouter()
const userId = ref(authUserId.value || 90001)
const propertyLabel = ref('')
const creatingProperty = ref(false)
const error = ref('')

async function createProperty() {
  creatingProperty.value = true
  error.value = ''
  try {
    const entityId = await postProperty({}, userId.value)
    await putLabel(entityId, language.value, propertyLabel.value, userId.value)
    await router.push({ path: '/', query: { entity: entityId } })
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    creatingProperty.value = false
  }
}
</script>
