<template>
  <div class="row">
    <label for="property-type-select">Type</label>
    <select
      id="property-type-select"
      class="form-select form-select-sm"
      style="width: auto"
      data-testid="property-type-select"
      :disabled="disabled || !types.length"
      :value="modelValue"
      @change="$emit('update:modelValue', $event.target.value)"
    >
      <option v-for="type in types" :key="type.id" :value="type.id">
        {{ type.label }}
      </option>
    </select>
    <span v-if="loading" class="text-muted small" data-testid="property-type-loading">
      Loading types…
    </span>
    <span v-else-if="!types.length" class="text-danger small" data-testid="property-type-empty">
      No property types are available.
    </span>
  </div>
</template>

<script setup>
// Property type picker. The options come from the API, so a new property type
// shows up here without a frontend change.
import { onMounted, ref, watch } from 'vue'
import { getPropertyDatatypes } from '../../api.js'

const props = defineProps({
  modelValue: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'error'])

const types = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    types.value = await getPropertyDatatypes()
    // Default to the first type so the form is submittable straight away
    if (types.value.length && !types.value.some((t) => t.id === props.modelValue)) {
      emit('update:modelValue', types.value[0].id)
    }
  } catch (e) {
    emit('error', String(e.message || e))
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.modelValue, load)
</script>