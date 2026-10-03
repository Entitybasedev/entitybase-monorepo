<template>
  <section v-if="error" class="alert alert-danger" data-testid="error-banner">{{ error }}</section>

  <section v-if="item" class="card card-body mb-3" data-testid="item-section">
    <h1>
      {{ item.id }}
      <span class="badge text-bg-secondary" data-testid="item-type-badge">{{ typeLabel }}</span>
    </h1>

    <ItemView
      v-if="kind === 'item'"
      :entity-id="item.id"
      :hashes="statementHashes"
      @error="error = $event"
      @reload="loadItem(item.id)"
    />
    <PropertyView
      v-else-if="kind === 'property'"
      :entity-id="item.id"
      :hashes="statementHashes"
      @error="error = $event"
      @reload="loadItem(item.id)"
    />
    <LexemeView
      v-else
      :entity-id="item.id"
      :revision="revisionData"
      :hashes="statementHashes"
      @error="error = $event"
      @reload="loadItem(item.id)"
    />

    <p>
      <a :href="`/entity/${item.id}`" data-testid="item-permalink">Permalink</a>
    </p>

    <h3>History</h3>
    <p>
      <router-link
        :to="`/${item.id}/history`"
        data-testid="item-history-link"
      >View history</router-link>
      ·
      <router-link
        :to="`/${item.id}/terms`"
        data-testid="item-terms-link"
      >View all terms</router-link>
    </p>
  </section>
</template>

<script setup>
// Shell for the entity view: loads the entity and hands it to the view for
// its type (item, property or lexeme).
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getItem } from '../api.js'
import { MAX_FALLBACK_LANGUAGES, fallbackChain, language } from '../settings.js'
import { userId as authUserId } from '../auth.js'
import { getUserSettings } from '../api.js'
import ItemView from '../components/entity/ItemView.vue'
import PropertyView from '../components/entity/PropertyView.vue'
import LexemeView from '../components/entity/LexemeView.vue'

const route = useRoute()

const authUser = ref(authUserId.value)
const error = ref('')
const item = ref(null)

const entityId = computed(() =>
  typeof route.params.entityId === 'string' ? route.params.entityId : ''
)

const TYPE_LABELS = { item: 'Item', property: 'Property', lexeme: 'Lexeme' }

const kind = computed(() => {
  const id = item.value?.id ?? ''
  if (id.startsWith('P')) return 'property'
  if (id.startsWith('L')) return 'lexeme'
  return 'item'
})

const typeLabel = computed(() => {
  const fromRevision = item.value?.data?.revision?.entity_type
  if (fromRevision && TYPE_LABELS[fromRevision]) return TYPE_LABELS[fromRevision]
  return TYPE_LABELS[kind.value]
})

const revisionData = computed(() => item.value?.data?.revision ?? {})
const statementHashes = computed(
  () => revisionData.value.hashes?.statements ?? []
)

async function loadItem(id) {
  error.value = ''
  item.value = null
  try {
    item.value = await getItem(id)
  } catch (e) {
    error.value = String(e.message || e)
  }
}

watch(entityId, (id) => {
  if (id) loadItem(id)
})

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
  if (entityId.value) {
    await loadItem(entityId.value)
  }
})
</script>