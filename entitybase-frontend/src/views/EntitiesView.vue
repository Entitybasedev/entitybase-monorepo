<template>
    <section v-if="error" class="error" data-testid="error-banner">{{ error }}</section>

    <section v-if="item" class="panel" data-testid="item-section">
      <h2>Entity {{ item.id }}</h2>
      <div class="row">
        <span class="field-name">Label</span>
        <span data-testid="item-label">{{ displayLabel }}</span>
      </div>
      <div class="row">
        <span class="field-name">Description</span>
        <span data-testid="item-description">{{ description || '—' }}</span>
      </div>
      <div class="row">
        <span class="field-name">Aliases</span>
        <span v-if="aliases.length" data-testid="item-aliases">
          <span
            v-for="alias in aliases"
            :key="alias"
            data-testid="item-alias"
            class="alias-chip"
          >{{ alias }}</span>
        </span>
        <span v-else>—</span>
      </div>
      <p>
        <a :href="`/?entity=${item.id}`" data-testid="item-permalink">Permalink</a>
      </p>

      <h3>Statements</h3>
      <form class="statement-form" data-testid="statement-form" @submit.prevent="addStatement">
        <div class="row">
          <label for="property-input">Property</label>
          <input id="property-input" v-model="stmtProperty" data-testid="statement-property-input" placeholder="P31" />
        </div>
        <div class="row">
          <label for="value-input">Value entity</label>
          <input id="value-input" v-model="stmtValue" data-testid="statement-value-input" placeholder="Q5" />
        </div>
        <button type="submit" :disabled="adding || !stmtProperty || !stmtValue" data-testid="add-statement-button">
          {{ adding ? 'Adding…' : 'Add statement' }}
        </button>
      </form>

      <ul data-testid="statement-list">
        <li v-for="s in statements" :key="s.id" data-testid="statement">
          <span class="field-name" data-testid="statement-property">{{ s.propertyLabel || s.property }}</span>
          <span data-testid="statement-value">{{ s.valueLabel || s.value }}</span>
        </li>
        <li v-if="!statements.length" data-testid="no-statements">No statements yet.</li>
      </ul>

      <h3>History</h3>
      <div v-if="viewingRevision" class="revision-banner" data-testid="revision-banner">
        Viewing revision {{ viewingRevision }} —
        <a href="#" data-testid="back-to-current" @click.prevent="backToCurrent">back to current</a>
      </div>
      <table class="history" data-testid="history-list">
        <tbody>
          <tr v-for="entry in history" :key="entry.revision_id" data-testid="history-row">
            <td data-testid="history-revision">{{ entry.revision_id }}</td>
            <td data-testid="history-timestamp">{{ entry.created_at }}</td>
            <td data-testid="history-user">{{ entry.user_id }}</td>
            <td data-testid="history-summary">{{ entry.edit_summary || '—' }}</td>
            <td>
              <button data-testid="history-view" @click="viewRevision(entry.revision_id)">View</button>
              <button
                v-if="canDiff(entry.revision_id)"
                data-testid="history-diff"
                @click="diffWithPrevious(entry.revision_id)"
              >Diff vs previous</button>
            </td>
          </tr>
        </tbody>
      </table>
      <button
        v-if="history.length >= historyOffset"
        data-testid="history-more"
        @click="loadMoreHistory"
      >Load more</button>

      <div v-if="diff" class="panel" data-testid="diff-view">
        <h3>Diff: revision {{ diff.newRev }} vs {{ diff.oldRev }}</h3>
        <p v-if="!diff.hasChanges" data-testid="diff-no-changes">No changes between these revisions.</p>
        <template v-else>
          <h4>Labels</h4>
          <ul>
            <li v-for="d in diff.labels" :key="'l' + d.lang" :data-testid="'diff-' + d.status">
              {{ d.lang }}: <span class="diff-old">{{ d.old ?? '—' }}</span> →
              <span class="diff-new">{{ d.new ?? '—' }}</span>
            </li>
          </ul>
          <h4>Descriptions</h4>
          <ul>
            <li v-for="d in diff.descriptions" :key="'d' + d.lang">
              {{ d.lang }}: <span class="diff-old">{{ d.old ?? '—' }}</span> →
              <span class="diff-new">{{ d.new ?? '—' }}</span>
            </li>
          </ul>
          <h4>Aliases</h4>
          <ul>
            <li v-for="a in diff.aliases" :key="'a' + a.lang">
              {{ a.lang }}:
              <span v-for="added in a.added" :key="added" class="diff-new" data-testid="diff-added">
                +{{ added }}
              </span>
              <span v-for="removed in a.removed" :key="removed" class="diff-old" data-testid="diff-removed">
                −{{ removed }}
              </span>
            </li>
          </ul>
          <h4>Statements</h4>
          <ul>
            <li v-for="st in diff.statements.added" :key="'sa' + st.property + st.value">
              <span class="diff-new" data-testid="diff-added">+ {{ st.property }}: {{ st.value }}</span>
            </li>
            <li v-for="st in diff.statements.removed" :key="'sr' + st.property + st.value">
              <span class="diff-old" data-testid="diff-removed">− {{ st.property }}: {{ st.value }}</span>
            </li>
          </ul>
        </template>
        <button data-testid="diff-close" @click="diff = null">Close diff</button>
      </div>
    </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getItem,
  getDescription,
  getAliases,
  getLabelWithFallback,
  getDescriptionWithFallback,
  getAliasesWithFallback,
  getUserSettings,
  getEntityHistory,
  getEntityRevision,
  getSnak,
  getStatement,
  resolveAliases as resolveAliasHashes,
  resolveDescriptions as resolveDescriptionHashes,
  resolveLabels as resolveLabelHashes,
  postStatement,
} from '../api.js'
import { computeEntityDiff } from '../entityDiff.js'
import {
  MAX_FALLBACK_LANGUAGES,
  fallbackChain,
  language,
  showQid,
} from '../settings.js'
import { isLoggedIn, userId as authUserId } from '../auth.js'

