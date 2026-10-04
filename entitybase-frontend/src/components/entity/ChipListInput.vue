<template>
  <div class="chip-list-input">
    <input
      v-model="draft"
      class="form-control"
      style="width: auto"
      :data-testid="testid + '-input'"
      :placeholder="placeholder"
      @keyup.enter="commit"
    />
    <span v-if="values.length" :data-testid="testid + '-chips'">
      <span
        v-for="value in values"
        :key="value"
        class="fallback-chip"
        :data-testid="testid + '-chip-' + value"
      >
        {{ display(value) }}
        <button
          type="button"
          class="fallback-remove"
          :data-testid="testid + '-remove-' + value"
          @click="remove(value)"
        >×</button>
      </span>
    </span>
  </div>
</template>

<script setup>
// Text input that commits to removable chips on Enter. Used for values that
// are typed freely rather than picked from a list (grammatical features).
import { computed, ref } from 'vue'
import { showQid } from '../../settings.js'
import { addChips } from './chips.js'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  // Prefix for the data-testid attributes, so several instances on one page
  // stay addressable in tests.
  testid: { type: String, required: true },
  placeholder: { type: String, default: 'type a value, press Enter' },
  // Optional id -> label map; unknown ids fall back to the raw value.
  labels: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue'])

const draft = ref('')
const values = computed(() => props.modelValue)

function display(value) {
  const label = props.labels?.[value]
  if (!label) return value
  return showQid.value ? `${label} (${value})` : label
}

function commit() {
  if (!draft.value.trim()) return
  emit('update:modelValue', addChips(props.modelValue, draft.value))
  draft.value = ''
}

function remove(value) {
  emit('update:modelValue', props.modelValue.filter((v) => v !== value))
}
</script>

<style scoped>
.chip-list-input { display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; }
</style>