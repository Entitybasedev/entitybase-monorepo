<template>
  <div :data-testid="testid">
    <div
      v-for="group in groups"
      :id="group.property"
      :key="group.property"
      class="statement-group"
      data-testid="statement-group"
    >
      <div class="statement-group-header">
        <a
          :href="`#${group.property}`"
          class="statement-anchor"
          data-testid="statement-property"
        >{{ group.propertyLabel || group.property }}</a>
        <span class="badge text-bg-secondary" data-testid="statement-group-count">
          {{ group.statements.length }}
        </span>
      </div>
      <ul>
        <li
          v-for="(s, i) in group.statements"
          :id="`${group.property}-${i + 1}`"
          :key="s.id || `${group.property}-${i}`"
          data-testid="statement"
        >
          <a
            :href="`#${group.property}-${i + 1}`"
            class="statement-anchor"
            data-testid="statement-link"
          >§</a>
          <template v-if="editable && !s.readOnly">
            <template v-if="editingStatement === s.hash">
              <input
                :value="statementDraft"
                class="statement-edit-input"
                data-testid="statement-edit-input"
                :aria-label="`New value for ${group.propertyLabel || group.property}`"
                @input="$emit('update:statementDraft', $event.target.value)"
                @keyup.enter="$emit('save', s, group)"
                @keyup.esc="$emit('cancel')"
              />
              <button
                class="btn btn-primary btn-sm"
                data-testid="statement-save-button"
                :disabled="statementSaving || !statementDraft.trim()"
                @click="$emit('save', s, group)"
              >{{ statementSaving ? 'Saving…' : 'Save' }}</button>
              <button
                class="btn btn-outline-secondary btn-sm"
                data-testid="statement-cancel-button"
                :disabled="statementSaving"
                @click="$emit('cancel')"
              >Cancel</button>
            </template>
            <template v-else>
              <span data-testid="statement-value">{{ s.valueLabel || s.value }}</span>
              <button
                class="btn btn-outline-secondary btn-sm statement-action"
                data-testid="statement-edit-button"
                :disabled="statementSaving || statementRemoving === s.hash"
                @click="$emit('edit', s)"
              >Edit</button>
              <button
                class="btn btn-outline-danger btn-sm statement-action"
                data-testid="statement-remove-button"
                :disabled="statementSaving || statementRemoving === s.hash"
                @click="$emit('remove', s)"
              >{{ statementRemoving === s.hash ? 'Removing…' : 'Remove' }}</button>
            </template>
          </template>
          <span v-else data-testid="statement-value">{{ s.valueLabel || s.value }}</span>
        </li>
      </ul>
    </div>
    <p v-if="!groups.length" data-testid="no-statements">No statements yet.</p>
  </div>
</template>

<script setup>
// Renders statements grouped by property. The same shape is used for entity
// statements (resolved from content hashes) and for the claims carried
// inline by lexeme senses and forms, so both render identically.
defineProps({
  groups: { type: Array, required: true },
  testid: { type: String, default: 'statement-list' },
  editable: { type: Boolean, default: false },
  editingStatement: { type: String, default: null },
  statementDraft: { type: String, default: '' },
  statementSaving: { type: Boolean, default: false },
  statementRemoving: { type: String, default: null },
})

defineEmits(['edit', 'save', 'cancel', 'remove'])
</script>