const route = useRoute()
const router = useRouter()

// Edits are attributed to the logged-in user; without a token this falls
// back to the legacy demo ID (overridable via the User ID input).
const userId = ref(authUserId.value || 90001)
const adding = ref(false)
const error = ref('')
const item = ref(null)

const stmtProperty = ref('')
const stmtValue = ref('')

const label = ref('')
const description = ref('')
const aliases = ref([])
const statements = ref([])

const history = ref([])
const historyOffset = ref(0)
const viewingRevision = ref(null)
const diff = ref(null)
const HISTORY_PAGE = 20

const termChain = computed(() => [
  ...new Set([language.value, ...fallbackChain.value]),
])

async function loadTerms(id) {
  const chain = termChain.value
  const result = (await getLabelWithFallback(id, chain)) ?? ''
  label.value = result
  description.value = (await getDescriptionWithFallback(id, chain)) ?? ''
  aliases.value = (await getAliasesWithFallback(id, chain)) ?? []
}

// Resolve an entity/property ID to its human-readable label (cached)
const labelCache = new Map()

async function humanLabel(id) {
  if (!id) return ''
  if (labelCache.has(id)) return labelCache.get(id)
  let resolved = ''
  try {
    resolved = (await getLabelWithFallback(id, termChain.value)) ?? ''
  } catch {
    resolved = ''
  }
  labelCache.set(id, resolved)
  return resolved
}

watch(language, async () => {
  if (item.value) await loadTerms(item.value.id)
})

watch(fallbackChain, async () => {
  if (item.value) await loadTerms(item.value.id)
})

const displayLabel = computed(() => {
  if (!label.value) return ''
  const suffix = showQid.value && item.value ? ` (${item.value.id})` : ''
  return label.value + suffix
})

const entityData = computed(
  () => item.value?.data?.revision ?? item.value?.data ?? item.value ?? {}
)

function entityIdFromQuery() {
  return typeof route.query.entity === 'string' ? route.query.entity : ''
}

