<template>
  <div>
    <TermsEditor :entity-id="entityId" :show-aliases="false" />
    <StatementSection
      :entity-id="entityId"
      :hashes="hashes"
      @error="$emit('error', $event)"
      @reload="$emit('reload')"
    />
  </div>
</template>

<script setup>
// A property: label and description plus statements. Properties have no
// aliases, so the alias row is hidden.
import TermsEditor from './TermsEditor.vue'
import StatementSection from './StatementSection.vue'

defineProps({
  entityId: { type: String, required: true },
  hashes: { type: Array, default: () => [] },
})

defineEmits(['error', 'reload'])
</script>