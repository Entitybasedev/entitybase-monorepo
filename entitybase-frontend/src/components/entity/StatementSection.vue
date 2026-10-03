<template>
  <div>
    <h3>Statements</h3>
    <form
      v-if="isLoggedIn"
      class="statement-form"
      data-testid="statement-form"
      @submit.prevent="addStatement"
    >
      <div class="row">
        <label for="property-input">Property</label>
        <input id="property-input" v-model="stmtProperty" data-testid="statement-property-input" placeholder="P31" />
      </div>
      <div class="row">
        <label for="value-input">Value entity</label>
        <input id="value-input" v-model="stmtValue" data-testid="statement-value-input" placeholder="Q5" />
      </div>
      <button class="btn btn-primary btn-sm" type="submit" data-testid="add-statement-button" :disabled="adding || !stmtProperty || !stmtValue">
        {{ adding ? 'Adding…' : 'Add statement' }}
      </button>
    </form>
    <p v-else class="login-hint" data-testid="login-required-edit">
      <router-link to="/login">Log in</router-link> to add statements.
    </p>

    <StatementGroups
      :groups="groupedStatements"
      :editable="isLoggedIn"
      :editing-statement="editingStatement"
      v-model:statement-draft="statementDraft"
      :statement-saving="statementSaving"
      :statement-removing="statementRemoving"
      @edit="startStatementEdit"
      @save="saveStatementEdit"
      @cancel="cancelStatementEdit"
      @remove="removeStatement"
    />
  </div>
</template>

<script setup>
// Statements for an entity: the add form plus the grouped, editable list.
// Shared by the item, property and lexeme views.
import { computed, ref, watch } from 'vue'
import {
  deleteStatement,
  getSnak,
  getStatement,
  postStatement,
} from '../../api.js'
import { isLoggedIn } from '../../auth.js'
import { useEntityLabels } from '../../composables/useEntityLabels.js'
import StatementGroups from './StatementGroups.vue'

const props = defineProps({
  entityId: { type: String, required: true },
  // Statement content hashes from the entity revision; the parent reloads
  // the entity after a change and hands the new list down
  hashes: { type: Array, default: () => [] },
})

const emit = defineEmits(['error', 'reload'])

const { humanLabel } = useEntityLabels()

const adding = ref(false)
const statements = ref([])
const stmtProperty = ref('')
const stmtValue = ref('')
const editingStatement = ref(null)
const statementDraft = ref('')
const statementSaving = ref(false)
const statementRemoving = ref(null)

// Statements are stored per content hash and resolved one by one
async function load() {
  statements.value = []
  const hashes = props.hashes
  if (!hashes.length) return
  try {
    const fetched = await Promise.all(hashes.map((hash) => getStatement(hash)))
    const resolved = await Promise.all(
      fetched
        .map((res, index) => ({
          stmt: res.statement,
          hash: String(hashes[index]),
        }))
        .filter((entry) => entry.stmt && entry.stmt.mainsnak)
        .map(async ({ stmt, hash }) => {
          const mainsnak =
            typeof stmt.mainsnak === 'object'
              ? stmt.mainsnak
              : await getSnak(stmt.mainsnak)
          return mainsnak ? { stmt, mainsnak, hash } : null
        })
    )
    statements.value = await Promise.all(
      resolved
        .filter(Boolean)
        .map(async ({ stmt, mainsnak, hash }) => {
          const dv = mainsnak.datavalue
          const valueId =
            dv?.type === 'wikibase-item' ? (dv.value?.id ?? '?') : null
          const value = valueId ?? String(dv?.value ?? '?')
          const [propertyLabel, valueLabel] = await Promise.all([
            humanLabel(mainsnak.property),
            valueId ? humanLabel(valueId) : Promise.resolve(''),
          ])
          return {
            id: stmt.id ?? mainsnak.hash ?? String(mainsnak.property),
            // Content hash, used to address the statement for edit/remove
            hash,
            property: mainsnak.property,
            propertyLabel,
            value,
            valueLabel,
          }
        })
    )
  } catch (e) {
    emit('error', String(e.message || e))
  }
}

// Statements grouped by property for anchored navigation
// (/entity/<qid>#P31 or #P31-<n> per statement)
const groupedStatements = computed(() => {
  const groups = new Map()
  for (const s of statements.value) {
    if (!groups.has(s.property)) groups.set(s.property, [])
    groups.get(s.property).push(s)
  }
  return [...groups.entries()].map(([property, stmts]) => ({
    property,
    propertyLabel: stmts[0]?.propertyLabel || property,
    statements: stmts,
  }))
})

function statementClaim(propertyId, valueId) {
  return {
    claim: {
      id: crypto.randomUUID(),
      mainsnak: {
        snaktype: 'value',
        property: propertyId,
        datavalue: {
          value: { id: valueId },
          type: 'wikibase-item',
        },
      },
      type: 'statement',
      rank: 'normal',
    },
  }
}

async function addStatement() {
  adding.value = true
  try {
    await postStatement(
      props.entityId,
      statementClaim(stmtProperty.value, stmtValue.value)
    )
    stmtProperty.value = ''
    stmtValue.value = ''
    emit('reload')
  } catch (e) {
    emit('error', String(e.message || e))
  } finally {
    adding.value = false
  }
}

function startStatementEdit(statement) {
  editingStatement.value = statement.hash
  statementDraft.value = statement.value
}

function cancelStatementEdit() {
  editingStatement.value = null
  statementDraft.value = ''
}

// There is no statement-replace endpoint, so changing a value is done as
// remove-then-add. If the remove succeeds but the add fails the statement
// is gone, so say so explicitly and keep the draft for a retry.
async function saveStatementEdit(statement) {
  const valueId = statementDraft.value.trim()
  if (!valueId || statementSaving.value) return
  statementSaving.value = true
  let removed = false
  try {
    await deleteStatement(props.entityId, statement.hash)
    removed = true
    await postStatement(
      props.entityId,
      statementClaim(statement.property, valueId)
    )
    editingStatement.value = null
    statementDraft.value = ''
    emit('reload')
  } catch (e) {
    emit(
      'error',
      removed
        ? `Statement removed, but adding “${valueId}” failed: ${
            e.message || e
          }. Add it again to finish the edit.`
        : `Edit failed, the statement was not changed: ${e.message || e}`
    )
  } finally {
    statementSaving.value = false
  }
}

async function removeStatement(statement) {
  if (statementRemoving.value) return
  statementRemoving.value = statement.hash
  try {
    await deleteStatement(props.entityId, statement.hash)
    if (editingStatement.value === statement.hash) cancelStatementEdit()
    emit('reload')
  } catch (e) {
    emit('error', `Could not remove the statement: ${e.message || e}`)
  } finally {
    statementRemoving.value = null
  }
}

watch([() => props.entityId, () => props.hashes], load, { immediate: true })
</script>