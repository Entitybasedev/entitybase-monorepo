<template>
  <main class="app">
    <h1>Entitybase</h1>
    <nav class="tabs" data-testid="nav">
      <button
        data-testid="nav-entities"
        :class="{ active: activeTab === 'entities' }"
        @click="showTab('entities')"
      >
        Entities
      </button>
      <button
        data-testid="nav-stream"
        :class="{ active: activeTab === 'stream' }"
        @click="showTab('stream')"
      >
        Change stream
      </button>
      <div class="docs-menu">
        <button data-testid="nav-docs" @click="docsOpen = !docsOpen">
          Docs ▾
        </button>
        <div v-if="docsOpen" class="docs-dropdown" data-testid="docs-dropdown">
          <a
            href="https://entitybasedev.github.io/entitybase-monorepo/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Documentation ↗
          </a>
          <a href="/docs" target="_blank" rel="noopener noreferrer">
            API docs (entitybase) ↗
          </a>
          <a href="http://localhost:8888/docs" target="_blank" rel="noopener noreferrer">
            API docs (change stream) ↗
          </a>
        </div>
      </div>
    </nav>

    <template v-if="activeTab === 'entities'">
    <section class="panel" data-testid="create-item-section">
      <h2>Create item</h2>
      <div class="row">
        <label for="label-input">Label (en)</label>
        <input
          id="label-input"
          v-model="newLabel"
          data-testid="item-label-input"
          placeholder="Universe"
        />
      </div>
      <div class="row">
        <label for="user-id-input">User ID</label>
        <input id="user-id-input" v-model.number="userId" data-testid="user-id-input" type="number" />
      </div>
      <button :disabled="!newLabel || creating" data-testid="create-item-button" @click="createItem">
        {{ creating ? 'Creating…' : 'Create item' }}
      </button>
    </section>

    <section class="panel" data-testid="create-property-section">
      <h2>Create property</h2>
      <div class="row">
        <label for="property-label-input">Label (en)</label>
        <input
          id="property-label-input"
          v-model="propertyLabel"
          data-testid="property-label-input"
          placeholder="instance of"
        />
      </div>
      <button
        :disabled="!propertyLabel || creatingProperty"
        data-testid="create-property-button"
        @click="createProperty"
      >
        {{ creatingProperty ? 'Creating…' : 'Create property' }}
      </button>
    </section>

    <section class="panel" data-testid="create-lexeme-section">
      <h2>Create lexeme</h2>
      <div class="row">
        <label for="lemma-input">Lemma (en)</label>
        <input id="lemma-input" v-model="lemma" data-testid="lemma-input" placeholder="answer" />
      </div>
      <div class="row">
        <label for="lexeme-language-input">Language QID</label>
        <input
          id="lexeme-language-input"
          v-model="lexemeLanguage"
          data-testid="lexeme-language-input"
          placeholder="Q1860"
        />
      </div>
      <div class="row">
        <label for="lexeme-category-input">Lexical category QID</label>
        <input
          id="lexeme-category-input"
          v-model="lexemeCategory"
          data-testid="lexeme-category-input"
          placeholder="Q1084"
        />
      </div>
      <button
        :disabled="!lemma || creatingLexeme"
        data-testid="create-lexeme-button"
        @click="createLexeme"
      >
        {{ creatingLexeme ? 'Creating…' : 'Create lexeme' }}
      </button>
    </section>

    <section v-if="error" class="error" data-testid="error-banner">{{ error }}</section>

    <section v-if="item" class="panel" data-testid="item-section">
      <h2>Entity {{ item.id }}</h2>
      <div class="row">
        <span class="field-name">Label</span>
        <span data-testid="item-label">{{ label }}</span>
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
          <span class="field-name" data-testid="statement-property">{{ s.property }}</span>
          <span data-testid="statement-value">{{ s.value }}</span>
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
            <li v-for="d in diff.descriptions" :key="'d' + d.lang" :data-testid="'diff-' + d.status">
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
    <StreamView v-if="activeTab === 'stream'" />
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import StreamView from './components/stream/StreamView.vue'
import {
  getItem,
  getLabel,
  getDescription,
  getAliases,
  getEntityHistory,
  getEntityRevision,
  getSnak,
  getStatement,
  resolveAliases as resolveAliasHashes,
  resolveDescriptions as resolveDescriptionHashes,
  resolveLabels as resolveLabelHashes,
  postStatement,
  postItem,
  postProperty,
  postLexeme,
  putLabel,
} from './api.js'
import { computeEntityDiff } from './entityDiff.js'

const activeTab = ref('entities')
const docsOpen = ref(false)

function showTab(tab) {
  activeTab.value = tab
  window.history.replaceState(null, '', `/?tab=${tab}`)
}

const userId = ref(90001)
const newLabel = ref('')
const creating = ref(false)
const adding = ref(false)
const error = ref('')
const item = ref(null)

const stmtProperty = ref('')
const stmtValue = ref('')

const propertyLabel = ref('')
const creatingProperty = ref(false)

const lemma = ref('')
const lexemeLanguage = ref('Q1860')
const lexemeCategory = ref('Q1084')
const creatingLexeme = ref(false)

const label = ref('')
const description = ref('')
const aliases = ref([])
const statements = ref([])

