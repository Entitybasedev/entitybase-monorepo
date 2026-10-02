<template>
  <section class="card card-body mb-3" data-testid="settings-section">
    <h2>Settings</h2>
    <p v-if="!isLoggedIn" data-testid="settings-not-logged-in">
      You are not logged in. Settings shown here are local to this browser.
    </p>
    <p v-else data-testid="settings-user">User: {{ username }} ({{ routeUserId }})</p>

    <div class="row">
      <label for="settings-language">Language</label>
      <select data-testid="settings-language-select" v-model="language">
        <option v-for="l in SUPPORTED_LANGUAGES" :key="l.code" :value="l.code">
          {{ l.name }}
        </option>
      </select>
    </div>

    <div class="row">
      <label for="settings-show-qid">Show IDs</label>
      <input
        id="settings-show-qid"
        type="checkbox"
        data-testid="settings-show-qid-toggle"
        v-model="showQid"
      />
    </div>

    <div class="row" data-testid="settings-fallback-chain">
      <span class="field-name">Language fallback chain</span>
      <span
        class="info-icon"
        data-testid="fallback-info"
        title="When a label or description is missing in your interface language, these languages are tried in order (max 5). Example: interface language is English, chain is [sv, da] — a term missing in English is looked up in Swedish, then Danish."
      >i</span>
      <span
        v-for="code in fallbackChain"
        :key="code"
        class="fallback-chip"
        data-testid="settings-fallback-chip"
      >
        {{ code }}
        <button
          class="fallback-remove"
          :data-testid="'settings-fallback-remove-' + code"
          @click="removeFallbackLanguage(code)"
        >×</button>
      </span>
      <select
        data-testid="settings-fallback-add-select"
        :value="''"
        :disabled="fallbackChain.length >= MAX_FALLBACK_LANGUAGES"
        @change="addFallbackLanguage($event.target.value)"
      >
        <option value="" disabled>+ add</option>
        <option
          v-for="l in availableFallbackLanguages"
          :key="l.code"
          :value="l.code"
        >{{ l.code }}</option>
      </select>
    </div>

    <button class="btn btn-primary btn-sm" data-testid="settings-save" :disabled="saving" @click="save">
      {{ saving ? 'Saving…' : 'Save settings' }}
    </button>
    <p v-if="savedMessage" class="saved" data-testid="settings-saved">{{ savedMessage }}</p>
    <section v-if="error" class="alert alert-danger" data-testid="settings-error">{{ error }}</section>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getUserSettings, putUserSettings } from '../api.js'
import {
  MAX_FALLBACK_LANGUAGES,
  SUPPORTED_LANGUAGES,
  fallbackChain,
  language,
  showQid,
} from '../settings.js'
import { isLoggedIn, userId as authUserId, username } from '../auth.js'

const route = useRoute()
const router = useRouter()

const routeUserId = computed(() => {
  const id = Number(route.params.userId)
  return Number.isFinite(id) && id > 0 ? id : authUserId.value
})

const saving = ref(false)
const savedMessage = ref('')
const error = ref('')

const availableFallbackLanguages = computed(() =>
  SUPPORTED_LANGUAGES.filter(
    (l) => l.code !== language.value && !fallbackChain.value.includes(l.code)
  )
)

function addFallbackLanguage(code) {
  if (!code || fallbackChain.value.includes(code)) return
  if (fallbackChain.value.length >= MAX_FALLBACK_LANGUAGES) return
  fallbackChain.value = [...fallbackChain.value, code]
}

function removeFallbackLanguage(code) {
  fallbackChain.value = fallbackChain.value.filter((c) => c !== code)
}

async function save() {
  saving.value = true
  savedMessage.value = ''
  error.value = ''
  try {
    await putUserSettings(routeUserId.value, {
      ui: { language: language.value, fallbackChain: fallbackChain.value },
    })
    savedMessage.value = 'Settings saved.'
  } catch (e) {
    error.value = `Failed to save settings: ${e.message}`
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const settings = await getUserSettings(routeUserId.value)
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
})

// Keep the URL in sync when the logged-in user's ID differs from the route
watch(isLoggedIn, (loggedIn) => {
  if (loggedIn && authUserId.value && String(authUserId.value) !== route.params.userId) {
    router.replace(`/${authUserId.value}/settings`)
  }
})
</script>

<style>
.saved { color: #1b5e20; }
.info-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.1rem;
  height: 1.1rem;
  border-radius: 50%;
  background: #b6d4fe;
  color: #084298;
  font-size: .75rem;
  font-weight: 700;
  cursor: help;
  user-select: none;
}
</style>
