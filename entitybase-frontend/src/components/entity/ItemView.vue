<template>
  <div>
    <TermsEditor :entity-id="entityId" :show-aliases="true" />
    <StatementSection
      :entity-id="entityId"
      :hashes="hashes"
      @error="$emit('error', $event)"
      @reload="$emit('reload')"
    />
  </div>
</template>

<script setup>
// An item: label, description and aliases plus statements.
import TermsEditor from './TermsEditor.vue'
import StatementSection from './StatementSection.vue'

defineProps({
  entityId: { type: String, required: true },
  hashes: { type: Array, default: () => [] },
})

defineEmits(['error', 'reload'])
</script>