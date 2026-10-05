<template>
  <div class="row property-value">
    <label :for="inputId">{{ label }}</label>
    <input
      :id="inputId"
      class="form-control"
      style="width: auto"
      :value="modelValue"
      :placeholder="placeholder || 'Q5'"
      :data-testid="testid"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <span v-if="error" class="text-danger" :data-testid="testid + '-error'">{{ error }}</span>
    <span v-else-if="!valid" class="text-muted small" :data-testid="testid + '-hint'">
      Enter an entity id such as Q5.
    </span>
  </div>
</template>

<script setup>
// Value input for item-valued properties (wikibase-item): the value is another
// entity, addressed by its id.
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: 'Value item' },
  placeholder: { type: String, default: 'Q5' },
  testid: { type: String, default: 'statement-value-input' },
  inputId: { type: String, default: 'value-input' },
})

const emit = defineEmits(['update:modelValue'])

const ENTITY_ID = /^[QPL]\d+$/i

const valid = computed(() => !props.modelValue || ENTITY_ID.test(props.modelValue.trim()))
const error = computed(() =>
  props.modelValue && !valid.value ? `“${props.modelValue.trim()}” is not an entity id` : ''
)
</script>