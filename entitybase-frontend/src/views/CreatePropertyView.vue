<template>
  <section class="card card-body mb-3" data-testid="create-property-section">
    <h2>Create property</h2>
    <section v-if="!isLoggedIn" class="login-required" data-testid="login-required">
      <p>You need to log in to create entities.</p>
      <router-link to="/login" data-testid="login-required-link">Log in</router-link>
    </section>
    <template v-else>
      <form class="row" @submit.prevent="createProperty">
        <PropertyTypeSelect v-model="datatype" @error="error = $event" />
        <label for="property-label-input">Label</label>
        <select
          class="form-select form-select-sm"
          style="width: auto"
          data-testid="property-lang-select"
          v-model="labelLanguage"
        >
          <option v-for="l in SUPPORTED_LANGUAGES" :key="l.code" :value="l.code">
            {{ l.code }}
          </option>
        </select>
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
import PropertyTypeSelect from '../components/property_types/PropertyTypeSelect.vue'
import { SUPPORTED_LANGUAGES, language } from '../settings.js'
import { isLoggedIn } from '../auth.js'

const router = useRouter()
const propertyLabel = ref('')
const labelLanguage = ref(language.value)
const datatype = ref('')
const creatingProperty = ref(false)
const error = ref('')

async function createProperty() {
  if (creatingProperty.value) return
  creatingProperty.value = true
  error.value = ''
  try {
    const entityId = await postProperty({
      type: 'property',
      datatype: datatype.value,
    })
    await putLabel(entityId, labelLanguage.value, propertyLabel.value)
    await router.push(`/entity/${entityId}`)
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    creatingProperty.value = false
  }
}
</script>