const history = ref([])
const historyOffset = ref(0)
const viewingRevision = ref(null)
const diff = ref(null)
const HISTORY_PAGE = 20

const entityData = computed(
  () => item.value?.data?.revision ?? item.value?.data ?? item.value ?? {}
)

function loadFromQuery() {
  const params = new URLSearchParams(window.location.search)
  const tab = params.get('tab')
  if (tab === 'stream') {
    activeTab.value = 'stream'
  } else if (tab === 'entities') {
    activeTab.value = 'entities'
  }
  const id = params.get('entity')
  if (id) {
    activeTab.value = 'entities'
    loadItem(id)
  }
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
    label.value = (await getLabel(id, 'en')) ?? ''
    description.value = (await getDescription(id, 'en')) ?? ''
    aliases.value = (await getAliases(id, 'en')) ?? []
    await loadHistory(id)
    description.value = (await getDescription(id, 'en')) ?? ''
    aliases.value = (await getAliases(id, 'en')) ?? []

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
    statements.value = withSnaks
      .filter(Boolean)
      .map(({ stmt, mainsnak }) => {
        const dv = mainsnak.datavalue
        const value =
          dv?.type === 'wikibase-item' ? (dv.value?.id ?? '?') : String(dv?.value ?? '?')
        return {
          id: stmt.id ?? mainsnak.hash ?? String(mainsnak.property),
          property: mainsnak.property,
          value,
        }
      })
  } catch (e) {
    error.value = String(e.message || e)
  }
}

async function createItem() {
  creating.value = true
  error.value = ''
  try {
    const entityId = await postItem({}, userId.value)
    await putLabel(entityId, 'en', newLabel.value, userId.value)
    window.history.replaceState(null, '', `/?tab=entities&entity=${encodeURIComponent(entityId)}`)
    await loadItem(entityId)
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    creating.value = false
  }
}

async function createProperty() {
  creatingProperty.value = true
  error.value = ''
  try {
    const entityId = await postProperty({}, userId.value)
    await putLabel(entityId, 'en', propertyLabel.value, userId.value)
    window.history.replaceState(null, '', `/?tab=entities&entity=${encodeURIComponent(entityId)}`)
    await loadItem(entityId)
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    creatingProperty.value = false
  }
}

async function createLexeme() {
  creatingLexeme.value = true
  error.value = ''
  try {
    const entityId = await postLexeme(
      {
        type: 'lexeme',
        lemmas: { en: { language: 'en', value: lemma.value } },
        language: lexemeLanguage.value,
        lexical_category: lexemeCategory.value,
      },
      userId.value
    )
    window.history.replaceState(null, '', `/?tab=entities&entity=${encodeURIComponent(entityId)}`)
    await loadItem(entityId)
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    creatingLexeme.value = false
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
    label.value = (await getLabel(item.value.id, 'en')) ?? ''
    description.value = (await getDescription(item.value.id, 'en')) ?? ''
    aliases.value = (await getAliases(item.value.id, 'en')) ?? []
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

onMounted(loadFromQuery)
</script>

<style>
.tabs { display: flex; gap: .5rem; margin-bottom: 1rem; }
.tabs button { padding: .4rem 1rem; border: 1px solid #ddd; background: #f5f5f5; border-radius: 6px; cursor: pointer; }
.tabs button.active { background: #007bff; color: white; border-color: #007bff; }
.tabs .docs-menu { position: relative; }
.tabs .docs-menu button { padding: .4rem 1rem; border: 1px solid #ddd; background: #f5f5f5; border-radius: 6px; cursor: pointer; }
.tabs .docs-dropdown { position: absolute; top: 110%; left: 0; background: white; border: 1px solid #ddd; border-radius: 6px; min-width: 16rem; box-shadow: 0 4px 12px rgba(0,0,0,.08); z-index: 10; display: flex; flex-direction: column; }
.tabs .docs-dropdown a { padding: .5rem .9rem; text-decoration: none; color: #333; }
.tabs .docs-dropdown a:hover { background: #f0f6ff; }
body { font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 40rem; }
.panel { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin: 1rem 0; }
.row { display: flex; gap: .5rem; margin: .5rem 0; align-items: center; }
.field-name { font-weight: 600; display: inline-block; min-width: 6rem; }
label { min-width: 8rem; }
input { padding: .25rem .5rem; }
button { padding: .35rem .8rem; cursor: pointer; }
.error { color: #b00020; padding: .5rem 1rem; border: 1px solid #b00020; border-radius: 8px; }
ul { list-style: none; padding-left: 0; }
li { padding: .25rem 0; }
.alias-chip { display: inline-block; background: #eef6ff; border: 1px solid #b6d4fe; border-radius: 999px; padding: .1rem .6rem; margin-right: .35rem; }
.history { width: 100%; border-collapse: collapse; font-size: .9rem; }
.history td { border-top: 1px solid #eee; padding: .3rem .4rem; }
.revision-banner { background: #fff8e1; border: 1px solid #ffe082; border-radius: 6px; padding: .4rem .8rem; margin: .5rem 0; }
.diff-old { background: #fdecea; color: #b71c1c; text-decoration: line-through; padding: 0 .25rem; }
.diff-new { background: #e8f5e9; color: #1b5e20; padding: 0 .25rem; }
</style>
