<template>
  <div>
    <div class="row">
      <span class="field-name">Type</span>
      <span data-testid="property-datatype">{{ datatypeLabel || '—' }}</span>
    </div>
    <TermsEditor :entity-id="entityId" :show-aliases="false" />
    <StatementSection
      :entity-id="entityId"
      :hashes="hashes"
      :revision="revision"
      @error="$emit('error', $event)"
      @reload="$emit('reload')"
    />
  </div>
</template>

<script setup>
// A property: its datatype, then label and description plus statements.
// Properties have no aliases, so the alias row is hidden.
import { computed } from 'vue'
import { propertyTypeLabel } from '../../property_types/labels.js'
import TermsEditor from './TermsEditor.vue'
import StatementSection from './StatementSection.vue'

const props = defineProps({
  entityId: { type: String, required: true },
  hashes: { type: Array, default: () => [] },
  // Revision data carries the property's datatype
  revision: { type: Object, default: () => ({}) },
})

defineEmits(['error', 'reload'])

const datatypeLabel = computed(() => propertyTypeLabel(props.revision?.datatype))
</script>