async function loadItem(id) {
  error.value = ''
  label.value = ''
  description.value = ''
  aliases.value = []
  statements.value = []
  history.value = []
  historyOffset.value = 0
  viewingRevision.value = null
  diff.value = null
  try {
    item.value = await getItem(id)

    // Label values are stored hash-referenced; fetch via the terms endpoints
    await loadTerms(id)
    await loadHistory(id)

    // Statement values are resolved per content hash; mainsnak is stored
    // as a snak hash and resolved via the snaks endpoint
    const hashes = entityData.value.hashes?.statements ?? []
    const fetched = await Promise.all(hashes.map((h) => getStatement(h)))
    const withSnaks = await Promise.all(
      fetched
        .map((res) => res.statement)
        .filter((stmt) => stmt && stmt.mainsnak)
        .map(async (stmt) => {
          const mainsnak =
            typeof stmt.mainsnak === 'object'
              ? stmt.mainsnak
              : await getSnak(stmt.mainsnak)
          if (!mainsnak) return null
          return { stmt, mainsnak }
        })
    )
    statements.value = await Promise.all(
      withSnaks
        .filter(Boolean)
        .map(async ({ stmt, mainsnak }) => {
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
            property: mainsnak.property,
            propertyLabel,
            value,
            valueLabel,
          }
        })
    )
  } catch (e) {
    error.value = String(e.message || e)
  }
}

async function addStatement() {
  adding.value = true
  error.value = ''
  try {
    await postStatement(
      item.value.id,
      {
        claim: {
          id: crypto.randomUUID(),
          mainsnak: {
            snaktype: 'value',
            property: stmtProperty.value,
            datavalue: {
              value: { id: stmtValue.value },
              type: 'wikibase-item',
            },
          },
          type: 'statement',
          rank: 'normal',
        },
      },
      userId.value
    )
    stmtProperty.value = ''
    stmtValue.value = ''
    await loadItem(item.value.id)
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    adding.value = false
  }
}

async function loadHistory(id, offset = 0) {
  const entries = (await getEntityHistory(id, HISTORY_PAGE, offset)) ?? []
  if (offset === 0) {
    history.value = entries
  } else {
    history.value = [...history.value, ...entries]
  }
  historyOffset.value = offset + entries.length
}

async function loadMoreHistory() {
  if (!item.value) return
  await loadHistory(item.value.id, historyOffset.value)
}

function canDiff(revisionId) {
  const idx = history.value.findIndex((e) => e.revision_id === revisionId)
  return idx >= 0 && idx + 1 < history.value.length
}

async function viewRevision(revisionId) {
  error.value = ''
  try {
    item.value = await getEntityRevision(item.value.id, revisionId)
    viewingRevision.value = revisionId
    await loadTerms(item.value.id)
    statements.value = []
  } catch (e) {
    error.value = String(e.message || e)
  }
}

async function backToCurrent() {
  viewingRevision.value = null
  await loadItem(item.value.id)
}

async function diffWithPrevious(revisionId) {
  error.value = ''
  diff.value = null
  try {
    const idx = history.value.findIndex((e) => e.revision_id === revisionId)
    const older = history.value[idx + 1]
    const [newRev, oldRev] = await Promise.all([
      getEntityRevision(item.value.id, revisionId),
      getEntityRevision(item.value.id, older.revision_id),
    ])
    const result = await computeEntityDiff(oldRev, newRev, {
      resolveLabels: resolveLabelHashes,
      resolveDescriptions: resolveDescriptionHashes,
      resolveAliases: resolveAliasHashes,
      getStatement,
      getSnak,
    })
    diff.value = { ...result, oldRev: older.revision_id, newRev: revisionId }
  } catch (e) {
    error.value = String(e.message || e)
  }
}

onMounted(async () => {
  try {
    const settings = await getUserSettings(userId.value)
    const ui = settings?.ui ?? {}
    if (Array.isArray(ui.fallbackChain)) {
      fallbackChain.value = ui.fallbackChain.slice(0, MAX_FALLBACK_LANGUAGES)
    }
    if (typeof ui.language === 'string' && ui.language) {
      language.value = ui.language
    }
  } catch {
    /* settings are optional */
  }
  const id = entityIdFromQuery()
  if (id) {
    await loadItem(id)
  }
})
</script>
