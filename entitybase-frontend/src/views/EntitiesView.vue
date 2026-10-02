<template>
    <section v-if="error" class="alert alert-danger" data-testid="error-banner">{{ error }}</section>

    <section v-if="item" class="card card-body mb-3" data-testid="item-section">
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
        <button class="btn btn-primary btn-sm" type="submit" :disabled="adding || !stmtProperty || !stmtValue" data-testid="add-statement-button">
          {{ adding ? 'Adding…' : 'Add statement' }}
        </button>
      </form>
      <p v-else class="login-hint" data-testid="login-required-edit">
        <router-link to="/login">Log in</router-link> to add statements.
      </p>

      <ul data-testid="statement-list">
        <li v-for="s in statements" :key="s.id" data-testid="statement">
          <span class="field-name" data-testid="statement-property">{{ s.propertyLabel || s.property }}</span>
          <span data-testid="statement-value">{{ s.valueLabel || s.value }}</span>
        </li>
        <li v-if="!statements.length" data-testid="no-statements">No statements yet.</li>
      </ul>

      <h3>History</h3>
      <p>
        <router-link
          :to="`/${item.id}/history`"
          data-testid="item-history-link"
        >View history</router-link>
      </p>
     </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getItem,
  getLabelWithFallback,
  getDescriptionWithFallback,
  getAliasesWithFallback,
  getUserSettings,
  getSnak,
  getStatement,
  postStatement,
} from '../api.js'
import {
  MAX_FALLBACK_LANGUAGES,
  fallbackChain,
  language,
  showQid,
} from '../settings.js'
import { isLoggedIn, userId as authUserId } from '../auth.js'

const route = useRoute()
const router = useRouter()

// Edits are attributed to the logged-in user (login is required to edit).
const authUser = ref(authUserId.value)
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
      }
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

onMounted(async () => {
  try {
    const settings = await getUserSettings(authUser.value || 90001)
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
