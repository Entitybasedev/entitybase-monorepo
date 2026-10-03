<template>
  <div>
    <div class="row">
      <span class="field-name">Label</span>
      <template v-if="editingLabel">
        <select
          class="form-select form-select-sm"
          style="width: auto"
          data-testid="label-lang-select"
          v-model="editLanguage"
        >
          <option v-for="l in SUPPORTED_LANGUAGES" :key="l.code" :value="l.code">
            {{ l.code }}
          </option>
        </select>
        <input
          v-model="labelDraft"
          data-testid="label-edit-input"
          @keyup.enter="saveLabel"
        />
        <button
          class="btn btn-primary btn-sm"
          data-testid="save-label-button"
          :disabled="savingLabel"
          @click="saveLabel"
        >{{ savingLabel ? 'Saving…' : 'Save' }}</button>
        <button
          class="btn btn-outline-secondary btn-sm"
          data-testid="cancel-label-button"
          @click="editingLabel = false"
        >Cancel</button>
      </template>
      <template v-else>
        <span data-testid="item-label">{{ displayLabel }}</span>
        <button
          v-if="isLoggedIn"
          class="btn btn-outline-secondary btn-sm"
          data-testid="edit-label-button"
          @click="startLabelEdit"
        >Edit</button>
      </template>
    </div>

    <div class="row">
      <span class="field-name">Description</span>
      <template v-if="editingDescription">
        <select
          class="form-select form-select-sm"
          style="width: auto"
          data-testid="description-lang-select"
          v-model="editLanguage"
        >
          <option v-for="l in SUPPORTED_LANGUAGES" :key="l.code" :value="l.code">
            {{ l.code }}
          </option>
        </select>
        <input
          v-model="descriptionDraft"
          data-testid="description-edit-input"
          @keyup.enter="saveDescription"
        />
        <button
          class="btn btn-primary btn-sm"
          data-testid="save-description-button"
          :disabled="savingDescription"
          @click="saveDescription"
        >{{ savingDescription ? 'Saving…' : 'Save' }}</button>
        <button
          class="btn btn-outline-secondary btn-sm"
          data-testid="cancel-description-button"
          @click="editingDescription = false"
        >Cancel</button>
      </template>
      <template v-else>
        <span data-testid="item-description">{{ description || '—' }}</span>
        <button
          v-if="isLoggedIn"
          class="btn btn-outline-secondary btn-sm"
          data-testid="edit-description-button"
          @click="startDescriptionEdit"
        >Edit</button>
      </template>
    </div>

    <div v-if="showAliases" class="row">
      <span class="field-name">Aliases</span>
      <template v-if="editingAliases">
        <select
          class="form-select form-select-sm"
          style="width: auto"
          data-testid="aliases-lang-select"
          v-model="editLanguage"
        >
          <option v-for="l in SUPPORTED_LANGUAGES" :key="l.code" :value="l.code">
            {{ l.code }}
          </option>
        </select>
        <input
          v-model="aliasDraft"
          class="form-control"
          style="width: auto"
          data-testid="aliases-edit-input"
          placeholder="type an alias, press Enter"
          @keyup.enter="commitAlias"
        />
        <button
          class="btn btn-primary btn-sm"
          data-testid="save-aliases-button"
          :disabled="savingAliases"
          @click="saveAliases"
        >{{ savingAliases ? 'Saving…' : 'Save' }}</button>
        <button
          class="btn btn-outline-secondary btn-sm"
          data-testid="cancel-aliases-button"
          @click="editingAliases = false"
        >Cancel</button>
        <span class="small text-muted">Type an alias and press Enter; click Save to commit.</span>
        <span v-if="committedAliases.length" data-testid="alias-slugs">
          <span
            v-for="alias in committedAliases"
            :key="alias"
            class="fallback-chip"
          >
            {{ alias }}
            <button
              class="fallback-remove"
              :data-testid="'alias-remove-' + alias"
              @click="removeCommittedAlias(alias)"
            >×</button>
          </span>
        </span>
      </template>
      <template v-else>
        <span v-if="aliases.length" data-testid="item-aliases">
          <span
            v-for="alias in aliases"
            :key="alias"
            data-testid="item-alias"
            class="alias-chip"
          >{{ alias }}</span>
        </span>
        <span v-else>—</span>
        <button
          v-if="isLoggedIn"
          class="btn btn-outline-secondary btn-sm"
          data-testid="edit-aliases-button"
          @click="startAliasesEdit"
        >Edit</button>
      </template>
    </div>
  </div>
</template>

