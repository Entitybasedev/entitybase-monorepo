<template>
  <div class="row property-value">
    <label :for="inputId">{{ label }}</label>
    <input
      :id="inputId"
      class="form-control"
      style="width: auto"
      :value="modelValue"
      :placeholder="placeholder || 'a short text'"
      :data-testid="testid"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <span v-if="error" class="text-danger" :data-testid="testid + '-error'">{{ error }}</span>
  </div>
</template>

<script setup>
// Value input for text-valued properties (string): free text, so anything the
// user types is the value. Length is bounded because a string property is a
// label-like value, not a text field.
import { computed } from 'vue'

const MAX_LENGTH = 250

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: 'Value' },
  placeholder: { type: String, default: 'a short text' },
  testid: { type: String, default: 'statement-value-input' },
  inputId: { type: String, default: 'value-input' },
})

defineEmits(['update:modelValue'])

const tooLong = computed(() => props.modelValue.length > MAX_LENGTH)
const error = computed(() =>
  tooLong.value ? `Keep it under ${MAX_LENGTH} characters` : ''
)
</script>