<script setup>
// Label, description and (for items) aliases, with a per-language editor.
// Items and properties share this; properties do not show aliases.
import { computed, ref, watch } from 'vue'
import {
  getAliases,
  getDescription,
  getLabel,
  getAliasesWithFallback,
  getDescriptionWithFallback,
  getLabelWithFallback,
  putAliases,
  putDescription,
  putLabel,
} from '../../api.js'
import {
  SUPPORTED_LANGUAGES,
  fallbackChain,
  language,
  showQid,
} from '../../settings.js'
import { isLoggedIn } from '../../auth.js'

const props = defineProps({
  entityId: { type: String, required: true },
  showAliases: { type: Boolean, default: true },
})

const label = ref('')
const description = ref('')
const aliases = ref([])
const editingLabel = ref(false)
const labelDraft = ref('')
const savingLabel = ref(false)
const editingDescription = ref(false)
const descriptionDraft = ref('')
const savingDescription = ref(false)
const editingAliases = ref(false)
const aliasDraft = ref('')
const committedAliases = ref([])
const savingAliases = ref(false)
// Language being edited (defaults to the interface language)
const editLanguage = ref('en')

const termChain = computed(() => [
  ...new Set([language.value, ...fallbackChain.value]),
])

const displayLabel = computed(() => {
  if (!label.value) return ''
  const suffix = showQid.value ? ` (${props.entityId})` : ''
  return label.value + suffix
})

async function load() {
  const chain = termChain.value
  label.value = (await getLabelWithFallback(props.entityId, chain)) ?? ''
  description.value =
    (await getDescriptionWithFallback(props.entityId, chain)) ?? ''
  if (props.showAliases) {
    aliases.value = (await getAliasesWithFallback(props.entityId, chain)) ?? []
  }
}

watch([language, fallbackChain], load)
watch(() => props.entityId, load, { immediate: true })

// Open the editor only once the term for the chosen language is loaded,
// otherwise the load resolves after the user has typed and resets the draft
async function startLabelEdit() {
  editLanguage.value = language.value
  labelDraft.value = (await getLabel(props.entityId, editLanguage.value)) ?? ''
  editingLabel.value = true
}

async function startDescriptionEdit() {
  editLanguage.value = language.value
  descriptionDraft.value =
    (await getDescription(props.entityId, editLanguage.value)) ?? ''
  editingDescription.value = true
}

async function startAliasesEdit() {
  editLanguage.value = language.value
  aliasDraft.value = ''
  committedAliases.value =
    (await getAliases(props.entityId, editLanguage.value)) ?? []
  editingAliases.value = true
}

// Switching the editor language loads that language's term
watch(editLanguage, async () => {
  const id = props.entityId
  const lang = editLanguage.value
  if (editingLabel.value) {
    labelDraft.value = (await getLabel(id, lang)) ?? ''
  }
  if (editingDescription.value) {
    descriptionDraft.value = (await getDescription(id, lang)) ?? ''
  }
  if (editingAliases.value) {
    committedAliases.value = (await getAliases(id, lang)) ?? []
  }
})

async function saveLabel() {
  savingLabel.value = true
  try {
    await putLabel(props.entityId, editLanguage.value, labelDraft.value)
    editingLabel.value = false
    await load()
  } finally {
    savingLabel.value = false
  }
}

async function saveDescription() {
  savingDescription.value = true
  try {
    await putDescription(props.entityId, editLanguage.value, descriptionDraft.value)
    editingDescription.value = false
    await load()
  } finally {
    savingDescription.value = false
  }
}

async function saveAliases() {
  savingAliases.value = true
  try {
    commitAlias()
    await putAliases(props.entityId, editLanguage.value, committedAliases.value)
    editingAliases.value = false
    await load()
  } finally {
    savingAliases.value = false
  }
}

// Commit the draft as slug chips: trim, drop blanks, dedupe
// case-insensitively (first casing wins). Enter commits; only the
// Save button persists to the server.
function parseAliasDraft(draft) {
  const seen = new Set()
  const values = []
  for (const raw of draft.split(',')) {
    const value = raw.trim()
    if (!value) continue
    const key = value.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    values.push(value)
  }
  return values
}

function commitAlias() {
  for (const value of parseAliasDraft(aliasDraft.value)) {
    const exists = committedAliases.value.some(
      (a) => a.toLowerCase() === value.toLowerCase()
    )
    if (!exists) committedAliases.value.push(value)
  }
  aliasDraft.value = ''
}

function removeCommittedAlias(alias) {
  committedAliases.value = committedAliases.value.filter((a) => a !== alias)
}
</script>